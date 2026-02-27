"""
Test Rabatio PL sur une seule URL pour debug
- 1er clic → nouvel onglet → popup fancybox
- Boucle: extraire code/titre → fermer popup → clic suivant → nouvelle popup
"""

from playwright.sync_api import sync_playwright


def test_rabatio_pl_single(url):
    """Test scraping sur une seule URL Rabatio PL"""
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

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
                browser.close()
                return results

            processed_codes = set()
            processed_titles = set()

            # STEP 1: Cliquer sur le 1er bouton → nouvel onglet
            first_btn = code_buttons.first
            first_btn.scroll_into_view_if_needed()
            page.wait_for_timeout(300)

            pages_before = len(context.pages)
            first_btn.click()
            page.wait_for_timeout(1500)

            if len(context.pages) <= pages_before:
                print("[Rabatio] ⚠️ Pas de nouvel onglet ouvert")
                browser.close()
                return results

            new_page = context.pages[-1]
            new_page.wait_for_timeout(1000)

            # STEP 2: Boucler sur le nouvel onglet
            max_iterations = min(total_count + 5, 25)

            for iteration in range(max_iterations):
                print(f"\n[Rabatio] --- Itération {iteration + 1} ---")

                try:
                    new_page.wait_for_timeout(1000)

                    # Extraire le code depuis span.code-text
                    code = None
                    try:
                        code_elem = new_page.locator("span.code-text").first
                        if code_elem.count() > 0:
                            code = code_elem.inner_text().strip()
                            print(f"[Rabatio] Code trouvé: {code}")
                    except:
                        pass

                    # Extraire le titre depuis .modal-header span.title
                    title = None
                    try:
                        title_elem = new_page.locator(".modal-header span.title").first
                        if title_elem.count() > 0:
                            title = title_elem.inner_text().strip()
                            print(f"[Rabatio] Titre trouvé: {title[:60]}...")
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

                    # Trouver le bouton suivant
                    new_page.wait_for_timeout(300)
                    next_buttons = new_page.locator("xpath=//div[contains(@class, 'rabat__list-item--button') and not(.//span[contains(text(), 'wygasł')])]//a[contains(@class, 'js-get-coupon') and @data-action-type='show_code']")
                    current_index = len(results)

                    print(f"[Rabatio] Boutons restants: {next_buttons.count()}, index: {current_index}")

                    if current_index >= next_buttons.count():
                        print("[Rabatio] Plus de boutons disponibles")
                        break

                    next_btn = next_buttons.nth(current_index)
                    next_btn.scroll_into_view_if_needed()
                    new_page.wait_for_timeout(200)

                    pages_before = len(context.pages)
                    next_btn.click()
                    new_page.wait_for_timeout(1000)

                    # Si un nouveau tab s'ouvre, switcher dessus
                    if len(context.pages) > pages_before:
                        new_page = context.pages[-1]
                        new_page.wait_for_timeout(500)

                except Exception as e:
                    print(f"[Rabatio] ⚠️ Erreur: {str(e)[:40]}")
                    break

            # Fermer tous les onglets sauf le principal
            for pg in context.pages[1:]:
                try:
                    pg.close()
                except:
                    pass

            print(f"\n[Rabatio] Total: {len(results)} codes récupérés")

        except Exception as e:
            print(f"[Rabatio] ❌ Erreur générale: {str(e)}")

        browser.close()

    return results


if __name__ == "__main__":
    test_url = "https://rabatio.com/sklepy/nike"

    print("=" * 60)
    print("TEST SCRAPER RABATIO PL - SINGLE URL")
    print(f"URL: {test_url}")
    print("=" * 60)

    results = test_rabatio_pl_single(test_url)

    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes trouvés")
    print("=" * 60)
    for i, r in enumerate(results):
        print(f"  [{i+1}] Code: {r['code']} -> {r['title'][:50]}...")
    print("=" * 60)
