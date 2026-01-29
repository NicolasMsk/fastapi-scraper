---
name: scraper-conventions
description: Coding conventions and patterns for Playwright coupon scrapers
disable-model-invocation: true
---

# Scraper Conventions

This project uses Playwright to scrape coupon codes from competitor websites.

## File Structure

```
Playwright/
├── {COUNTRY}/
│   └── scrap_{source}_{COUNTRY}.py
├── gsheet_loader.py      # Load URLs from Google Sheets
├── gsheet_writer.py      # Write results to Google Sheets
├── code_analyzer.py      # LLM analysis of codes
└── credentials/          # Google Sheets service account
```

## Scraper Pattern

Every scraper follows this structure:

```python
def scrape_{source}_all(page, context, url):
    """Main scraping function"""
    results = []
    affiliate_link = None

    try:
        # 1. Navigate to page
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # 2. Handle cookies/popups

        # 3. Find code buttons (exclude expired, similar merchants)

        # 4. Click first button to open new tab

        # 5. Capture affiliate link with stability check

        # 6. Loop through codes: extract code, title, close popup, next

    except Exception as e:
        print(f"[{Source}] Error: {str(e)[:50]}")

    return results, affiliate_link

def main():
    # Load from Google Sheets
    competitor_data = get_competitor_urls("COUNTRY", "source")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # ... process each merchant

    # Write results to Google Sheets
    append_to_gsheet(all_results, source_name="Source Country")
```

## Affiliate Link Capture Pattern

Always use this pattern for reliable affiliate capture:

```python
# Wait up to 10 seconds, verify URL is stable for 1.5s
try:
    last_url = None
    stable_count = 0
    for _ in range(20):  # Max 10 seconds
        current_url = page.url
        if "source_domain" not in current_url.lower():
            if current_url == last_url:
                stable_count += 1
                if stable_count >= 3:  # Stable for 1.5s
                    affiliate_link = current_url
                    break
            else:
                stable_count = 0
                last_url = current_url
        page.wait_for_timeout(500)
except Exception as e:
    pass
```

## Result Format

Each code must have:
- `code`: The promo code string
- `title`: Description of the offer
- `affiliate_link`: Captured redirect URL (optional)

Final result for Google Sheets:
```python
{
    "Date": "YYYY-MM-DD",
    "Country": "XX",
    "Merchant_ID": "",
    "Merchant_slug": "",
    "GPN_URL": "",
    "Competitor_Source": "source_name",
    "Competitor_URL": url,
    "Affiliate_Link": "",
    "Code": "",
    "Title": ""
}
```

## Common Exclusions

Always exclude:
- Expired codes (look for "expired", "scadute", "expiré" sections)
- Similar/competitor merchant offers
- "Get Deal" / "See Deal" (not actual codes)
- Exclusive codes (site-specific)

## Browser Choice

- **Chromium**: Default, works for most sites
- **Firefox**: Use for Cloudflare-protected sites (VoucherCodes UK)
