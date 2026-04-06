"""
Lead Scraper Web App - Double-click START.bat to launch.
"""

import io
import json
import re
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Auto-install dependencies
for pkg, imp in [("flask", "flask"), ("playwright", "playwright"), ("openpyxl", "openpyxl")]:
    try:
        __import__(imp)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

from flask import Flask, render_template_string, request, jsonify, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# Store latest results for download
latest_results = {"data": [], "business_type": "", "city": ""}

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lead Scraper</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
        }

        h1 {
            text-align: center;
            font-size: 2.2rem;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            text-align: center;
            color: #94a3b8;
            margin-bottom: 36px;
            font-size: 1rem;
        }

        .search-box {
            background: #1e293b;
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 32px;
            border: 1px solid #334155;
        }

        .form-row {
            display: flex;
            gap: 16px;
            align-items: end;
        }

        .form-group {
            flex: 1;
        }

        label {
            display: block;
            font-size: 0.85rem;
            font-weight: 600;
            color: #94a3b8;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        input {
            width: 100%;
            padding: 14px 18px;
            border-radius: 10px;
            border: 2px solid #334155;
            background: #0f172a;
            color: #e2e8f0;
            font-size: 1rem;
            transition: border-color 0.2s;
        }

        input:focus {
            outline: none;
            border-color: #60a5fa;
        }

        input::placeholder { color: #475569; }

        .btn {
            padding: 14px 32px;
            border-radius: 10px;
            border: none;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            white-space: nowrap;
        }

        .btn-search {
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            color: white;
            min-width: 140px;
        }

        .btn-search:hover { transform: translateY(-1px); box-shadow: 0 4px 20px rgba(59,130,246,0.4); }
        .btn-search:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }

        .btn-download {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
        }

        .btn-download:hover { transform: translateY(-1px); box-shadow: 0 4px 20px rgba(16,185,129,0.4); }

        /* Progress */
        .progress-area {
            display: none;
            margin-bottom: 32px;
        }

        .progress-bar-track {
            height: 6px;
            background: #1e293b;
            border-radius: 3px;
            overflow: hidden;
            margin-bottom: 12px;
        }

        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6);
            border-radius: 3px;
            width: 0%;
            transition: width 0.3s;
        }

        .progress-text {
            color: #94a3b8;
            font-size: 0.9rem;
            text-align: center;
        }

        /* Results */
        .results-area { display: none; }

        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .stats {
            display: flex;
            gap: 24px;
        }

        .stat {
            text-align: center;
        }

        .stat-number {
            font-size: 2rem;
            font-weight: 700;
        }

        .stat-label {
            font-size: 0.8rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .stat-green .stat-number { color: #ef4444; }
        .stat-red .stat-number { color: #10b981; }
        .stat-total .stat-number { color: #60a5fa; }

        table {
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 12px;
            overflow: hidden;
        }

        th {
            background: #334155;
            padding: 14px 18px;
            text-align: left;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94a3b8;
            font-weight: 600;
        }

        td {
            padding: 14px 18px;
            border-bottom: 1px solid #273549;
            font-size: 0.95rem;
        }

        tr:last-child td { border-bottom: none; }
        tr:hover td { background: #273549; }

        .tag {
            display: inline-block;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        .tag-yes {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .tag-no {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .error-msg {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #f87171;
            padding: 16px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: none;
        }

        @media (max-width: 700px) {
            .form-row { flex-direction: column; }
            .stats { gap: 16px; }
            .stat-number { font-size: 1.5rem; }
            td, th { padding: 10px 12px; font-size: 0.85rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Lead Scraper</h1>
        <p class="subtitle">Find local businesses without websites — your next clients</p>

        <div class="search-box">
            <div class="form-row">
                <div class="form-group">
                    <label>Business Type</label>
                    <input type="text" id="businessType" placeholder="plumbers, dentists, restaurants...">
                </div>
                <div class="form-group">
                    <label>City</label>
                    <input type="text" id="city" placeholder="Hammond Louisiana">
                </div>
                <button class="btn btn-search" id="searchBtn" onclick="doSearch()">Search</button>
            </div>
        </div>

        <div class="error-msg" id="errorMsg"></div>

        <div class="progress-area" id="progressArea">
            <div class="progress-bar-track">
                <div class="progress-bar-fill" id="progressBar"></div>
            </div>
            <p class="progress-text" id="progressText">Starting search...</p>
        </div>

        <div class="results-area" id="resultsArea">
            <div class="results-header">
                <div class="stats">
                    <div class="stat stat-total">
                        <div class="stat-number" id="statTotal">0</div>
                        <div class="stat-label">Total Found</div>
                    </div>
                    <div class="stat stat-red">
                        <div class="stat-number" id="statNoSite">0</div>
                        <div class="stat-label">No Website (Leads!)</div>
                    </div>
                    <div class="stat stat-green">
                        <div class="stat-number" id="statHasSite">0</div>
                        <div class="stat-label">Has Website</div>
                    </div>
                </div>
                <button class="btn btn-download" onclick="downloadExcel()">Download Excel</button>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Business Name</th>
                        <th>Phone</th>
                        <th>Address</th>
                        <th>Website</th>
                    </tr>
                </thead>
                <tbody id="resultsBody"></tbody>
            </table>
        </div>
    </div>

    <script>
        let pollTimer = null;

        function doSearch() {
            const biz = document.getElementById('businessType').value.trim();
            const city = document.getElementById('city').value.trim();

            if (!biz || !city) {
                showError('Please fill in both fields.');
                return;
            }

            // Reset UI
            document.getElementById('errorMsg').style.display = 'none';
            document.getElementById('resultsArea').style.display = 'none';
            document.getElementById('progressArea').style.display = 'block';
            document.getElementById('progressBar').style.width = '5%';
            document.getElementById('progressText').textContent = 'Opening Google Maps...';
            document.getElementById('searchBtn').disabled = true;
            document.getElementById('searchBtn').textContent = 'Searching...';

            fetch('/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({business_type: biz, city: city})
            })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'started') {
                    pollTimer = setInterval(pollProgress, 1500);
                }
            })
            .catch(() => {
                showError('Failed to start search. Make sure the server is running.');
                resetBtn();
            });
        }

        function pollProgress() {
            fetch('/progress')
            .then(r => r.json())
            .then(data => {
                document.getElementById('progressBar').style.width = data.percent + '%';
                document.getElementById('progressText').textContent = data.message;

                if (data.done) {
                    clearInterval(pollTimer);
                    if (data.results && data.results.length > 0) {
                        showResults(data.results);
                    } else {
                        showError(data.message || 'No results found. Try again in a minute.');
                    }
                    document.getElementById('progressArea').style.display = 'none';
                    resetBtn();
                }
            });
        }

        function showResults(results) {
            const tbody = document.getElementById('resultsBody');
            tbody.innerHTML = '';

            let hasSite = 0, noSite = 0;

            // Sort: no website first
            results.sort((a, b) => {
                if (a.website === 'No' && b.website === 'Yes') return -1;
                if (a.website === 'Yes' && b.website === 'No') return 1;
                return 0;
            });

            results.forEach(r => {
                if (r.website === 'Yes') hasSite++;
                else noSite++;

                const tag = r.website === 'Yes'
                    ? '<span class="tag tag-yes">Yes</span>'
                    : '<span class="tag tag-no">No &mdash; Lead!</span>';

                tbody.innerHTML += `<tr>
                    <td>${esc(r.name)}</td>
                    <td>${esc(r.phone)}</td>
                    <td>${esc(r.address)}</td>
                    <td>${tag}</td>
                </tr>`;
            });

            document.getElementById('statTotal').textContent = results.length;
            document.getElementById('statNoSite').textContent = noSite;
            document.getElementById('statHasSite').textContent = hasSite;
            document.getElementById('resultsArea').style.display = 'block';
        }

        function downloadExcel() {
            window.location.href = '/download';
        }

        function showError(msg) {
            const el = document.getElementById('errorMsg');
            el.textContent = msg;
            el.style.display = 'block';
        }

        function resetBtn() {
            document.getElementById('searchBtn').disabled = false;
            document.getElementById('searchBtn').textContent = 'Search';
        }

        function esc(s) {
            if (!s) return '';
            const d = document.createElement('div');
            d.textContent = s;
            return d.innerHTML;
        }

        // Allow Enter key to trigger search
        document.addEventListener('keydown', e => {
            if (e.key === 'Enter') doSearch();
        });
    </script>
</body>
</html>
"""

# Scraping progress state
progress = {"percent": 0, "message": "Idle", "done": False, "results": []}


def scrape_google_maps(business_type: str, city: str):
    """Scrape Google Maps — updates global progress as it goes."""
    global progress, latest_results
    progress = {"percent": 5, "message": "Opening Google Maps...", "done": False, "results": []}

    query = f"{business_type} in {city}"
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    results = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 900},
            )
            page = context.new_page()

            progress["message"] = "Loading Google Maps..."
            progress["percent"] = 10

            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception:
                page.goto(url, timeout=30000)

            time.sleep(3)

            # Accept cookies/consent
            try:
                consent = page.locator("button:has-text('Accept all')")
                if consent.count() > 0:
                    consent.first.click()
                    time.sleep(1)
            except Exception:
                pass

            # Scroll to load more results
            feed = page.locator('div[role="feed"]')
            if feed.count() == 0:
                feed = page.locator('div[role="main"]')

            progress["message"] = "Scrolling to load more results..."
            for i in range(8):
                progress["percent"] = 10 + int((i / 8) * 20)
                try:
                    feed.evaluate("el => el.scrollTop = el.scrollHeight")
                except Exception:
                    try:
                        page.mouse.wheel(0, 3000)
                    except Exception:
                        pass
                time.sleep(1.5)

            progress["percent"] = 30

            # Find listings
            links = page.locator('a[href*="/maps/place/"]')
            count = links.count()
            progress["message"] = f"Found {count} listings. Extracting details..."

            for i in range(count):
                pct = 30 + int((i / max(count, 1)) * 65)
                progress["percent"] = min(pct, 95)
                progress["message"] = f"Checking business {i+1} of {count}..."

                try:
                    link = links.nth(i)
                    label = link.get_attribute("aria-label") or ""
                    if not label:
                        continue

                    link.click()
                    time.sleep(2)

                    name = label.strip()
                    phone = ""
                    address = ""
                    has_website = "No"

                    # Phone
                    try:
                        phone_el = page.locator(
                            'button[data-item-id*="phone:"] div.fontBodyMedium, '
                            'button[aria-label*="Phone:"]'
                        )
                        if phone_el.count() > 0:
                            phone_label = (
                                page.locator('button[data-item-id*="phone:"]')
                                .first.get_attribute("aria-label") or ""
                            )
                            if phone_label:
                                match = re.search(r"[\d\(\)\-\+\s\.]{7,}", phone_label)
                                if match:
                                    phone = match.group().strip()
                            if not phone:
                                phone_text = phone_el.first.text_content() or ""
                                match = re.search(r"[\d\(\)\-\+\s\.]{7,}", phone_text)
                                if match:
                                    phone = match.group().strip()
                    except Exception:
                        pass

                    # Address
                    try:
                        addr_el = page.locator(
                            'button[data-item-id="address"] div.fontBodyMedium, '
                            'button[aria-label*="Address:"]'
                        )
                        if addr_el.count() > 0:
                            addr_label = (
                                page.locator('button[data-item-id="address"]')
                                .first.get_attribute("aria-label") or ""
                            )
                            if addr_label:
                                address = addr_label.replace("Address: ", "").strip()
                            else:
                                address = addr_el.first.text_content().strip()
                    except Exception:
                        pass

                    # Website
                    try:
                        website_el = page.locator(
                            'a[data-item-id="authority"], '
                            'button[data-item-id="authority"]'
                        )
                        if website_el.count() > 0:
                            has_website = "Yes"
                    except Exception:
                        pass

                    results.append({
                        "name": name,
                        "phone": phone,
                        "address": address,
                        "website": has_website,
                    })

                    # Go back
                    try:
                        back_btn = page.locator('button[aria-label="Back"]')
                        if back_btn.count() > 0:
                            back_btn.first.click()
                            time.sleep(1.5)
                    except Exception:
                        page.go_back()
                        time.sleep(2)

                except Exception:
                    try:
                        page.go_back()
                        time.sleep(1.5)
                    except Exception:
                        pass
                    continue

            browser.close()

    except Exception as e:
        progress["message"] = f"Error: {e}"
        progress["done"] = True
        progress["results"] = []
        return

    latest_results["data"] = results
    latest_results["business_type"] = business_type
    latest_results["city"] = city

    if results:
        no_site = sum(1 for r in results if r["website"] == "No")
        progress["message"] = f"Done! Found {len(results)} businesses ({no_site} without a website)"
    else:
        progress["message"] = "No results found. Google may have blocked the request — try again in a minute."

    progress["percent"] = 100
    progress["done"] = True
    progress["results"] = results


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    business_type = data.get("business_type", "").strip()
    city = data.get("city", "").strip()

    if not business_type or not city:
        return jsonify({"status": "error", "message": "Both fields required"}), 400

    # Run scraper in background thread
    thread = threading.Thread(
        target=scrape_google_maps,
        args=(business_type, city),
        daemon=True,
    )
    thread.start()

    return jsonify({"status": "started"})


@app.route("/progress")
def get_progress():
    return jsonify(progress)


@app.route("/download")
def download():
    results = latest_results["data"]
    if not results:
        return "No results to download", 404

    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"

    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    yes_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    no_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    for col, header in enumerate(["Business Name", "Phone Number", "Address", "Website"], 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    for row_idx, biz in enumerate(results, 2):
        ws.cell(row=row_idx, column=1, value=biz["name"]).border = thin_border
        ws.cell(row=row_idx, column=2, value=biz["phone"]).border = thin_border
        ws.cell(row=row_idx, column=3, value=biz["address"]).border = thin_border
        wc = ws.cell(row=row_idx, column=4, value=biz["website"])
        wc.border = thin_border
        wc.alignment = Alignment(horizontal="center")
        wc.fill = yes_fill if biz["website"] == "Yes" else no_fill

    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 45
    ws.column_dimensions["D"].width = 12
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:D{len(results) + 1}"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    safe_type = re.sub(r"[^\w\s-]", "", latest_results["business_type"]).strip().replace(" ", "_")
    safe_city = re.sub(r"[^\w\s-]", "", latest_results["city"]).strip().replace(" ", "_")
    filename = f"{safe_type}_{safe_city}_leads.xlsx"

    return send_file(buf, download_name=filename, as_attachment=True,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":
    # Open browser automatically after a short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://localhost:5000")

    threading.Thread(target=open_browser, daemon=True).start()

    print("\n  Lead Scraper is running!")
    print("  Open http://localhost:5000 in your browser")
    print("  Press Ctrl+C to stop\n")

    app.run(host="127.0.0.1", port=5000, debug=False)
