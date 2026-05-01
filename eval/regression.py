import json
from pathlib import Path
from typing import Dict


def regression_snapshot(eval_dataset_path: Path) -> Dict[str, float]:
    if not eval_dataset_path.exists():
        return {"total": 0.0, "failed": 0.0, "pass_rate": 1.0}

    total = 0
    failed = 0
    for line in eval_dataset_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        total += 1
        event = json.loads(line)
        if not event.get("passed", True):
            failed += 1

    pass_rate = 1.0 if total == 0 else (total - failed) / total
    return {"total": float(total), "failed": float(failed), "pass_rate": pass_rate}

