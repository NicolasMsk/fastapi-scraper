"""
Playwright script to scrape ALL coupon codes from Pepper.pl (Poland)
- Based on HotUKDeals scraper (same Pepper platform)
- Retrieves ALL codes from each page
- EXCLUDES similar merchants and expired codes
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_pepper_all(page, context, url):
    """
    Scrape all codes from a Pepper.pl page using Playwright.

    IMPORTANT: We EXCLUDE:
    - div._1hla7140 = "Active vouchers for retailers similar to..."
    - div.jkau50 = "Great discounts that have expired..."

    We only keep codes from the main merchant (with h3 = not expired)
    """
    results = []

    try:
        # Navigate to page with domcontentloaded strategy
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)

        # Close cookie consent popups
        try:
            page.click("button:has-text('Accept'), button:has-text('Agree'), button:has-text('Akceptuj'), #onetrust-accept-btn-handler", timeout=2000)
            page.wait_for_timeout(500)
        except:
            pass

        # ===================================================================
        # XPath to find VALID "See Code" buttons:
        # 1. Inside a card with h3 (not expired)
        # 2. NOT in the "similar vouchers" container (_1hla7140)
        # 3. NOT in the "expired" container (jkau50 with h2 containing "expired")
        # 4. NOT "Exclusive" offers
        # ===================================================================
        xpath_valid_codes = """
            //div[@data-testid='vouchers-ui-voucher-card-description'][.//h3]
                [not(ancestor::div[contains(@class, '_1hla7140')])]
                [not(ancestor::div[contains(@class, 'jkau50') and .//h2[contains(text(), 'expired') or contains(text(), 'wygasł')]])]
                [not(ancestor::div[@data-testid='vouchers-ui-voucher-card']//div[contains(text(), 'Exclusive')])]
            //div[@role='button' and (contains(@title, 'See Code') or contains(@title, 'Zobacz kod') or contains(@title, 'Pokaż kod'))]
        """.replace('\n', '').replace('    ', '')

        # Locate all valid "See Code" buttons
        see_code_buttons = page.locator(f"xpath={xpath_valid_codes}")
        total_count = see_code_buttons.count()

        if total_count == 0:
            return results

        print(f"      {total_count} valid codes found")

        # Track processed codes and titles to avoid duplicates
        processed_codes = set()
        processed_titles = set()

        # === STEP 1: Click on first button to open new tab ===
        first_btn = see_code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(300)

        # Click using JavaScript evaluation
        pages_before = len(context.pages)
        page.evaluate("(el) => el.click()", first_btn.element_handle())
        page.wait_for_timeout(1000)

        # Verify new tab opened
        if len(context.pages) <= pages_before:
            return results

        # Switch to new tab
        new_page = context.pages[-1]
        new_page.wait_for_timeout(1000)

        # === STEP 2: Loop through all codes on new tab ===
        max_iterations = min(total_count + 5, 25)

        for iteration in range(max_iterations):
            try:
                new_page.wait_for_timeout(1000)

                # STEP 1: Extract code (h4 with class b8qpi*)
                code = None
                try:
                    code_elem = new_page.locator("h4[class*='b8qpi']").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                except:
                    pass

                # Fallback: search all h4 elements for valid code
                if not code:
                    try:
                        h4_elems = new_page.locator("h4")
                        for i in range(h4_elems.count()):
                            text = h4_elems.nth(i).inner_text().strip()
                            if text and 3 <= len(text) <= 30 and text not in processed_codes:
                                code = text
                                break
                    except:
                        pass

                # STEP 2: Extract title from POPUP (h4.az57m without b8qpi)
                current_title = None
                try:
                    title_elems = new_page.locator("xpath=//h4[contains(@class, 'az57m') and not(contains(@class, 'b8qpi'))]")
                    if title_elems.count() > 0:
                        current_title = title_elems.first.inner_text().strip()
                except:
                    pass

                # Fallback: get title from card h3 element
                if not current_title:
                    try:
                        h3_elems = new_page.locator("div[data-testid='vouchers-ui-voucher-card-description'] h3")
                        idx = len(results)
                        if h3_elems.count() > idx:
                            current_title = h3_elems.nth(idx).inner_text().strip()
                    except:
                        pass

                # Only add if both code AND title are found (no default values)
                if code and current_title and code not in processed_codes and current_title not in processed_titles:
                    processed_codes.add(code)
                    processed_titles.add(current_title)
                    results.append({"code": code, "title": current_title})
                    print(f"[Pepper] ✅ Code: {code} | {current_title[:50]}...")

                # STEP 3: Close the popup
                try:
                    close_icon = new_page.locator("span[data-testid='CloseIcon'], svg[data-testid='CloseIcon']").first
                    if close_icon.count() > 0:
                        close_icon.click(timeout=2000)
                        new_page.wait_for_timeout(500)
                except:
                    pass

                # STEP 4: Find next button (with same exclusions)
                new_page.wait_for_timeout(300)

                xpath_next = """
                    //div[@data-testid='vouchers-ui-voucher-card-description'][.//h3]
                        [not(ancestor::div[contains(@class, '_1hla7140')])]
                        [not(ancestor::div[contains(@class, 'jkau50') and .//h2[contains(text(), 'expired') or contains(text(), 'wygasł')]])]
                        [not(ancestor::div[@data-testid='vouchers-ui-voucher-card']//div[contains(text(), 'Exclusive')])]
                    //div[@role='button' and (contains(@title, 'See Code') or contains(@title, 'Zobacz kod') or contains(@title, 'Pokaż kod'))]
                """.replace('\n', '').replace('    ', '')

                # Get all valid buttons
                next_buttons = new_page.locator(f"xpath={xpath_next}")
                current_index = len(results)

                # Get button at current index
                next_btn = next_buttons.nth(current_index)
                next_btn.scroll_into_view_if_needed()
                new_page.wait_for_timeout(200)

                # Click button using JavaScript
                pages_before = len(context.pages)
                new_page.evaluate("(el) => el.click()", next_btn.element_handle())
                new_page.wait_for_timeout(1000)

                # If a new tab opened, switch to it
                if len(context.pages) > pages_before:
                    new_page = context.pages[-1]
                    new_page.wait_for_timeout(500)

            except Exception as e:
                # Exit loop if any error occurs
                break

        # Close all opened tabs except the main one
        for p in context.pages[1:]:
            try:
                p.close()
            except:
                pass

    except Exception as e:
        print(f"      ❌ Error: {str(e)[:50]}")

    return results


def main():
    """Scrape Pepper PL depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")

    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("PL", "pepper")
    print(f"📍 Pepper: {len(competitor_data)} URLs uniques")

    all_results = []

    print(f"\n🚀 Launching Playwright...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        for idx, (merchant_row, url) in enumerate(competitor_data, 1):
            merchant_slug = merchant_row.get('Merchant_slug', 'Unknown')

            print(f"\n[{idx}/{len(competitor_data)}] 🏪 {merchant_slug}")
            print(f"   URL: {url[:60]}...")

            try:
                codes = scrape_pepper_all(page, context, url)
                print(f"   ✅ {len(codes)} codes found")

                for code_info in codes:
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "PL",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "pepper",
                        "Competitor_URL": url,
                        "Code": code_info["code"],
                        "Title": code_info["title"]
                    })
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:50]}")

            print(f"   📝 Total: {len(all_results)} codes")

        browser.close()

    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="Pepper PL")

        print(f"\n{'='*60}")
        print(f"✅ PEPPER PL COMPLETED!")
        print(f"📊 {len(all_results)} codes retrieved and sent to Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ No codes found")


if __name__ == "__main__":
    main()
