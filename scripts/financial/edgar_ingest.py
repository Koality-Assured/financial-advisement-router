"""Parse SEC company-facts JSON from recorded fixtures (advisory research only).

tags: [financial, edgar, xbrl, sec]
routing_hints: [edgar, companyfacts, 10-k, 10-q, xbrl, rate-limit]

Default path is a synthetic fixture. Live data.sec.gov pulls require
EDGAR_USER_AGENT in the environment, sleep to stay under 10 req/s, and are off
in tests. User-Agent examples in this repo are fake.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _ledger import (  # noqa: E402
    ADVISORY_STAMP,
    FloatLedgerError,
    ledger_context,
    stamp_payload,
    to_decimal,
)

FAKE_USER_AGENT_EXAMPLE = "FinancialAdvisementRouter research@example.com"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
MIN_INTERVAL_SEC = 0.11  # stay under 10 requests per second


def pad_cik(cik: str | int) -> str:
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    if not digits:
        raise ValueError("CIK must contain digits")
    return digits.zfill(10)


def _as_decimal_val(raw: Any, *, field: str) -> Decimal:
    if isinstance(raw, float):
        raise FloatLedgerError(f"float XBRL value rejected for {field}")
    return to_decimal(raw, field=field)


def extract_gaap_facts(payload: dict[str, Any], tags: list[str]) -> dict[str, Any]:
    facts = payload.get("facts", {}).get("us-gaap", {})
    extracted: dict[str, Any] = {}
    with ledger_context():
        for tag in tags:
            node = facts.get(tag)
            if not isinstance(node, dict):
                extracted[tag] = None
                continue
            units = node.get("units", {})
            usd = units.get("USD") or units.get("usd")
            if not usd:
                extracted[tag] = None
                continue
            latest = usd[-1]
            extracted[tag] = {
                "end": latest.get("end"),
                "form": latest.get("form"),
                "fy": latest.get("fy"),
                "fp": latest.get("fp"),
                "val": str(_as_decimal_val(latest.get("val"), field=tag)),
            }
    return extracted


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ingest_payload(payload: dict[str, Any], tags: list[str]) -> dict[str, Any]:
    cik = pad_cik(payload.get("cik", "0"))
    return stamp_payload(
        {
            "cik": cik,
            "entity": payload.get("entityName") or payload.get("entity") or "synthetic",
            "facts": extract_gaap_facts(payload, tags),
            "source": payload.get("source", "fixture"),
        }
    )


def live_fetch(cik: str, user_agent: str) -> dict[str, Any]:
    padded = pad_cik(cik)
    url = FACTS_URL.format(cik=padded)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov",
        },
    )
    time.sleep(MIN_INTERVAL_SEC)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - host pinned
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        default=str(_HERE / "fixtures" / "synthetic_companyfacts.json"),
        help="Recorded companyfacts JSON (default fixture; CI does not call EDGAR)",
    )
    parser.add_argument(
        "--tags",
        default="Assets,Liabilities,StockholdersEquity,NetCashProvidedByUsedInOperatingActivities",
        help="Comma-separated us-gaap tags",
    )
    parser.add_argument("--live", action="store_true", help="Fetch data.sec.gov (requires EDGAR_USER_AGENT)")
    parser.add_argument("--cik", default=None, help="CIK for --live")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.dry_run:
        print(
            json.dumps(
                stamp_payload(
                    {
                        "dry_run": True,
                        "fixture": args.fixture,
                        "live": args.live,
                        "user_agent_example": FAKE_USER_AGENT_EXAMPLE,
                    }
                ),
                indent=2,
            )
        )
        return 0
    try:
        if args.live:
            ua = os.environ.get("EDGAR_USER_AGENT", "").strip()
            if not ua:
                print(
                    "error: set EDGAR_USER_AGENT (fake example: "
                    f"{FAKE_USER_AGENT_EXAMPLE})",
                    file=sys.stderr,
                )
                return 2
            if not args.cik:
                print("error: --live requires --cik", file=sys.stderr)
                return 2
            payload = live_fetch(args.cik, ua)
            payload["source"] = "data.sec.gov"
        else:
            payload = load_fixture(Path(args.fixture))
            payload["source"] = "fixture"
        result = ingest_payload(payload, tags)
    except (OSError, KeyError, ValueError, FloatLedgerError, json.JSONDecodeError, urllib.error.URLError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["advisory_stamp"])
        print(f"cik={result['cik']} entity={result['entity']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
