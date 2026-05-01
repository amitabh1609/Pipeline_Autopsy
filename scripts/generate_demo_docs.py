#!/usr/bin/env python3
"""Generate synthetic demo documents (Phase 6). Output dir is gitignored by default."""

from __future__ import annotations

import argparse
import random
from pathlib import Path


def _invoice(i: int) -> str:
    return f"""Invoice #GEN-{i:04d}
Vendor: Demo Supplies Co {i % 7}
Customer: Sample Buyer LLC
Total Due: ${100 + (i * 17) % 900}
Tax: ${10 + (i * 3) % 80}
Payment Terms: Net 30
"""


def _ticket(i: int) -> str:
    return f"""Ticket T-{i:05d}
Issue: intermittent timeout on shard {(i % 3) + 1}
Priority: {'High' if i % 2 == 0 else 'Medium'}
Observed: rolling restarts during peak traffic.
Requested: RCA and mitigation timeline.
"""


def _ambiguous(i: int) -> str:
    return f"""Internal memo #{i}
They indicated approval might land Thursday unless legal pushes back.
Stakeholder "Alex" could mean either product or infra — follow usual escalation.
"""


def _short(i: int) -> str:
    msgs = ["Ping.", "Status?", "ASAP please.", "Need update.", "Blocked."]
    return msgs[i % len(msgs)]


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate TraceBack demo documents.")
    ap.add_argument("--count", type=int, default=50, help="Number of text files to write.")
    ap.add_argument("--out", type=Path, default=Path("documents/generated"))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rnd = random.Random(args.seed)
    writers = [_invoice, _ticket, _ambiguous, _short]
    args.out.mkdir(parents=True, exist_ok=True)
    for n in range(args.count):
        path = args.out / f"demo_{n + 1:03d}.txt"
        body = writers[n % len(writers)](n + 1)
        if rnd.random() < 0.12:
            body += "\nDisclaimer: synthetic fixture for pipeline testing.\n"
        path.write_text(body.strip() + "\n", encoding="utf-8")
    print(f"Wrote {args.count} files under {args.out.resolve()}")


if __name__ == "__main__":
    main()
