#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FRESH_PROSPECTS = ROOT / "output" / "fresh-prospects.csv"
FRESH_OUTREACH = ROOT / "output" / "fresh-outreach.csv"


def run_step(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def has_rows(path: Path) -> bool:
    if not path.exists():
        return False
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return any(bool((row.get("website") or "").strip()) for row in reader)


def main() -> int:
    run_step([sys.executable, "scripts/discover_prospects.py"])

    if has_rows(FRESH_PROSPECTS):
        run_step(
            [
                sys.executable,
                "scripts/generate_outreach.py",
                str(FRESH_PROSPECTS),
                "--output",
                str(FRESH_OUTREACH),
            ]
        )
    else:
        FRESH_OUTREACH.write_text("", encoding="utf-8")

    run_step([sys.executable, "scripts/sync_lead_state.py"])
    run_step([sys.executable, "scripts/enrich_contact_paths.py"])
    run_step([sys.executable, "scripts/generate_audit_pages.py"])
    run_step([sys.executable, "scripts/ingest_replies.py"])

    send_command = [sys.executable, "scripts/send_outreach.py"]
    if os.getenv("SEND_LIVE_OUTREACH", "").strip().lower() in {"1", "true", "yes"}:
        send_command.append("--live")
    run_step(send_command)
    form_command = [sys.executable, "scripts/submit_contact_forms.py"]
    if os.getenv("SEND_LIVE_FORMS", "").strip().lower() in {"1", "true", "yes"}:
        form_command.append("--live")
    run_step(form_command)
    run_step([sys.executable, "scripts/report_lead_state.py"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
