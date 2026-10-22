"""Cross-platform equivalents of the Makefile targets."""
import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["data", "extend-pools", "refresh-references", "mock-data", "run", "test", "research"])
    args = parser.parse_args()
    commands = {
        "data": ["-m", "src.data.ingest"],
        "mock-data": ["-m", "src.data.bootstrap"],
        "run": ["-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        "test": ["-m", "pytest"],
        "research": ["-m", "src.evaluation.research"],
        "extend-pools": ["-m", "src.data.extend_pools"],
        "refresh-references": ["-m", "src.data.refresh_references"],
    }
    code = subprocess.call([sys.executable, "-X", "utf8", *commands[args.command]], cwd=Path(__file__).parent)
    if args.command=='data' and code==0:
        code=subprocess.call([sys.executable,'-X','utf8','-m','src.data.extend_pools'],cwd=Path(__file__).parent)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
