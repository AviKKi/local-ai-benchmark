import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_bench.config import BenchmarkError
from local_bench.registry import Registry


def main():
    url, maximum, timeout = sys.argv[1:]
    registry = Registry({"integrity": {"metadata_fetch_timeout_seconds": float(timeout)}})
    try:
        sys.stdout.buffer.write(registry.fetch(url, int(maximum)))
        return 0
    except BenchmarkError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
