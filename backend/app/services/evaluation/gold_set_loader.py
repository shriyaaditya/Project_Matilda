import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GoldSetLoader:
    """
    Loads and validates the frozen ground-truth evaluation dataset matilda_gold_set.json.
    """

    def __init__(self, json_path: str = "evaluation/matilda_gold_set.json") -> None:
        self.json_path = Path(json_path)

    def load_dataset(self, split: str = "all") -> dict[str, Any]:
        if not self.json_path.is_file():
            raise FileNotFoundError(f"Gold set dataset file not found: {self.json_path}")

        with open(self.json_path, encoding="utf-8") as f:
            data = json.load(f)

        cases = data.get("cases", [])
        if split != "all":
            cases = [c for c in cases if c.get("split") == split]

        return {
            "metadata": data.get("metadata", {}),
            "cases": cases,
        }
