#!/usr/bin/env python3
"""从 decisions.json 与 evidence/index.json 生成批次或最终 HTML 报告。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

from onemulti.reporting import (  # noqa: E402
    ReportError,
    batch_model,
    load_inputs,
    render,
    safe_batch_id,
    summary_model,
)


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}-", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("om_root", help="Skill 安装根目录，例如 .onemulti 或 $OM")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--batch-id", help="生成指定批次报告，例如 B01")
    mode.add_argument("--summary", action="store_true", help="生成最终汇总报告")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    om_root = Path(args.om_root).resolve()
    try:
        ledger, index = load_inputs(om_root)
        template = (om_root / "assets" / "report" / "report-template.html").read_text(
            encoding="utf-8"
        )
        if args.summary:
            model = summary_model(ledger, index, om_root)
            output = om_root / "adaptation-summary.html"
        else:
            batch_id = safe_batch_id(args.batch_id)
            model = batch_model(ledger, index, om_root, batch_id)
            output = om_root / f"adaptation-report-{batch_id}.html"
        write_atomic(output, render(template, model))
    except (OSError, ReportError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    result = {
        "status": "generated",
        "kind": model["kind"],
        "tier": model["tier"],
        "testConclusion": model["conclusion"],
        "flowStatus": model["flowStatus"],
        "verificationState": model["verificationState"],
        "output": str(output),
        "counts": model["counts"],
        "quality": {key: value for key, value in model["quality"].items() if key != "rows"},
    }
    if model["kind"] == "batch":
        result["batchId"] = model["batch"]["batchId"]
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
