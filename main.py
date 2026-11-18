#!/usr/bin/env python3
"""make.fun entrypoint — deploy the bundled entry.jpg.

Standard library only. Resolves entry.jpg next to this file (never the
process working directory), stages a copy in the output directory, checks
it, makes it world-readable, and atomically renames it into place.
"""

import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "entry.jpg")
MAX_BYTES = 1048576


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def main():
    if not os.path.isfile(SOURCE):
        fail(f"bundled entry.jpg not found at {SOURCE}")

    source_size = os.path.getsize(SOURCE)
    if source_size == 0:
        fail(f"bundled entry.jpg at {SOURCE} is empty")
    if source_size > MAX_BYTES:
        fail(f"bundled entry.jpg is {source_size} bytes, over the {MAX_BYTES} cap")

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as exc:
        fail(f"cannot create output directory {out_dir}: {exc}")

    destination = os.path.join(out_dir, "entry.jpg")

    fd, staged = tempfile.mkstemp(prefix=".entry-", suffix=".jpg", dir=out_dir)
    os.close(fd)
    try:
        shutil.copyfile(SOURCE, staged)

        staged_size = os.path.getsize(staged)
        if staged_size != source_size:
            fail(f"staged copy is {staged_size} bytes, expected {source_size}")

        # mkstemp creates 0600 and os.replace preserves it; the grader reads
        # as another user, so widen before publishing.
        os.chmod(staged, 0o644)
        os.replace(staged, destination)
    except BaseException:
        try:
            os.unlink(staged)
        except OSError:
            pass
        raise

    if not os.path.isfile(destination):
        fail(f"deployed file missing at {destination}")
    deployed_size = os.path.getsize(destination)
    if deployed_size != source_size:
        fail(f"deployed copy is {deployed_size} bytes, expected {source_size}")

    print(f"wrote {destination} ({deployed_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
