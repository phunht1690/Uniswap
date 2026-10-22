"""Load versioned settings without inspecting credentials."""
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(name: str) -> dict:
    return yaml.safe_load((ROOT / "config" / f"{name}.yaml").read_text(encoding="utf-8"))


def state_directory() -> Path:
    return Path(os.environ.get("UNISWAP_STATE_DIR", str(ROOT))).resolve()


def make_directories(root: Path) -> None:
    for name in ["data/raw/mock", "data/interim", "data/processed", "outputs/runs", "outputs/tables", "outputs/figures"]:
        (root / name).mkdir(parents=True, exist_ok=True)
