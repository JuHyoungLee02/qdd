"""E-M35CL stage-cap diagnosis (read-only, CPU). Reads res/<ckpt>/<cond>/<set>/*/result.json, prints tables + JSON."""
import glob
import json
import re
import sys
from collections import Counter, defaultdict

import numpy as np

R = '/data/harvest/out/main35_closed/res'
OUT = sys.argv[1] if len(sys.argv) > 1 else '/data/harvest/tmp/diag_m35cl/diag.json'
REACH = 8.0
NUM = r'(-?\d+(?:\.\d+)?)'


def outcome(h):
    m = re.search(r'-> (.*?); TCP now \(' + NUM + ', ' + NUM + ', ' + NUM + r'\)', h)
    o = m.group(1) if m else h.split('->')[-1]
    tcp = [float(m.group(i)) for i in (2, 3, 4)] if m else None
    k = {'clipped': 'clipped to the workspace' in o, 'blocked': 'BLOCKED' in o, 'reached': 'reached the target' in o,
         'sag': 'normal arm sag' in o, 'settled': 'arm stopped moving' in o, 'unres': 'does not lead' in o,
         'stop': h.split(':', 1)[1].strip() == 'stop', 'invalid': 'invalid answer' in h}
    e = re.search(r'(?:error|stopped) ' + NUM + ' mm', o)
    return k, (float(e.group(1)) if e else None), tcp


def xy(a, b):
    return float(np.hypot(a[0] - b[0], a[1] - b[1])) * 1e3


def sites(r):
    by = {}
    for c in r['calls']:
        by[c['site']] = c  # last attempt of the site
    hs = {}
    for h in r['history']:
        m = re.match(r'(\d+):', h)
        if m:
            hs[int(m.group(1))] = h
    out = []
    ever = False
    for s in sorted(by):
        c = by[s]
        t = c['truth']
        ever_before = ever
        ever = ever or t['holding']
        cmd = (c.get('parsed') or {}).get('command') or {}
        a = (c.get('parsed') or {}).get('assessment') or {}
        rs = c.get('resolved') or {}
        k, err, tcp_after = outcome(hs.get(s, f'{s}: ?'))
        phase = 'carry' if t['holding'] else ('approach' if not ever_before else 'after')
        ref = t['place_xyz'] if phase == 'carry' else t['tgt_xyz']
        g = rs.get('goal')
        out.append(dict(site=s, phase=phase, hold=t['holding'], tcp=t['tcp'], tgt=t['tgt_xyz'], place=t['place_xyz'],
                        mode=cmd.get('mode'), height=cmd.get('height'), grip=cmd.get('gripper'),
                        pt=cmd.get('point_2d'), goal=g, kind=rs.get('kind'), mem=rs.get('memory'),
                        d_ref=xy(t['tcp'], ref), goal_err=(xy(g, ref) if g else None), out=k, err=err,
                        tcp_after=tcp_after, status=a.get('execution_status'),
                        attempting=(a.get('task_progress') or {}).get('currently_attempting'),
                        done_list=(a.get('task_progress') or {}).get('verified_completed')))
    return out


def same_cmd(a, b):
    if a['mode'] != b['mode'] or a['height'] != b['height'] or a['grip'] != b['grip']:
        return False
    if a['pt'] and b['pt']:
        return np.hypot(a['pt'][0] - b['pt'][0], a['pt'][1] - b['pt'][1]) <= 20
    return a['pt'] == b['pt']


def classify(r, S):
    """Mechanism labels for a failed episode (overlapping)."""
    L = S[-10:]
    lab = {}
    moved = [xy(x['tcp'], y['tcp']) + abs(x['tcp'][2] - y['tcp'][2]) * 1e3 for x, y in zip(L, L[1:])]
    rep = sum(same_cmd(x, y) for x, y in zip(L, L[1:]))
    lab['repeat_loop'] = rep >= 6 and float(np.sum(moved)) < 30  # same command, robot not moving
    lab['clip_block'] = sum(x['out']['clipped'] or x['out']['blocked'] for x in L) >= 5
    ge = [x['goal_err'] for x in L if x['goal_err'] is not None and x['phase'] != 'after']
    lab['wrong_target'] = bool(ge) and float(np.median(ge)) > 50
    # converging: relevant distance shrinking over the last 6 sites, not yet there
    L6 = S[-6:]
    d = [x['d_ref'] for x in L6]
    same_phase = len({x['phase'] for x in L6}) == 1
    slope = float(np.polyfit(range(len(d)), d, 1)[0]) if len(d) >= 3 else 0.0
    lab['converging'] = same_phase and slope < -5 and d[-1] > 15
    lab['stage_change_last8'] = len({x['phase'] for x in S[-8:]}) > 1 or any(
        x['out'] and x['grip'] in ('close', 'open') for x in S[-8:] if x['mode'] == 'point')
    # judgement: at the right place but planner does not advance
    at_above = [x for x in S if x['phase'] == 'approach' and x['d_ref'] <= 15 and x['height'] == 'above']
    at_place = [x for x in S if x['phase'] == 'carry' and x['d_ref'] <= 20 and x['height'] in ('above', 'lift')]
    lab['judge_approach'] = len(at_above) >= 3
    lab['judge_place'] = len(at_place) >= 3
    lab['regrasp'] = r.get('n_close', 0) >= 3
    lab['near_miss_nonreach'] = sum(1 for x in L if (x['out']['settled'] or x['out']['sag'] or x['out']['blocked'])
                                    and x['err'] is not None and x['err'] <= 15) >= 3
    lab['unresolved'] = sum(x['out']['unres'] for x in S) >= 3
    lab['invalid'] = sum(x['out']['invalid'] for x in S) >= 2
    return lab, dict(slope=slope, d_last=d[-1] if d else None, rep=rep, moved=float(np.sum(moved)),
                     ge_med=float(np.median(ge)) if ge else None)


def run():
    eps = []
    for f in sorted(glob.glob(R + '/*/*/*/*/result.json')):
        p = f.split('/')
        r = json.load(open(f))
        S = sites(r)
        eps.append(dict(ckpt=p[-5], cond=p[-4], set=p[-3], name=p[-2], r=r, S=S))
    res = {}
    for key in sorted({(e['ckpt'], e['cond'], e['set']) for e in eps}):
        E = [e for e in eps if (e['ckpt'], e['cond'], e['set']) == key]
        res['/'.join(key)] = summarize(E)
    for ck in ('f35d', '0.5'):
        E = [e for e in eps if e['ckpt'] == ck]
        res[ck + '/ALL'] = summarize(E)
        E = [e for e in eps if e['ckpt'] == ck and e['cond'] == 'none']
        res[ck + '/none/both'] = summarize(E)
    json.dump(res, open(OUT, 'w'), indent=1, default=float)
    for k in ('f35d/none/both', 'f35d/none/ood_o58', 'f35d/none/l8s_val', 'f35d/ALL', '0.5/none/both', '0.5/ALL'):
        print('=====', k)
        print(json.dumps(res[k], default=float, indent=None)[:6000])
    # per-episode dump of cap failures (f35d none) for the report
    rows = []
    for e in eps:
        if e['r']['end_reason'] in ('stage_cap_calls', 'stage_cap_motion'):
            lab, x = classify(e['r'], e['S'])
            rows.append(dict(k='/'.join((e['ckpt'], e['cond'], e['set'], e['name'])), fs=e['r']['fail_stage'],
                             lab=[a for a, v in lab.items() if v], **x))
    json.dump(rows, open(OUT.replace('.json', '_eps.json'), 'w'), indent=0, default=float)


def summarize(E):
    out = {'n': len(E), 'end': Counter(f"{e['r']['fail_stage']}/{e['r']['end_reason']}" for e in E).most_common(8)}
    succ = [e for e in E if e['r']['success']]
    fail = [e for e in E if not e['r']['success']]
    cap = [e for e in E if e['r']['end_reason'] == 'stage_cap_calls']
    out['n_succ'], out['n_cap'] = len(succ), len(cap)
    ns = [len(e['S']) for e in succ]
    out['succ_sites'] = dict(p50=float(np.median(ns)) if ns else None, p90=float(np.percentile(ns, 90)) if ns else None,
                             max=max(ns) if ns else None, hist=Counter(min(n // 5 * 5, 30) for n in ns))
    # success by cap k: episodes that succeeded using <= k sites
    out['succ_by_cap'] = {k: sum(n <= k for n in ns) for k in (10, 15, 20, 25, 30)}
    # hazard in sites 21-30 among episodes still running at site 20
    alive20 = [e for e in E if len(e['S']) > 20 or (e['r']['success'] and len(e['S']) > 20)]
    s2130 = sum(1 for n in ns if 20 < n <= 30)
    out['alive_after20'] = len(alive20)
    out['succ_21_30'] = s2130
    h = s2130 / max(len(alive20), 1) / 10  # per call hazard
    out['hazard_per_call_21_30'] = h
    run30 = len(cap)
    out['extrap_extra_succ'] = {f'cap{c}': run30 * (1 - (1 - h) ** (c - 30)) for c in (45, 60)}
    # mechanism labels for cap failures
    labs = Counter()
    info = []
    for e in cap:
        lab, x = classify(e['r'], e['S'])
        for a, v in lab.items():
            labs[a] += bool(v)
        info.append(x)
        # exclusive primary class
    prim = Counter()
    for e in cap:
        lab, _ = classify(e['r'], e['S'])
        if lab['repeat_loop'] and lab['clip_block']:
            p = 'stuck: clipped/blocked repeat'
        elif lab['repeat_loop'] and lab['wrong_target']:
            p = 'stuck: wrong target repeat'
        elif lab['repeat_loop']:
            p = 'stuck: same command, no motion'
        elif lab['converging'] or lab['stage_change_last8']:
            p = 'progressing at cut'
        elif lab['wrong_target']:
            p = 'wandering: wrong target'
        elif lab['judge_approach'] or lab['judge_place']:
            p = 'at goal, planner not advancing'
        else:
            p = 'other oscillation'
        prim[p] += 1
    out['cap_labels'] = dict(labs)
    out['cap_primary'] = dict(prim)
    # arrival tolerance: move outcomes
    mv = [x for e in E for x in e['S'] if x['err'] is not None and not x['out']['clipped']]
    nonreach = [x for x in mv if not x['out']['reached']]
    out['moves'] = len(mv)
    out['nonreach'] = len(nonreach)
    out['nonreach_le15'] = sum(x['err'] <= 15 for x in nonreach)
    out['nonreach_le15_frac_of_moves'] = out['nonreach_le15'] / max(len(mv), 1)
    out['nonreach_err_hist'] = Counter(('<=15' if x['err'] <= 15 else '15-30' if x['err'] <= 30 else '30-80'
                                        if x['err'] <= 80 else '>80') for x in nonreach)
    out['clipped_moves'] = sum(x['out']['clipped'] for e in E for x in e['S'])
    # after a <=15 mm non-reach, does the planner repeat the same command?
    rep_after = tot_after = 0
    for e in E:
        S = e['S']
        for a, b in zip(S, S[1:]):
            if a['err'] is not None and not a['out']['reached'] and a['err'] <= 15:
                tot_after += 1
                rep_after += same_cmd(a, b)
    out['after_near_nonreach_repeat'] = [rep_after, tot_after]
    # planner per-call target error (point -> xyz) vs truth object, by phase/intent
    ge = defaultdict(list)
    for e in E:
        for x in e['S']:
            if x['goal_err'] is not None and x['phase'] != 'after' and x['height'] in ('above', 'grasp', 'place'):
                ge[f"{x['phase']}/{x['height']}"].append(x['goal_err'])
    out['goal_err_mm'] = {k: dict(n=len(v), p50=float(np.median(v)), p75=float(np.percentile(v, 75)),
                                  le8=float(np.mean(np.array(v) <= 8)), le15=float(np.mean(np.array(v) <= 15)),
                                  gt50=float(np.mean(np.array(v) > 50))) for k, v in ge.items()}
    # success vs fail goal error (approach/above median per episode)
    def ep_ge(e):
        v = [x['goal_err'] for x in e['S'] if x['goal_err'] is not None and x['phase'] == 'approach']
        return float(np.median(v)) if v else None
    for nm, G in (('succ', succ), ('cap', cap)):
        v = [ep_ge(e) for e in G if ep_ge(e) is not None]
        out[f'ep_approach_goal_err_{nm}'] = dict(n=len(v), p50=float(np.median(v)) if v else None,
                                                 gt50=float(np.mean(np.array(v) > 50)) if v else None)
    # jitter: runs of consecutive same (phase, height) point commands whose goals are within 60 mm of the run start
    stds, osc = [], 0
    for e in E:
        S = [x for x in e['S'] if x['goal'] and x['mode'] == 'point' and x['height'] in ('above', 'grasp', 'place')]
        run = []
        for x in S + [None]:
            if run and (x is None or x['height'] != run[0]['height'] or x['phase'] != run[0]['phase'] or
                        np.linalg.norm(np.subtract(x['goal'], run[0]['goal'])) > 0.06 or x['site'] != run[-1]['site'] + 1):
                if len(run) >= 3:
                    g = np.array([y['goal'] for y in run]) * 1e3
                    stds.append(float(np.linalg.norm(g.std(0))))
                run = []
            if x is not None:
                run.append(x)
    out['jitter_std3d_mm'] = dict(n=len(stds), p50=float(np.median(stds)) if stds else None,
                                  p90=float(np.percentile(stds, 90)) if stds else None,
                                  gt8=float(np.mean(np.array(stds) > 8)) if stds else None,
                                  gt15=float(np.mean(np.array(stds) > 15)) if stds else None)
    # LoopGuard (tol 15 mm) blockers on 'above' repeats: goal jump vs TCP not arrived
    gj = tn = rp = 0
    for e in E:
        S = e['S']
        for a, b in zip(S, S[1:]):
            if a['height'] == 'above' and b['height'] == 'above' and a['goal'] and b['goal'] and a['mode'] == b['mode'] == 'point':
                if a['pt'] and b['pt'] and np.hypot(a['pt'][0] - b['pt'][0], a['pt'][1] - b['pt'][1]) <= 20:
                    rp += 1
                    if np.linalg.norm(np.subtract(a['goal'], b['goal'])) > 0.015:
                        gj += 1
                    elif np.linalg.norm(np.subtract(b['tcp'], a['goal'])) > 0.015:
                        tn += 1
    out['above_repeat_pairs'] = rp
    out['guard_blocked_goal_jump'] = gj
    out['guard_blocked_tcp_far'] = tn
    out['guard_switches'] = sum(len(e['r']['boost']['switches']) for e in E)
    # judgement: calls at the right place (truth) with a non-advancing command
    ja = sum(1 for e in E for x in e['S'] if x['phase'] == 'approach' and x['d_ref'] <= 15 and x['height'] == 'above'
             and abs(x['tcp'][2] - (x['goal'] or [0, 0, -9])[2]) <= 0.015)
    jp = sum(1 for e in E for x in e['S'] if x['phase'] == 'carry' and x['d_ref'] <= 20 and x['height'] in ('above', 'lift')
             and x['goal'] and abs(x['tcp'][2] - x['goal'][2]) <= 0.015)
    out['judge_calls_at_above_repeat'] = ja
    out['judge_calls_at_place_notplace'] = jp
    # planner says holding / grasp done while truth not holding (and vice versa)
    fh = th = 0
    for e in E:
        for x in e['S']:
            dl = ' '.join(x['done_list'] or []).lower()
            says = 'grasp' in dl or 'pick' in dl
            if x['phase'] == 'approach' and says:
                fh += 1
            if x['phase'] == 'carry' and not says and x['height'] in ('grasp',):
                th += 1
    out['planner_claims_grasp_truth_not_holding'] = fh
    out['planner_regrasp_while_holding'] = th
    # place/stop failures: final truth
    ps = [e for e in E if e['r']['end_reason'] == 'stop' and not e['r']['success']]
    pst = []
    for e in ps:
        x = e['S'][-1]
        pst.append(dict(d_tgt_place_xy=xy(x['tgt'], x['place']), hold=x['hold'], tipped=e['r']['tipped']))
    out['stop_fail'] = dict(n=len(ps), d_tgt_place_p50=float(np.median([p['d_tgt_place_xy'] for p in pst])) if pst else None,
                            tipped=sum(p['tipped'] for p in pst), held=sum(p['hold'] for p in pst))
    # other
    out['other'] = dict(knocked=sum(bool(e['r']['knocked']) for e in fail), tipped=sum(e['r']['tipped'] for e in fail),
                        unresolved=sum(e['r'].get('n_point_unresolved', 0) for e in E),
                        invalid=sum(e['r']['n_invalid'] for e in E),
                        mem_dropped=sum(sum(1 for m in e['r']['boost']['mem_checks'] if not m.get('kept')) for e in E),
                        multi_close=sum(e['r']['n_close'] >= 2 for e in fail),
                        close_no_hold=sum(1 for e in fail if e['r']['n_close'] >= 1 and not e['r']['ever_hold']),
                        sim_t_cap_p50=float(np.median([e['r']['sim_t'] for e in cap])) if cap else None)
    return out


if __name__ == '__main__':
    run()
