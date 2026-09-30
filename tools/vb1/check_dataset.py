#!/usr/bin/env python3
"""학습 전 데이터셋 점검 — 실제 샘플을 꺼내 영상 디코딩까지 확인한다.

    python check_dataset.py <dataset_root> [video_backend]

video_backend 를 주면 그 백엔드로 강제한다 (예: pyav, torchcodec).
"""
import sys
import traceback


def main():
    root = sys.argv[1]
    backend = sys.argv[2] if len(sys.argv) > 2 else None
    repo_id = root.rstrip('/').split('/')[-1]

    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    kwargs = {'root': root}
    if backend:
        kwargs['video_backend'] = backend
    ds = LeRobotDataset(repo_id, **kwargs)
    print(f'episodes={ds.num_episodes} frames={ds.num_frames} fps={ds.fps}', flush=True)
    print(f'video_backend={getattr(ds, "video_backend", "?")}', flush=True)

    for idx in (0, len(ds) // 2, len(ds) - 1):
        try:
            sample = ds[idx]
        except Exception:
            print(f'--- sample {idx}: 실패 ---', flush=True)
            traceback.print_exc()
            return 1
        shapes = []
        for key, value in sample.items():
            shape = getattr(value, 'shape', None)
            shapes.append(f'{key}{tuple(shape)}' if shape is not None else key)
        print(f'--- sample {idx} OK: ' + ', '.join(shapes), flush=True)

    print('DATASET_CHECK_PASSED', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
