"""JSONL recorder for CallRecord-like dataclasses; never writes request headers."""
import dataclasses
import json
import pathlib


class Recorder:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def __enter__(self):
        self._f = open(self.path, "a", encoding="utf-8")
        return self

    def write(self, rec):
        self._f.write(json.dumps(dataclasses.asdict(rec), ensure_ascii=False) + "\n")

    def __exit__(self, *exc):
        self._f.close()
