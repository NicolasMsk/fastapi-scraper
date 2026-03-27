"""
Script Playwright pour scraper TOUS les codes Rabatio (Pologne)
- Cliquer sur le 1er bouton "Kod" → nouvel onglet s'ouvre avec popup fancybox
- Extraire code (span.code-text) et titre (span.title) depuis la popup
- Fermer la popup (button[data-fancybox-close])
- Cliquer sur le bouton suivant (sur le même onglet) → nouvelle popup
- Boucler jusqu'à plus de boutons
"""

import os
import re
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet

# Exclusive codes sheet
EXCLUSIVE_SPREADSHEET_ID = "1YZQ9YPYmBuUZSIQgSVdjxmweNDAk0LK74PU5O4EAX2A"
EXCLUSIVE_SHEET_NAME = "Exclusive_Code"
EXCLUSIVE_PATTERN = re.compile(r'tylko u nas', re.IGNORECASE)


def scrape_rabatio_all(page, context, url):
    """
    Scrape TOUS les codes d'une page Rabatio avec Playwright.

    Flow:
    1. Cliquer sur le 1er bouton code → nouvel onglet s'ouvre
    2. Sur le nouvel onglet: popup fancybox avec code + titre
    3. Extraire span.code-text et .modal-header span.title
    4. Fermer la popup avec button[data-fancybox-close]
    5. Cliquer sur le bouton suivant (toujours sur le même onglet)
    6. Boucler jusqu'à plus de boutons
    """
    results = []

    try:
        print(f"[Rabatio] Accès à l'URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1000)

        # Accepter cookies - Cookiebot
        try:
            page.click("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll", timeout=1500)
            page.wait_for_timeout(300)
            print("[Rabatio] Cookie fermé")
        except:
            pass

        # === PRE-EXTRACT terms + expiry from listing page ===
        # Title is in data-offer-title on the <a> button
        # Expiry is in span.rabat__list-item--time (sibling of <a> in --button div)
        # Terms is in span.subtitle (in the --detail div, same parent container)
        title_extras = page.evaluate("""() => {
            var mapping = {};
            var buttons = document.querySelectorAll("a.js-get-coupon[data-action-type='show_code']");
            buttons.forEach(function(btn) {
                var title = btn.getAttribute('data-offer-title') || '';
                if (!title) return;
                var expiry = '';
                var terms = '';
                var buttonDiv = btn.closest('.rabat__list-item--button');
                if (buttonDiv) {
                    var timeEl = buttonDiv.querySelector('span.rabat__list-item--time');
                    if (timeEl) {
                        var match = timeEl.textContent.trim().match(/ważny do (\\d{2}\\.\\d{2}\\.\\d{4})/i);
                        if (match) expiry = match[1];
                    }
                }
                var container = btn.closest('.rabat__list-item') || (buttonDiv ? buttonDiv.parentElement : null);
                if (container) {
                    var subtitle = container.querySelector('span.subtitle');
                    if (subtitle) terms = subtitle.textContent.trim();
                }
                mapping[title] = {terms: terms, expiration_date: expiry};
            });
            return mapping;
        }""")
        if title_extras:
            print(f"[Rabatio] {len(title_extras)} terms/expiry pre-extracted")

        # Trouver les boutons code sur la page principale
        code_buttons = page.locator("xpath=//div[contains(@class, 'rabat__list-item--button') and not(.//span[contains(text(), 'wygasł')])]//a[contains(@class, 'js-get-coupon') and @data-action-type='show_code']")
        total_count = code_buttons.count()

        print(f"[Rabatio] {total_count} boutons code trouvés")

        if total_count == 0:
            return results

        processed_codes = set()
        processed_titles = set()

        # === STEP 1: Cliquer sur le 1er bouton pour ouvrir le nouvel onglet ===
        first_btn = code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(200)

        pages_before = len(context.pages)
        first_btn.click()
        page.wait_for_timeout(800)

        if len(context.pages) <= pages_before:
            print("[Rabatio] ⚠️ Pas de nouvel onglet ouvert")
            return results

        # Switch vers le nouvel onglet
        new_page = context.pages[-1]
        new_page.wait_for_timeout(500)

        # === STEP 2: Boucler sur le nouvel onglet ===
        max_iterations = min(total_count + 5, 25)

        for iteration in range(max_iterations):
            try:
                new_page.wait_for_timeout(500)

                # Extraire le code depuis span.code-text
                code = None
                try:
                    code_elem = new_page.locator("span.code-text").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                except:
                    pass

                # Extraire le titre depuis .modal-header span.title
                title = None
                try:
                    title_elem = new_page.locator(".modal-header span.title").first
                    if title_elem.count() > 0:
                        title = title_elem.inner_text().strip()
                except:
                    pass

                if code and title and code not in processed_codes and title not in processed_titles:
                    processed_codes.add(code)
                    processed_titles.add(title)
                    extras = title_extras.get(title, {})
                    results.append({
                        "code": code,
                        "title": title,
                        "terms": extras.get("terms", ""),
                        "expiration_date": extras.get("expiration_date", "")
                    })
                    print(f"[Rabatio] ✅ Code: {code} | {title[:50]}...")
                elif code and code in processed_codes:
                    print(f"[Rabatio] ⚠️ Code doublon: {code}")
                else:
                    print(f"[Rabatio] ⚠️ Code/titre non trouvé (code={code}, title={title})")

                # Fermer la popup fancybox
                try:
                    new_page.click("button[data-fancybox-close]", timeout=1500)
                    new_page.wait_for_timeout(300)
                except:
                    pass

                # Trouver le bouton suivant sur le nouvel onglet
                new_page.wait_for_timeout(200)
                next_buttons = new_page.locator("xpath=//div[contains(@class, 'rabat__list-item--button') and not(.//span[contains(text(), 'wygasł')])]//a[contains(@class, 'js-get-coupon') and @data-action-type='show_code']")
                current_index = len(results)

                if current_index >= next_buttons.count():
                    print("[Rabatio] Plus de boutons disponibles")
                    break

                next_btn = next_buttons.nth(current_index)
                next_btn.scroll_into_view_if_needed()
                new_page.wait_for_timeout(200)

                # Cliquer sur le bouton suivant
                pages_before = len(context.pages)
                next_btn.click()
                new_page.wait_for_timeout(500)

                # Si un nouveau tab s'ouvre, switcher dessus
                if len(context.pages) > pages_before:
                    new_page = context.pages[-1]
                    new_page.wait_for_timeout(300)

            except Exception as e:
                print(f"[Rabatio] ⚠️ Erreur itération {iteration}: {str(e)[:40]}")
                break

        # Fermer tous les onglets sauf le principal
        for p in context.pages[1:]:
            try:
                p.close()
            except:
                pass

        print(f"[Rabatio] Total: {len(results)} codes récupérés")

    except Exception as e:
        print(f"[Rabatio] ❌ Erreur générale: {str(e)[:50]}")

    return results


def append_exclusive_to_gsheet(results):
    """Append exclusive codes to the dedicated Exclusive_Code spreadsheet."""
    if not results:
        return 0

    import gspread
    from google.oauth2.service_account import Credentials

    _local_path = os.path.join(os.path.dirname(__file__), "..", "..", "credentials", "service_account.json")
    _cloud_path = "/app/credentials/service_account.json"
    creds_path = _cloud_path if os.path.exists(_cloud_path) else _local_path

    creds = Credentials.from_service_account_file(creds_path, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ])
    gc = gspread.authorize(creds)

    spreadsheet = gc.open_by_key(EXCLUSIVE_SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(EXCLUSIVE_SHEET_NAME)

    rows_to_add = []
    for r in results:
        rows_to_add.append([
            r.get("Date", ""),
            r.get("Country", ""),
            r.get("Merchant_ID", ""),
            r.get("Merchant_slug", ""),
            r.get("GPN_URL", ""),
            r.get("Competitor_Source", ""),
            r.get("Competitor_URL", ""),
            r.get("Code", ""),
            r.get("Title", ""),
            r.get("Terms", r.get("terms", "")),
            r.get("Expiry Date", r.get("expiration_date", "")),
            "",  # Actioned by
            ""   # Comments
        ])

    worksheet.append_rows(rows_to_add, value_input_option="USER_ENTERED")
    print(f"📤 {len(rows_to_add)} exclusive codes written to Exclusive_Code sheet")
    return len(rows_to_add)


def main():
    """Scrape Rabatio PL depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")

    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("PL", "rabatio")
    print(f"📍 Rabatio: {len(competitor_data)} URLs uniques")

    all_results = []
    all_exclusive = []

    print(f"\n🚀 Lancement de Playwright...")

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
                codes = scrape_rabatio_all(page, context, url)
                print(f"   ✅ {len(codes)} codes trouvés")

                for code_info in codes:
                    row = {
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "PL",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "rabatio",
                        "Competitor_URL": url,
                        "Code": code_info["code"],
                        "Title": code_info["title"],
                        "terms": code_info.get("terms", ""),
                        "expiration_date": code_info.get("expiration_date", "")
                    }
                    # Check if title contains "Tylko u nas" → exclusive
                    if EXCLUSIVE_PATTERN.search(code_info.get("title", "")):
                        all_exclusive.append(row)
                        print(f"   🔒 Exclusive: {code_info['code']}")
                    else:
                        all_results.append(row)
            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:50]}")

            print(f"   📝 Total: {len(all_results)} codes + {len(all_exclusive)} exclusive")

        browser.close()

    if all_results:
        append_to_gsheet(all_results, source_name="Rabatio PL")

        print(f"\n{'='*60}")
        print(f"✅ RABATIO PL TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")

    if all_exclusive:
        append_exclusive_to_gsheet(all_exclusive)
        print(f"🔒 {len(all_exclusive)} exclusive codes sent to Exclusive_Code sheet")
    else:
        print(f"⚠️ No exclusive codes found")


if __name__ == "__main__":
    main()
