"""R7 cycle 15 N2: `stageb_train train --resume` must refuse every changed option that changes the training trajectory
(or the logged evaluation sets), including the S-E2E diagnostic options (prereg_se2e_diag) and the temporal options
(prereg_se2e_temporal). Every option of the train parser is classified: RESUME_KEYS (must match) or RESUME_FREE
(bookkeeping). A checkpoint saved before an option existed resumes as if it had the option's default (the options
were added with defaults that keep the earlier behaviour)."""
import pytest

pytest.importorskip("torch")

from harvest.train import stageb_train as T  # noqa: E402

# the options named by the R7 cycle-15 report (N2) and the review instruction
NAMED = ("lr_schedule", "warmup_steps", "train_subset", "train_subset_seed", "train_fraction", "eval_train_subset",
         "eval_train_per_kind", "camera_layout", "motion_line", "motion_bins", "motion_dropout", "se2e_t_root")


def _defaults():
    return vars(T.build_parser().parse_args(["train", "--run", "a"]))


def _changed(v):
    if isinstance(v, bool):
        return not v
    if isinstance(v, int):
        return v + 1
    if isinstance(v, float):
        return v + 0.25
    return (v or "") + "_other"


def test_every_train_option_is_classified():
    dests = set(_defaults())
    keys, free = set(T.RESUME_KEYS), set(T.RESUME_FREE)
    assert not keys & free
    assert dests <= keys | free, sorted(dests - keys - free)  # a new option must be classified


@pytest.mark.parametrize("key", NAMED)
def test_named_options_are_resume_keys(key):
    assert key in T.RESUME_KEYS


@pytest.mark.parametrize("key", sorted(T.RESUME_KEYS))
def test_resume_refuses_any_changed_resume_key(key):
    base = _defaults()
    with pytest.raises(SystemExit, match=key):
        T.check_resume_args(base, {**base, key: _changed(base[key])})


def test_resume_accepts_changed_bookkeeping_options():
    base = _defaults()
    now = dict(base)
    for k in T.RESUME_FREE:
        if k != "cmd":
            now[k] = _changed(base[k])
    T.check_resume_args(base, now)  # run name, stop point, save / eval cadence, output root ... may differ


def test_old_checkpoint_without_the_new_options_resumes_with_defaults():
    base = _defaults()
    old = {k: v for k, v in base.items() if k not in NAMED}  # args saved before these options existed
    T.check_resume_args(old, base)  # defaults = the earlier behaviour: accepted
    for key in NAMED:
        with pytest.raises(SystemExit, match=key):
            T.check_resume_args(old, {**base, key: _changed(base[key])})
