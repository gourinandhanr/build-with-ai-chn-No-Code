"""
test_api.py - Integration smoke-test for the Pickup Optimizer API.

Usage:
    # Start the server first:
    uvicorn main:app --port 8000

    # Then in another terminal:
    python test_api.py

The script exercises both endpoints and prints prettified JSON output.
It works out-of-the-box with MOCK_MAPS=true (no API key required).
"""

from __future__ import annotations

import json
import sys
import os

import httpx

# Force UTF-8 output on Windows
os.environ.setdefault("PYTHONIOENCODING", "utf-8")


BASE = "http://localhost:8000"
DIVIDER = "=" * 72



def pp(label: str, data: dict | list) -> None:
    """Pretty-print a labelled JSON payload."""
    print(f"\n{DIVIDER}", flush=True)
    print(f"  {label}")
    print(DIVIDER)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=15) as client:

        # -- 0. Health check ---
        print("\n[+] Health check ...")
        r = client.get("/health")
        r.raise_for_status()
        pp("GET /health", r.json())

        # -- 1. Single-user pickup optimization ---
        print("\n\n[+] Testing POST /optimize-pickup ...")

        # User that should be picked up (U001 – high & increasing weight)
        r = client.post(
            "/optimize-pickup",
            json={"user_id": "U001", "address": "123 Main Street, Mumbai"},
        )
        r.raise_for_status()
        pp("POST /optimize-pickup  [U001 – expect pickup=True]", r.json())

        # User that should NOT be picked up (U002 – low & stable weight)
        r = client.post(
            "/optimize-pickup",
            json={"user_id": "U002", "address": "456 Park Avenue, Delhi"},
        )
        r.raise_for_status()
        pp("POST /optimize-pickup  [U002 – expect pickup=False]", r.json())

        # User with spiking weight (U003)
        r = client.post(
            "/optimize-pickup",
            json={"user_id": "U003", "address": "789 Lake Road, Bangalore"},
        )
        r.raise_for_status()
        pp("POST /optimize-pickup  [U003 – expect pickup=True, spike]", r.json())

        # User with declining weight (U004 – borderline)
        r = client.post(
            "/optimize-pickup",
            json={"user_id": "U004", "address": "321 Hill View, Chennai"},
        )
        r.raise_for_status()
        pp("POST /optimize-pickup  [U004 – expect pickup=False, declining]", r.json())

        # Non-existent user
        r = client.post(
            "/optimize-pickup",
            json={"user_id": "U999", "address": "Nowhere"},
        )
        pp(
            "POST /optimize-pickup  [U999 – expect 404]",
            {"status_code": r.status_code, "detail": r.json()},
        )

        # -- 2. All pickup locations for today ---
        print("\n\n[+] Testing GET /pickup-locations-today ...")
        r = client.get("/pickup-locations-today")
        r.raise_for_status()
        pp("GET /pickup-locations-today", r.json())

    print(f"\n\n{'-' * 72}")
    print("[OK] All tests completed successfully!")
    print(f"{'-' * 72}\n")


if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print(
            "\n[ERROR] Could not connect to the server.\n"
            "    Make sure it is running:  uvicorn main:app --port 8000\n",
            file=sys.stderr,
        )
        sys.exit(1)
