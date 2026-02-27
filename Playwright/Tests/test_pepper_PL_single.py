"""
Test Pepper PL sur une seule URL pour debug
"""

from playwright.sync_api import sync_playwright


def test_pepper_pl_single(url):
    """Test scraping sur une seule URL Pepper PL"""
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        try:
            print(f"[Pepper PL] Accès à l'URL: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)

            # Fermer popups cookies
            try:
                page.click("button:has-text('Accept'), button:has-text('Agree'), button:has-text('Akceptuj'), #onetrust-accept-btn-handler", timeout=2000)
                page.wait_for_timeout(500)
            except:
                pass

            # XPath pour trouver les boutons "Pokaż kod" VALIDES
            xpath_valid_codes = """
                //div[@data-testid='vouchers-ui-voucher-card-description'][.//h3]
                    [not(ancestor::div[contains(@class, '_1hla7140')])]
                    [not(ancestor::div[contains(@class, 'jkau50') and .//h2[contains(text(), 'expired') or contains(text(), 'wygasł')]])]
                    [not(ancestor::div[@data-testid='vouchers-ui-voucher-card']//div[contains(text(), 'Exclusive')])]
                //div[@role='button' and (contains(@title, 'See Code') or contains(@title, 'Zobacz kod') or contains(@title, 'Pokaż kod'))]
            """.replace('\n', '').replace('    ', '')

            see_code_buttons = page.locator(f"xpath={xpath_valid_codes}")
            total_count = see_code_buttons.count()

            print(f"[Pepper PL] {total_count} boutons valides trouvés")

            if total_count == 0:
                print("[Pepper PL] Aucun code disponible")
                browser.close()
                return results

            processed_codes = set()
            processed_titles = set()

            # Cliquer sur le premier bouton
            first_btn = see_code_buttons.first
            first_btn.scroll_into_view_if_needed()
            page.wait_for_timeout(300)

            pages_before = len(context.pages)
            page.evaluate("(el) => el.click()", first_btn.element_handle())
            page.wait_for_timeout(1000)

            if len(context.pages) <= pages_before:
                print("[Pepper PL] Aucun nouvel onglet ouvert")
                browser.close()
                return results

            new_page = context.pages[-1]
            print("[Pepper PL] Switché vers le nouvel onglet")
            new_page.wait_for_timeout(1000)

            max_iterations = min(total_count + 5, 25)

            for iteration in range(max_iterations):
                print(f"\n[Pepper PL] --- Itération {iteration + 1} ---")

                try:
                    new_page.wait_for_timeout(1000)

                    # Extraire le code (h4 avec classe b8qpi*)
                    code = None
                    try:
                        code_elem = new_page.locator("h4[class*='b8qpi']").first
                        if code_elem.count() > 0:
                            code = code_elem.inner_text().strip()
                            print(f"[Pepper PL] Code trouvé via h4.b8qpi: {code}")
                    except:
                        pass

                    if not code:
                        try:
                            h4_elems = new_page.locator("h4")
                            for i in range(h4_elems.count()):
                                text = h4_elems.nth(i).inner_text().strip()
                                print(f"[Pepper PL]   h4[{i}]: '{text}'")
                                if text and 3 <= len(text) <= 30 and text not in processed_codes:
                                    code = text
                                    break
                        except:
                            pass

                    # Extraire le titre (h4 avec az57m mais PAS b8qpi)
                    current_title = None
                    try:
                        title_elems = new_page.locator("xpath=//h4[contains(@class, 'az57m') and not(contains(@class, 'b8qpi'))]")
                        if title_elems.count() > 0:
                            current_title = title_elems.first.inner_text().strip()
                            print(f"[Pepper PL] Titre popup: {current_title[:60]}...")
                    except:
                        pass

                    if not current_title:
                        try:
                            h3_elems = new_page.locator("div[data-testid='vouchers-ui-voucher-card-description'] h3")
                            idx = len(results)
                            if h3_elems.count() > idx:
                                current_title = h3_elems.nth(idx).inner_text().strip()
                        except:
                            pass

                    if code and current_title and code not in processed_codes and current_title not in processed_titles:
                        processed_codes.add(code)
                        processed_titles.add(current_title)
                        results.append({"code": code, "title": current_title})
                        print(f"[Pepper PL] ✅ Code: {code} | {current_title[:50]}...")
                    else:
                        print(f"[Pepper PL] ⚠️ Code non trouvé ou doublon: {code}")

                    # Fermer la popup
                    try:
                        close_icon = new_page.locator("span[data-testid='CloseIcon'], svg[data-testid='CloseIcon']").first
                        if close_icon.count() > 0:
                            close_icon.click(timeout=2000)
                            new_page.wait_for_timeout(500)
                    except:
                        pass

                    # Bouton suivant
                    new_page.wait_for_timeout(300)

                    xpath_next = """
                        //div[@data-testid='vouchers-ui-voucher-card-description'][.//h3]
                            [not(ancestor::div[contains(@class, '_1hla7140')])]
                            [not(ancestor::div[contains(@class, 'jkau50') and .//h2[contains(text(), 'expired') or contains(text(), 'wygasł')]])]
                            [not(ancestor::div[@data-testid='vouchers-ui-voucher-card']//div[contains(text(), 'Exclusive')])]
                        //div[@role='button' and (contains(@title, 'See Code') or contains(@title, 'Zobacz kod') or contains(@title, 'Pokaż kod'))]
                    """.replace('\n', '').replace('    ', '')

                    next_buttons = new_page.locator(f"xpath={xpath_next}")
                    current_index = len(results)

                    print(f"[Pepper PL] Boutons restants: {next_buttons.count()}, index: {current_index}")

                    if current_index >= next_buttons.count():
                        print("[Pepper PL] Plus de boutons disponibles")
                        break

                    next_btn = next_buttons.nth(current_index)
                    next_btn.scroll_into_view_if_needed()
                    new_page.wait_for_timeout(200)

                    pages_before = len(context.pages)
                    new_page.evaluate("(el) => el.click()", next_btn.element_handle())
                    new_page.wait_for_timeout(1000)

                    if len(context.pages) > pages_before:
                        new_page = context.pages[-1]
                        new_page.wait_for_timeout(500)

                except Exception as e:
                    print(f"[Pepper PL] Erreur: {str(e)[:40]}")
                    break

            for p in context.pages[1:]:
                try:
                    p.close()
                except:
                    pass

        except Exception as e:
            print(f"[Pepper PL] ❌ Erreur générale: {str(e)}")

        browser.close()

    return results


if __name__ == "__main__":
    test_url = "https://www.pepper.pl/kupony/nike.com"

    print("=" * 60)
    print("TEST SCRAPER PEPPER PL - SINGLE URL")
    print(f"URL: {test_url}")
    print("=" * 60)

    results = test_pepper_pl_single(test_url)

    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes trouvés")
    print("=" * 60)
    for i, r in enumerate(results):
        print(f"  [{i+1}] Code: {r['code']} -> {r['title'][:50]}...")
    print("=" * 60)
