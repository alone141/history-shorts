"""Writing files safely.

On some drives (seen on a managed Windows PC, drive E:), overwriting an existing
file in place does not truncate it: when the new content is shorter, the old
tail stays behind and silently corrupts JSON, source files, WAV and MP4 files.
Every writer in this project therefore goes through `fresh()`, which removes
the old file first, or through `write_text()` / `write_bytes()`, which write a
new file beside the target and then swap it in.
"""
from __future__ import annotations

import os
from pathlib import Path


def fresh(path: str | os.PathLike) -> Path:
    """Remove `path` if it exists (and make its folder) so the next write starts clean."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    return target


def write_bytes(path: str | os.PathLike, data: bytes) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".new")
    fresh(temporary).write_bytes(data)
    os.replace(temporary, target)
    return target


def write_text(path: str | os.PathLike, text: str) -> Path:
    return write_bytes(path, text.encode("utf-8"))
