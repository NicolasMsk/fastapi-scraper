"""
Script Playwright pour scraper TOUS les codes Rabatio (Pologne)
- Cliquer sur le 1er bouton "Kod" → nouvel onglet s'ouvre avec popup fancybox
- Extraire code (span.code-text) et titre (span.title) depuis la popup
- Fermer la popup (button[data-fancybox-close])
- Cliquer sur le bouton suivant (sur le même onglet) → nouvelle popup
- Boucler jusqu'à plus de boutons
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


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
        page.wait_for_timeout(2500)

        # Accepter cookies - Cookiebot
        try:
            page.click("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll", timeout=3000)
            page.wait_for_timeout(500)
            print("[Rabatio] Cookie fermé")
        except:
            pass

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
        page.wait_for_timeout(300)

        pages_before = len(context.pages)
        first_btn.click()
        page.wait_for_timeout(1500)

        if len(context.pages) <= pages_before:
            print("[Rabatio] ⚠️ Pas de nouvel onglet ouvert")
            return results

        # Switch vers le nouvel onglet
        new_page = context.pages[-1]
        new_page.wait_for_timeout(1000)

        # === STEP 2: Boucler sur le nouvel onglet ===
        max_iterations = min(total_count + 5, 25)

        for iteration in range(max_iterations):
            try:
                new_page.wait_for_timeout(1000)

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
                    results.append({"code": code, "title": title})
                    print(f"[Rabatio] ✅ Code: {code} | {title[:50]}...")
                elif code and code in processed_codes:
                    print(f"[Rabatio] ⚠️ Code doublon: {code}")
                else:
                    print(f"[Rabatio] ⚠️ Code/titre non trouvé (code={code}, title={title})")

                # Fermer la popup fancybox
                try:
                    new_page.click("button[data-fancybox-close]", timeout=2000)
                    new_page.wait_for_timeout(500)
                except:
                    pass

                # Trouver le bouton suivant sur le nouvel onglet
                new_page.wait_for_timeout(300)
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
                new_page.wait_for_timeout(1000)

                # Si un nouveau tab s'ouvre, switcher dessus
                if len(context.pages) > pages_before:
                    new_page = context.pages[-1]
                    new_page.wait_for_timeout(500)

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


def main():
    """Scrape Rabatio PL depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")

    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("PL", "rabatio")
    print(f"📍 Rabatio: {len(competitor_data)} URLs uniques")

    all_results = []

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
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "PL",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "rabatio",
                        "Competitor_URL": url,
                        "Code": code_info["code"],
                        "Title": code_info["title"]
                    })
            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:50]}")

            print(f"   📝 Total: {len(all_results)} codes")

        browser.close()

    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="Rabatio PL")

        print(f"\n{'='*60}")
        print(f"✅ RABATIO PL TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")


if __name__ == "__main__":
    main()
