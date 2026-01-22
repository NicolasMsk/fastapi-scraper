"""
Test Cuponation Australie sur une seule URL pour debug
"""

from playwright.sync_api import sync_playwright


def test_cuponation_au_single(url):
    """Test scraping sur une seule URL Cuponation AU"""
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False pour voir ce qui se passe
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            print(f"[Cuponation AU] Accès à l'URL: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2500)  # Optimisé: 4000 -> 2500
            
            # Accepter cookies
            try:
                page.click("button:has-text('Accept'), button:has-text('Agree'), #onetrust-accept-btn-handler", timeout=3000)
                page.wait_for_timeout(500)  # Optimisé: 1000 -> 500
            except:
                pass
            
            # ===================================================================
            # Trouver les boutons "See code" (AU) - EXCLURE expirés (jkau50)
            # ===================================================================
            
            # Essayer "See code" (AU)
            xpath_buttons = "//div[@role='button'][@title='See code'][not(ancestor::div[contains(@class, 'jkau5')])]"
            get_code_buttons = page.locator(f"xpath={xpath_buttons}")
            total_count = get_code_buttons.count()
            
            print(f"[Cuponation AU] Boutons 'See code' trouvés: {total_count}")
            
            if total_count == 0:
                # Essayer avec title contenant "code"
                xpath_buttons = "//div[@role='button'][contains(translate(@title, 'CODE', 'code'), 'code')][not(ancestor::div[contains(@class, 'jkau5')])]"
                get_code_buttons = page.locator(f"xpath={xpath_buttons}")
                total_count = get_code_buttons.count()
                print(f"[Cuponation AU] Fallback - boutons 'code' trouvés: {total_count}")
            
            if total_count == 0:
                print("[Cuponation AU] Aucun code disponible pour ce marchand")
                browser.close()
                return results
            
            processed_codes = set()
            
            # === ÉTAPE 1: Cliquer sur le premier bouton pour ouvrir le nouvel onglet ===
            first_btn = get_code_buttons.first
            first_btn.scroll_into_view_if_needed()
            page.wait_for_timeout(300)  # Optimisé: 500 -> 300
            
            # Récupérer le titre du premier code
            try:
                card = first_btn.locator("xpath=ancestor::div[@data-testid='vouchers-ui-voucher-card']")
                first_title = card.locator("h3").first.inner_text().strip()
            except:
                first_title = "Offer 1"
            
            print(f"[Cuponation AU] Clic sur le premier code: {first_title[:50]}...")
            
            # Cliquer avec JavaScript
            pages_before = len(context.pages)
            page.evaluate("(el) => el.click()", first_btn.element_handle())
            page.wait_for_timeout(1500)  # Optimisé: 2000 -> 1500
            
            if len(context.pages) <= pages_before:
                print("[Cuponation AU] Aucun nouvel onglet ouvert, essai avec click direct...")
                try:
                    with context.expect_page(timeout=5000) as new_page_info:
                        first_btn.click()
                    new_page = new_page_info.value
                except:
                    print("[Cuponation AU] Échec - pas de nouvel onglet")
                    browser.close()
                    return results
            else:
                new_page = context.pages[-1]
            
            print("[Cuponation AU] Switché vers le nouvel onglet")
            new_page.wait_for_timeout(1500)  # Optimisé: 2000 -> 1500
            
            # === ÉTAPE 2: Boucle sur le nouvel onglet ===
            max_iterations = min(total_count + 5, 25)
            
            for iteration in range(max_iterations):
                print(f"\n[Cuponation AU] --- Itération {iteration + 1} ---")
                
                new_page.wait_for_timeout(1500)  # Optimisé: 2000 -> 1500
                
                # 1. Récupérer le code (h4 avec classe b8qpi*)
                code = None
                try:
                    code_elem = new_page.locator("h4[class*='b8qpi']").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                        print(f"[Cuponation AU] Code trouvé via h4.b8qpi: {code}")
                except:
                    pass
                
                if not code:
                    # Fallback: tous les h4
                    try:
                        h4_elems = new_page.locator("h4")
                        for i in range(h4_elems.count()):
                            text = h4_elems.nth(i).inner_text().strip()
                            print(f"[Cuponation AU]   h4[{i}]: '{text}'")
                            if text and 3 <= len(text) <= 30 and text not in processed_codes:
                                code = text
                                print(f"[Cuponation AU] Code sélectionné: {code}")
                                break
                    except:
                        pass
                
                # 2. Récupérer le titre (h4 avec az57m mais PAS b8qpi)
                current_title = None
                try:
                    title_elems = new_page.locator("xpath=//h4[contains(@class, 'az57m') and not(contains(@class, 'b8qpi'))]")
                    if title_elems.count() > 0:
                        current_title = title_elems.first.inner_text().strip()
                        print(f"[Cuponation AU] Titre popup: {current_title[:60]}...")
                except:
                    pass
                
                if not current_title:
                    current_title = f"Offer {iteration + 1}"
                
                if code and code not in processed_codes:
                    processed_codes.add(code)
                    results.append({
                        "code": code,
                        "title": current_title
                    })
                    print(f"[Cuponation AU] ✅ Code: {code} -> {current_title[:40]}...")
                else:
                    print(f"[Cuponation AU] ⚠️ Code non trouvé ou doublon: {code}")
                
                # 3. Fermer la popup (span avec data-testid='CloseIcon')
                try:
                    close_icon = new_page.locator("span[data-testid='CloseIcon'], svg[data-testid='CloseIcon']").first
                    if close_icon.count() > 0:
                        close_icon.click(timeout=3000)
                        print("[Cuponation AU] Popup fermée")
                        new_page.wait_for_timeout(500)  # Optimisé: 1000 -> 500
                except Exception as e:
                    print(f"[Cuponation AU] ⚠️ Erreur fermeture popup: {str(e)[:30]}")
                
                # 4. Chercher le prochain bouton SUR CE NOUVEL ONGLET
                new_page.wait_for_timeout(300)  # Optimisé: 500 -> 300
                
                xpath_next = "//div[@role='button'][@title='See code'][not(ancestor::div[contains(@class, 'jkau5')])]"
                next_buttons = new_page.locator(f"xpath={xpath_next}")
                next_count = next_buttons.count()
                
                if next_count == 0:
                    xpath_next = "//div[@role='button'][contains(translate(@title, 'CODE', 'code'), 'code')][not(ancestor::div[contains(@class, 'jkau5')])]"
                    next_buttons = new_page.locator(f"xpath={xpath_next}")
                    next_count = next_buttons.count()
                
                current_index = len(results)
                print(f"[Cuponation AU] Boutons restants: {next_count}, index actuel: {current_index}")
                
                if current_index >= next_count:
                    print("[Cuponation AU] Plus de boutons 'See code' disponibles")
                    break
                
                # 5. Cliquer sur le bouton suivant
                next_btn = next_buttons.nth(current_index)
                try:
                    next_btn.scroll_into_view_if_needed()
                    new_page.wait_for_timeout(200)  # Optimisé: 300 -> 200
                    
                    pages_before = len(context.pages)
                    new_page.evaluate("(el) => el.click()", next_btn.element_handle())
                    new_page.wait_for_timeout(1500)  # Optimisé: 2000 -> 1500
                    
                    # Si un nouvel onglet s'est ouvert, switcher
                    if len(context.pages) > pages_before:
                        new_page = context.pages[-1]
                        print(f"[Cuponation AU] Switché vers nouvel onglet pour code {current_index + 1}")
                        new_page.wait_for_timeout(800)  # Optimisé: 1000 -> 800
                    
                except Exception as e:
                    print(f"[Cuponation AU] Erreur clic suivant: {str(e)[:30]}")
                    break
            
            # Fermer les onglets
            for p in context.pages[1:]:
                try:
                    p.close()
                except:
                    pass
            
        except Exception as e:
            print(f"[Cuponation AU] ❌ Erreur générale: {str(e)}")
        
        browser.close()
    
    return results


if __name__ == "__main__":
    test_url = "https://www.cuponation.com.au/rebelsport-coupons"
    
    print("=" * 60)
    print("TEST SCRAPER CUPONATION AU - SINGLE URL")
    print(f"URL: {test_url}")
    print("=" * 60)
    
    results = test_cuponation_au_single(test_url)
    
    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes trouvés")
    print("=" * 60)
    for i, r in enumerate(results):
        print(f"  [{i+1}] Code: {r['code']} -> {r['title'][:50]}...")
    print("=" * 60)
