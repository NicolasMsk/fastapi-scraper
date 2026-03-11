"""
Script Playwright pour scraper TOUS les codes CouponFollow (US)
- Clique sur "Show Coupon Code" -> nouvel onglet -> récupère code/titre/expiry -> ferme popup -> suivant
- Exclut les offres expirées (div.discount-box.ex) et les "Get Deal"
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_couponfollow_all(page, context, url):
    """Scrape tous les codes d'une page CouponFollow avec Playwright"""
    results = []

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # Fermer cookie banner si présent
        try:
            page.click("button:has-text('Accept'), button:has-text('Got it'), button:has-text('I agree')", timeout=3000)
            page.wait_for_timeout(500)
        except:
            pass

        # Trouver UNIQUEMENT les boutons "Show Coupon Code" (hors expirés avec div.discount-box.ex)
        code_buttons = page.locator("div.offer-card-box:not(:has(div.discount-box.ex)) a.btn-reveal.offer-cta:has(div.cover:has-text('Show Coupon Code'))")
        count = code_buttons.count()

        if count == 0:
            # Fallback sans filtre parent
            code_buttons = page.locator("a.btn-reveal.offer-cta:has(div.cover:has-text('Show Coupon Code'))")
            count = code_buttons.count()

        print(f"[CouponFollow] {count} boutons 'Show Coupon Code' trouvés (hors expirés)")

        if count == 0:
            return results

        processed_codes = set()
        processed_titles = set()

        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_btn = code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        with context.expect_page() as new_page_info:
            first_btn.click()

        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded")
        new_page.wait_for_timeout(2000)

        max_iterations = count + 5
        clicked_count = 0

        for iteration in range(max_iterations):
            new_page.wait_for_timeout(1500)

            code = None
            current_title = None
            expiration_date = ""
            terms = ""

            # 1. Récupérer le code depuis input#code
            try:
                code_input = new_page.locator("input#code").first
                if code_input.count() > 0:
                    code = code_input.get_attribute("value")
                    if code:
                        code = code.strip()
            except:
                pass

            if not code:
                # Fallback: chercher span.code[data-code]
                try:
                    code_elem = new_page.locator("span.code[data-code]").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                except:
                    pass

            # 2. Récupérer le titre depuis la popup
            try:
                title_elem = new_page.locator("div.offer-details span.text[data-description]").first
                if title_elem.count() > 0:
                    current_title = title_elem.inner_text().strip()
            except:
                pass

            if not current_title:
                try:
                    title_elems = new_page.locator("h3.offer-title")
                    if title_elems.count() > 0:
                        current_title = title_elems.first.inner_text().strip()
                except:
                    pass

            # 3. Récupérer l'expiration date
            try:
                exp_elem = new_page.locator("div.exp").first
                if exp_elem.count() > 0:
                    exp_text = exp_elem.inner_text().strip()
                    # Format: "Expiration Date: 3/11/2026"
                    if ":" in exp_text:
                        expiration_date = exp_text.split(":", 1)[1].strip()
            except:
                pass

            # 4. Récupérer les terms (description de l'offre)
            try:
                terms_elem = new_page.locator("div.offer-details span.text[data-description]").first
                if terms_elem.count() > 0:
                    terms = terms_elem.inner_text().strip()
            except:
                pass

            # Ajouter le résultat si code ET titre trouvés
            if code and current_title and len(code) >= 3 and code not in processed_codes and current_title not in processed_titles:
                processed_codes.add(code)
                processed_titles.add(current_title)
                results.append({
                    "code": code,
                    "title": current_title,
                    "expiration_date": expiration_date,
                    "terms": terms
                })
                print(f"[CouponFollow] Code: {code} | {current_title[:50]}...")
                print(f"[CouponFollow]    Expiry: {expiration_date if expiration_date else 'N/A'} | Terms: {'Yes' if terms else 'No'}")
            else:
                if not code:
                    print(f"[CouponFollow] Code non trouve")
                elif not current_title:
                    print(f"[CouponFollow] Titre non trouve (code: {code})")
                else:
                    print(f"[CouponFollow] Doublon ignore: {code}")

            # 5. Fermer la popup
            popup_closed = False
            try:
                close_btn = new_page.locator("button.close[data-close]").first
                if close_btn.count() > 0:
                    close_btn.click()
                    popup_closed = True
                    new_page.wait_for_timeout(500)
            except:
                pass

            if not popup_closed:
                try:
                    close_btn = new_page.locator("button[aria-label='close']").first
                    if close_btn.count() > 0:
                        close_btn.click()
                        popup_closed = True
                        new_page.wait_for_timeout(500)
                except:
                    pass

            # 6. Chercher le prochain bouton CODE sur cette page
            new_page.wait_for_timeout(500)

            next_buttons = new_page.locator("div.offer-card-box:not(:has(div.discount-box.ex)) a.btn-reveal.offer-cta:has(div.cover:has-text('Show Coupon Code'))")
            next_count = next_buttons.count()

            if next_count == 0:
                next_buttons = new_page.locator("a.btn-reveal.offer-cta:has(div.cover:has-text('Show Coupon Code'))")
                next_count = next_buttons.count()

            clicked_count += 1

            if clicked_count >= next_count:
                break

            # 7. Cliquer sur le bouton suivant
            next_btn = next_buttons.nth(clicked_count)
            try:
                next_btn.scroll_into_view_if_needed()
                new_page.wait_for_timeout(300)

                with context.expect_page() as next_page_info:
                    next_btn.click()

                next_new_page = next_page_info.value
                next_new_page.wait_for_load_state("domcontentloaded")
                new_page.close()
                new_page = next_new_page
                new_page.wait_for_timeout(1000)

            except Exception as e:
                print(f"[CouponFollow] Erreur clic suivant: {str(e)[:50]}")
                break

        try:
            new_page.close()
        except:
            pass

        print(f"[CouponFollow] Total: {len(results)} codes recuperes")

    except Exception as e:
        print(f"      Erreur: {str(e)[:50]}")

    return results


def main():
    """Scrape CouponFollow US depuis Google Sheets"""
    print(f"Chargement depuis Google Sheets...")

    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("US", "couponfollow")
    print(f"CouponFollow: {len(competitor_data)} URLs uniques")

    all_results = []

    print(f"\nLancement de Playwright...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = context.new_page()

        for idx, (merchant_row, url) in enumerate(competitor_data, 1):
            merchant_slug = merchant_row.get('Merchant_slug', 'Unknown')

            print(f"\n[{idx}/{len(competitor_data)}] {merchant_slug}")
            print(f"   URL: {url[:60]}...")

            # Créer une nouvelle page pour chaque marchand
            page = context.new_page()

            try:
                codes = scrape_couponfollow_all(page, context, url)
                print(f"   {len(codes)} codes trouves")

                for code_info in codes:
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "US",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "couponfollow",
                        "Competitor_URL": url,
                        "Code": code_info["code"],
                        "Title": code_info["title"],
                        "terms": code_info.get("terms", ""),
                        "expiration_date": code_info.get("expiration_date", "")
                    })
            except Exception as e:
                print(f"   Erreur: {str(e)[:50]}")

            # Fermer la page après chaque marchand
            try:
                page.close()
            except:
                pass

            # Fermer tous les onglets ouverts sauf le contexte
            for p_page in context.pages:
                try:
                    p_page.close()
                except:
                    pass

            print(f"   Total: {len(all_results)} codes")

        browser.close()

    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="CouponFollow US")

        print(f"\n{'='*60}")
        print(f"COUPONFOLLOW US TERMINE!")
        print(f"{len(all_results)} codes recuperes et envoyes a Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\nAucun code trouve")


if __name__ == "__main__":
    main()
