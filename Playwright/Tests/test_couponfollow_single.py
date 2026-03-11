"""
Test script pour CouponFollow US - Tester une seule URL
Workflow: clic sur "Show Coupon Code" -> nouvel onglet -> récupérer code/titre/expiry -> fermer popup -> suivant
"""

from playwright.sync_api import sync_playwright


def scrape_couponfollow_test(page, context, url):
    """Scrape tous les codes d'une page CouponFollow avec Playwright"""
    results = []

    try:
        print(f"[CouponFollow] Accès à l'URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # Fermer cookie banner si présent
        try:
            page.click("button:has-text('Accept'), button:has-text('Got it'), button:has-text('I agree')", timeout=3000)
            page.wait_for_timeout(500)
        except:
            pass

        # Pré-extraire les titres et filtrer les offres CODE uniquement (pas DEAL)
        # On récupère le mapping index → titre depuis la page listing
        title_data = page.evaluate("""() => {
            const cards = document.querySelectorAll('div.offer-card-box');
            const data = [];
            cards.forEach(card => {
                const insights = card.querySelector('div.insights');
                const isCode = insights && insights.textContent.includes('CODE');
                const titleEl = card.querySelector('h3.offer-title');
                const title = titleEl ? titleEl.textContent.trim() : '';
                data.push({title: title, isCode: isCode});
            });
            return data;
        }""")

        print(f"[CouponFollow] {len(title_data)} offres trouvées sur la page")
        code_offers = [d for d in title_data if d['isCode']]
        print(f"[CouponFollow] {len(code_offers)} offres CODE (hors DEAL)")

        # Trouver UNIQUEMENT les boutons "Show Coupon Code"
        # Exclure: "Get Deal", "See Coupon" (expirés avec div.discount-box.ex)
        code_buttons = page.locator("div.offer-card-box:not(:has(div.discount-box.ex)) a.btn-reveal.offer-cta:has(div.cover:has-text('Show Coupon Code'))")
        count = code_buttons.count()

        if count == 0:
            # Fallback sans filtre parent
            code_buttons = page.locator("a.btn-reveal.offer-cta:has(div.cover:has-text('Show Coupon Code'))")
            count = code_buttons.count()
            print(f"[CouponFollow] Fallback: {count} boutons trouvés")

        print(f"[CouponFollow] {count} boutons 'Show Coupon Code' trouvés (hors expirés)")

        if count == 0:
            print("[CouponFollow] Aucun code disponible sur cette page")
            return results

        processed_codes = set()
        processed_titles = set()

        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_btn = code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        # Récupérer le titre du premier code depuis la page listing
        first_title = None
        try:
            card = first_btn.locator("xpath=ancestor::div[contains(@class, 'offer-card-box')]")
            first_title = card.locator("h3.offer-title").first.inner_text().strip()
        except:
            pass

        if first_title:
            print(f"[CouponFollow] Clic sur le premier code: {first_title[:60]}...")
        else:
            print(f"[CouponFollow] Clic sur le premier code (titre non trouvé)")

        with context.expect_page() as new_page_info:
            first_btn.click()

        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded")
        new_page.wait_for_timeout(2000)

        print("[CouponFollow] Switché vers le nouvel onglet")

        max_iterations = count + 5
        clicked_count = 0

        for iteration in range(max_iterations):
            print(f"\n[CouponFollow] --- Itération {iteration + 1} ---")

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
                    print(f"[CouponFollow] Code trouvé via input#code: {code}")
            except:
                pass

            if not code:
                # Fallback: chercher span.code[data-code]
                try:
                    code_elem = new_page.locator("span.code[data-code]").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                        print(f"[CouponFollow] Code trouvé via span.code: {code}")
                except:
                    pass

            # 2. Récupérer le titre depuis la popup (h3.heading ou offer-title)
            try:
                # Chercher le titre dans la popup - utiliser le texte de description comme titre
                title_elem = new_page.locator("div.offer-details span.text[data-description]").first
                if title_elem.count() > 0:
                    current_title = title_elem.inner_text().strip()
                    print(f"[CouponFollow] Titre trouvé: {current_title[:60]}...")
            except:
                pass

            if not current_title:
                # Fallback: chercher h3.offer-title sur la page
                try:
                    title_elems = new_page.locator("h3.offer-title")
                    if title_elems.count() > 0:
                        current_title = title_elems.first.inner_text().strip()
                        print(f"[CouponFollow] Titre trouvé via h3.offer-title: {current_title[:60]}...")
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
                    print(f"[CouponFollow] Expiry: {expiration_date}")
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
                print(f"[CouponFollow] ✅ Code: {code} -> {current_title[:50]}...")
                if expiration_date:
                    print(f"[CouponFollow]    📅 Expiry: {expiration_date}")
                if terms:
                    print(f"[CouponFollow]    📋 Terms: {terms[:60]}...")
            else:
                if not code:
                    print(f"[CouponFollow] ⚠️ Code non trouvé")
                elif not current_title:
                    print(f"[CouponFollow] ⚠️ Titre non trouvé (code: {code})")
                else:
                    print(f"[CouponFollow] ⚠️ Doublon ignoré: {code}")

            # 5. Fermer la popup
            popup_closed = False
            try:
                close_btn = new_page.locator("button.close[data-close]").first
                if close_btn.count() > 0:
                    close_btn.click()
                    popup_closed = True
                    print("[CouponFollow] Popup fermée via button.close")
                    new_page.wait_for_timeout(500)
            except:
                pass

            if not popup_closed:
                try:
                    close_btn = new_page.locator("button[aria-label='close']").first
                    if close_btn.count() > 0:
                        close_btn.click()
                        popup_closed = True
                        print("[CouponFollow] Popup fermée via aria-label")
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
                print("[CouponFollow] Plus de boutons disponibles")
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
                print(f"[CouponFollow] Switché vers nouvel onglet pour code {clicked_count + 1}")
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

        print(f"\n[CouponFollow] Total: {len(results)} codes récupérés")

    except Exception as e:
        print(f"[CouponFollow] ❌ Erreur générale: {str(e)[:80]}")

    return results


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    test_url = "https://couponfollow.com/site/carters.com"

    print(f"Test CouponFollow US")
    print(f"URL: {test_url}")
    print(f"{'='*60}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        results = scrape_couponfollow_test(page, context, test_url)

        print(f"\n{'='*60}")
        print(f"📊 RÉSULTATS: {len(results)} codes")
        print(f"{'='*60}")
        for i, r in enumerate(results, 1):
            print(f"\n  [{i}] Code: {r['code']}")
            print(f"      Titre: {r['title'][:80]}...")
            if r.get('expiration_date'):
                print(f"      Expiry: {r['expiration_date']}")
            if r.get('terms'):
                print(f"      Terms: {r['terms'][:80]}...")

        browser.close()
