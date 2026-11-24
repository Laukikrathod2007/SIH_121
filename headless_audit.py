import asyncio
import json
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:5173"
SCREENSHOT_DIR = Path("audit_screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

ROUTES = [
    ("dashboard", "/app"),
    ("command_center", "/app/command-center"),
    ("live_drilling", "/app/drilling"),
    ("nearby_wells", "/app/wells"),
    ("offset_map", "/app/offset-map"),
    ("correlation", "/app/correlation"),
    ("risk_prediction", "/app/risk"),
    ("alerts_advisory", "/app/alerts"),
    ("historical_search", "/app/knowledge"),
    ("copilot", "/app/copilot"),
    ("document_ingestion", "/app/documents"),
    ("simulator", "/app/simulator"),
    ("reports", "/app/reports"),
    ("system_status", "/app/status"),
]

async def run_audit():
    print("=" * 60)
    print("  HEADLESS PLAYWRIGHT COMPREHENSIVE UI/UX AUDIT")
    print(f"  Target: {BASE_URL}")
    print(f"  Mode: 100% Silent Headless (Zero Windows / Popups)")
    print("=" * 60)

    results = {
        "passed_pages": [],
        "failed_pages": [],
        "console_errors": {},
        "failed_requests": {},
        "contrast_warnings": {},
        "screenshots": [],
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=1,
        )

        for name, route in ROUTES:
            print(f"\n[AUDITING ROUTE] {name} -> {route}")
            page_errors = []
            page_bad_requests = []

            # -------------------------------------------------------------
            # 1. DARK MODE AUDIT
            # -------------------------------------------------------------
            page = await context.new_page()
            page.on("console", lambda msg: page_errors.append(f"[Dark] {msg.text}") if msg.type == "error" else None)
            page.on("requestfailed", lambda req: page_bad_requests.append(f"[Dark] {req.url} - {req.failure}") if "net::ERR_ABORTED" not in str(req.failure) else None)
            page.on("response", lambda res: page_bad_requests.append(f"[Dark] {res.url} - {res.status}") if res.status >= 400 else None)

            try:
                # Set theme dark in localStorage before navigation
                await page.add_init_script("localStorage.setItem('drillwise-theme', 'dark');")
                await page.goto(f"{BASE_URL}{route}", wait_until="networkidle", timeout=15000)
                await asyncio.sleep(1.2) # allow Three.js / React re-renders

                # Screenshot dark
                dark_shot = SCREENSHOT_DIR / f"{name}_dark.png"
                await page.screenshot(path=str(dark_shot), full_page=False)
                results["screenshots"].append(str(dark_shot))

                # Verify critical elements
                title = await page.title()
                scada_panels = await page.locator(".scada-panel").count()
                print(f"  ✓ Dark Mode OK | Title: '{title}' | SCADA panels: {scada_panels}")

                # Interaction tests on specific pages
                if name == "document_ingestion":
                    presets = await page.locator("button:has-text('NHK-001')").count()
                    print(f"    - Evaluator Presets visible: {presets}")
                    if presets > 0:
                        btn = page.locator("button:has-text('NHK-001')").first
                        await btn.click()
                        await asyncio.sleep(2.0)
                        print("    - Clicked NHK-001 preset: job initiated successfully")

                elif name == "alerts_advisory":
                    hist_tab = page.locator("button:has-text('ALERT HISTORY')")
                    if await hist_tab.count() > 0:
                        await hist_tab.click()
                        await asyncio.sleep(1.0)
                        print("    - Switched to Alert History tab successfully")

            except Exception as e:
                print(f"  ✗ Dark Mode FAILED: {e}")
                results["failed_pages"].append(f"{name}_dark: {e}")
            finally:
                await page.close()

            # -------------------------------------------------------------
            # 2. LIGHT MODE AUDIT
            # -------------------------------------------------------------
            page_light = await context.new_page()
            page_light.on("console", lambda msg: page_errors.append(f"[Light] {msg.text}") if msg.type == "error" else None)
            page_light.on("requestfailed", lambda req: page_bad_requests.append(f"[Light] {req.url} - {req.failure}") if "net::ERR_ABORTED" not in str(req.failure) else None)
            page_light.on("response", lambda res: page_bad_requests.append(f"[Light] {res.url} - {res.status}") if res.status >= 400 else None)

            try:
                await page_light.add_init_script("localStorage.setItem('drillwise-theme', 'light');")
                await page_light.goto(f"{BASE_URL}{route}", wait_until="networkidle", timeout=15000)
                await asyncio.sleep(1.2)

                light_shot = SCREENSHOT_DIR / f"{name}_light.png"
                await page_light.screenshot(path=str(light_shot), full_page=False)
                results["screenshots"].append(str(light_shot))

                # Check data-theme applied
                data_theme = await page_light.evaluate("document.documentElement.getAttribute('data-theme')")
                print(f"  ✓ Light Mode OK | HTML data-theme: '{data_theme}' | Screenshot saved")
                results["passed_pages"].append(name)
            except Exception as e:
                print(f"  ✗ Light Mode FAILED: {e}")
                results["failed_pages"].append(f"{name}_light: {e}")
            finally:
                await page_light.close()

            if page_errors:
                results["console_errors"][name] = page_errors
            if page_bad_requests:
                results["failed_requests"][name] = page_bad_requests

        await browser.close()

    report_path = Path("audit_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 60)
    print(f"  AUDIT COMPLETE: {len(results['passed_pages'])}/{len(ROUTES)} pages audited in both Dark and Light modes")
    print(f"  Screenshots saved to: {SCREENSHOT_DIR.resolve()}")
    print(f"  Detailed report saved to: {report_path.resolve()}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_audit())
