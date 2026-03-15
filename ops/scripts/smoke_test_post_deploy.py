#!/usr/bin/env python3
"""
Post-deploy smoke test: verifies critical endpoints are responding.

Usage:
    python ops/scripts/smoke_test_post_deploy.py --base-url https://api.gestiqcloud.com
    python ops/scripts/smoke_test_post_deploy.py  # defaults to http://localhost:8000
"""

import argparse
import json
import sys
import time
from urllib import error as urlerror
from urllib import request as urlrequest


def check_endpoint(base_url: str, path: str, expected_status: int = 200) -> dict:
    """Check a single endpoint and return result."""
    url = f"{base_url.rstrip('/')}{path}"
    start = time.monotonic()
    try:
        req = urlrequest.Request(url, method="GET")
        with urlrequest.urlopen(req, timeout=10) as resp:
            elapsed = (time.monotonic() - start) * 1000
            body = resp.read().decode("utf-8", errors="replace")
            return {
                "url": url,
                "status": resp.status,
                "ok": resp.status == expected_status,
                "elapsed_ms": round(elapsed, 1),
                "body_preview": body[:200],
            }
    except urlerror.HTTPError as e:
        elapsed = (time.monotonic() - start) * 1000
        return {
            "url": url,
            "status": e.code,
            "ok": e.code == expected_status,
            "elapsed_ms": round(elapsed, 1),
            "body_preview": str(e),
        }
    except Exception as e:
        elapsed = (time.monotonic() - start) * 1000
        return {
            "url": url,
            "status": 0,
            "ok": False,
            "elapsed_ms": round(elapsed, 1),
            "body_preview": str(e),
        }


def main():
    parser = argparse.ArgumentParser(description="Post-deploy smoke test")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    parser.add_argument("--timeout", type=int, default=30, help="Max wait time in seconds")
    args = parser.parse_args()

    endpoints = [
        ("/healthz", 200),
        ("/health", 200),
        ("/ready", 200),
        ("/docs", 200),
        ("/api/v1", 200),
    ]

    print(f"Running smoke tests against {args.base_url}")
    print("=" * 60)

    results = []
    for path, expected in endpoints:
        result = check_endpoint(args.base_url, path, expected)
        status_icon = "✓" if result["ok"] else "✗"
        print(f"  {status_icon} {path} -> {result['status']} ({result['elapsed_ms']}ms)")
        results.append(result)

    print("=" * 60)

    failed = [r for r in results if not r["ok"]]
    if failed:
        print(f"\n[FAILED] {len(failed)}/{len(results)} checks failed:")
        for r in failed:
            print(f"  ✗ {r['url']}: status={r['status']}, {r['body_preview'][:100]}")
        sys.exit(1)
    else:
        print(f"\n[SUCCESS] All {len(results)} checks passed")


if __name__ == "__main__":
    main()
