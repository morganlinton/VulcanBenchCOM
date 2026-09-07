"""Check a local public harness checkout against all recorded task hashes.

Requires the harness's supported Python version. Does not invoke any model.
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.harness_root.resolve()
    sys.path.insert(0, str(root))
    from harness.tasks import load_task, task_hash

    data = Path(__file__).resolve().parents[1] / "assets/data/swe-v4-astra-fable51/runs.json"
    rows = json.loads(data.read_text())["rows"]
    tasks = sorted({r["task"] for r in rows})
    assert len(tasks) == 23
    for task in tasks:
        actual = task_hash(load_task(task, root / "tasks/coding-intelligence-index-v4"))
        recorded = {r["source_hashes"]["task"] for r in rows if r["task"] == task}
        assert recorded == {actual}, f"Task definition differs: {task}"
    print("All 23 task definitions match every published run's task hash.")


if __name__ == "__main__":
    main()
