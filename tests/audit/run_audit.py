"""Offline audit harness — run the guardrails engine against the test corpus.

Reads `tests/audit/corpus.csv` (1,520-row DV-scenario corpus authored by
Aaron Wang) and processes every row through `guardrails.router.process_message`,
printing the tier + response. Stdlib only — no pandas — so this is safe to
run anywhere.

This is offline tooling, not part of the Worker bundle.

Usage:
    python tests/audit/run_audit.py
    python tests/audit/run_audit.py --filter "G-01"
    python tests/audit/run_audit.py --limit 20
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Make `src/` importable when running this script directly.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from guardrails.router import process_message  # noqa: E402
from guardrails.session import SessionState  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--corpus",
        default=str(Path(__file__).parent / "corpus.csv"),
        help="Path to the audit CSV",
    )
    ap.add_argument("--filter", default=None, help="Substring filter on Scenario Type")
    ap.add_argument("--limit", type=int, default=None, help="Max rows to process")
    args = ap.parse_args()

    with Path(args.corpus).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Normalize column names defensively
        if reader.fieldnames is None:
            print("error: corpus has no header row")
            return 1
        cols = {c.strip(): c for c in reader.fieldnames}
        prompt_col = next((cols[k] for k in cols if "prompt" in k.lower()), None)
        scenario_col = next(
            (cols[k] for k in cols if "scenario" in k.lower() or "type" in k.lower()),
            None,
        )
        if prompt_col is None:
            print(f"error: could not find prompt column in {list(cols)}")
            return 1

        print("\n## LEA GUARDRAILS AUDIT — G-01 to G-20 STRICT COMPLIANCE")
        print("=" * 80)

        total = 0
        for row in reader:
            prompt = (row.get(prompt_col) or "").strip()
            if not prompt:
                continue
            scenario = (row.get(scenario_col) or "Standard") if scenario_col else "Standard"
            if args.filter and args.filter.lower() not in scenario.lower():
                continue
            if args.limit is not None and total >= args.limit:
                break

            total += 1
            session = SessionState()
            result = process_message(prompt, session)
            print(f"Run {total:04d} | {scenario}")
            print(f"  Prompt : {prompt[:200]}")
            print(f"  Tier   : {result['tier']}")
            print(f"  Output : {result['response'][:300]}")
            print(f"  G-19   : quick_exit_required={result['show_quick_exit']}")
            print("-" * 80)

        print(f"\n{total} prompts processed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
