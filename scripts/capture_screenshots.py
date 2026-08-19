#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Digital Real-Estate Frontier, LLC
"""Capture README screenshots of the CONTINUUM dashboard.

Runs Playwright/Chromium against a target URL (live Cloud Run by default),
takes 3 screenshots for the README, and writes them to `docs/img/`.

Usage:
    python scripts/capture_screenshots.py
    python scripts/capture_screenshots.py --url http://localhost:8000
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "img"


def capture(url: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,  # retina — sharper PNGs for README
        )
        page = ctx.new_page()

        # 1. Full dashboard (above the fold + full page)
        page.goto(url, wait_until="networkidle", timeout=60_000)
        # Give any client-side fetches a moment to settle, even if they 500.
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "01-dashboard.png"), full_page=False)
        page.screenshot(path=str(OUT / "02-dashboard-full.png"), full_page=True)

        # 3. /health JSON — visible proof the deployment is live.
        page.goto(f"{url.rstrip('/')}/health", wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "03-health.png"), full_page=False)

        browser.close()

    print(f"wrote screenshots to {OUT}")
    for f in sorted(OUT.glob("*.png")):
        print(f"  {f.name}  {f.stat().st_size // 1024} KB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--url",
        default="https://continuum-882642985987.us-central1.run.app",
        help="Base URL to screenshot (default: live Cloud Run)",
    )
    args = ap.parse_args()
    capture(args.url)


if __name__ == "__main__":
    main()
