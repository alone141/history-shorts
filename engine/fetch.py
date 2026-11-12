"""Download source files listed by a topic, with resume and a size check.

Certificates are verified against the operating system's trust store (via
truststore), so the same code works behind a TLS-inspecting proxy whose root
certificate is installed on the machine, and on an ordinary connection.

Usage:  python -m engine.fetch <manifest.json> [name ...]
        python -m engine.fetch <manifest.json> --check     (each source still answers; downloads nothing)

A manifest is a JSON list of {"name", "url", "dest", "note"} entries; "dest"
is relative to the repository root. Files that already exist are skipped.
"""
from __future__ import annotations

import json
import shutil
import ssl
import sys
import time
import urllib.request
from pathlib import Path
from engine.files import fresh, write_text as save_text

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:  # falls back to the bundled certificates
    pass

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = "evidence-films-fetch/1.0 (python-urllib)"
CHUNK = 1 << 20


def download(url: str, dest: Path, method: str = "GET", body: bytes | None = None,
             headers: dict | None = None) -> int:
    """Fetch url to dest (atomic: written to .part first). Returns bytes written."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("User-Agent", USER_AGENT)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    context = ssl.create_default_context()
    started = time.time()
    written = 0
    with urllib.request.urlopen(request, context=context, timeout=120) as response, open(fresh(part), "wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        last = started
        while True:
            block = response.read(CHUNK)
            if not block:
                break
            out.write(block)
            written += len(block)
            now = time.time()
            if now - last > 5:
                last = now
                done = f"{written / 1e6:.0f} MB"
                whole = f" of {total / 1e6:.0f} MB" if total else ""
                print(f"    {dest.name}: {done}{whole}", flush=True)
    if total and written != total:
        raise IOError(f"{dest.name}: got {written} bytes, expected {total}")
    shutil.move(str(part), str(dest))
    rate = written / 1e6 / max(time.time() - started, 0.001)
    print(f"  ok  {dest.relative_to(ROOT)}  {written / 1e6:.1f} MB  ({rate:.1f} MB/s)", flush=True)
    return written


def check(manifest_path: Path) -> int:
    """Ask each source for its first byte only, and report what answers."""
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = 0
    for entry in entries:
        request = urllib.request.Request(entry["url"], headers={"User-Agent": USER_AGENT, "Range": "bytes=0-0"})
        try:
            with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=60) as response:
                response.read(1)
                print(f"  ok   {response.status}  {entry['name']}", flush=True)
        except Exception as error:
            failures += 1
            print(f"  FAIL {entry['name']}: {type(error).__name__}: {error}", flush=True)
    return failures


def run(manifest_path: Path, only: list[str]) -> int:
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = 0
    for entry in entries:
        if only and entry["name"] not in only:
            continue
        dest = ROOT / entry["dest"]
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  have {entry['dest']}", flush=True)
            continue
        try:
            download(entry["url"], dest)
        except Exception as error:  # report and carry on with the other files
            failures += 1
            print(f"  FAIL {entry['name']}: {type(error).__name__}: {error}", flush=True)
    return failures


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    if "--check" in sys.argv[2:]:
        raise SystemExit(1 if check(Path(sys.argv[1])) else 0)
    raise SystemExit(1 if run(Path(sys.argv[1]), sys.argv[2:]) else 0)
