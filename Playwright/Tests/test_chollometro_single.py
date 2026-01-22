"""
Test Chollometro sur une seule URL pour debug
"""

from playwright.sync_api import sync_playwright
import time


def test_chollometro_single(url):
    """Test scraping sur une seule URL Chollometro"""
    results = []
    start_time = time.time()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False pour voir
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            print(f"[Chollometro] Accès à l'URL: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)
            
            # Accepter cookies
            try:
                page.click("button:has-text('Aceptar'), button:has-text('Accept')", timeout=2000)
                page.wait_for_timeout(500)
            except:
                pass
            
            # Fermer popups
            try:
                page.click("button[aria-label='Close'], button[aria-label='close'], button[aria-label='cerrar']", timeout=1000)
            except:
                pass
            
            # Trouver les boutons "Ver cupón" VALIDES (pas expirés, pas autres marchands)
            see_code_buttons = page.locator("xpath=//div[@role='button'][@title='Ver cupón'][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]")
            count = see_code_buttons.count()
            
            if count == 0:
                see_code_buttons = page.locator("xpath=//div[@role='button'][@title='Ver cupón'][not(ancestor::div[contains(@class, 'jkau50')])]")
                count = see_code_buttons.count()
            
            if count == 0:
                print("[Chollometro] Aucun code disponible")
                browser.close()
                return results
            
            print(f"[Chollometro] {count} boutons 'Ver cupón' trouvés")
            
            processed_codes = set()
            processed_titles = set()
            
            # Cliquer sur le premier bouton
            first_btn = see_code_buttons.first
            first_btn.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            
            with context.expect_page() as new_page_info:
                first_btn.click()
            
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded")
            new_page.wait_for_timeout(1000)
            
            print("[Chollometro] Switché vers le nouvel onglet")
            
            max_iterations = count + 5
            
            for iteration in range(max_iterations):
                print(f"\n[Chollometro] --- Itération {iteration + 1} ---")
                
                new_page.wait_for_timeout(1000)
                
                code = None
                current_title = None
                
                # 1. Récupérer le code (h4.b8qpi79 ou h4[class*='b8qpi'])
                try:
                    code_elem = new_page.locator("h4.b8qpi79, h4[class*='b8qpi7']").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                        print(f"[Chollometro] Code trouvé: {code}")
                except:
                    pass
                
                if not code:
                    try:
                        h4_elems = new_page.locator("h4")
                        for i in range(h4_elems.count()):
                            text = h4_elems.nth(i).inner_text().strip()
                            if text and 3 <= len(text) <= 30 and text not in processed_codes:
                                code = text
                                print(f"[Chollometro] Code (fallback h4): {code}")
                                break
                    except:
                        pass
                
                # 2. Récupérer le titre (h4.az57m40.az57m46 SANS b8qpi79)
                try:
                    title_elems = new_page.locator("h4.az57m40.az57m46")
                    for i in range(title_elems.count()):
                        elem = title_elems.nth(i)
                        classes = elem.get_attribute("class") or ""
                        if "b8qpi79" not in classes:
                            text = elem.inner_text().strip()
                            if text and len(text) > 10:
                                current_title = text
                                print(f"[Chollometro] Titre trouvé: {current_title[:50]}...")
                                break
                except:
                    pass
                
                # Ajouter si code ET titre trouvés
                if code and current_title and code not in processed_codes and current_title not in processed_titles:
                    processed_codes.add(code)
                    processed_titles.add(current_title)
                    results.append({"code": code, "title": current_title})
                    print(f"[Chollometro] ✅ Code: {code} -> {current_title[:40]}...")
                else:
                    print(f"[Chollometro] ⚠️ Code/titre non trouvé ou doublon")
                
                # 3. Fermer la popup
                try:
                    close_icon = new_page.locator("span[data-testid='CloseIcon']").first
                    if close_icon.count() > 0:
                        close_icon.click()
                        print("[Chollometro] Popup fermée")
                        new_page.wait_for_timeout(500)
                except:
                    pass
                
                # 4. Chercher le prochain bouton
                new_page.wait_for_timeout(300)
                
                next_buttons = new_page.locator("div[data-testid='vouchers-ui-voucher-card-description']:has(h3) div[role='button'][title='Ver cupón']")
                next_count = next_buttons.count()
                
                if next_count == 0:
                    next_buttons = new_page.locator("div[role='button'][title='Ver cupón']")
                    next_count = next_buttons.count()
                
                current_index = len(results)
                print(f"[Chollometro] Boutons restants: {next_count}, index: {current_index}")
                
                if current_index >= next_count:
                    print("[Chollometro] Plus de boutons disponibles")
                    break
                
                # 5. Cliquer sur le bouton suivant
                next_btn = next_buttons.nth(current_index)
                try:
                    next_btn.scroll_into_view_if_needed()
                    new_page.wait_for_timeout(200)
                    
                    with context.expect_page() as next_page_info:
                        next_btn.click()
                    
                    next_new_page = next_page_info.value
                    next_new_page.wait_for_load_state("domcontentloaded")
                    print(f"[Chollometro] Switché vers nouvel onglet")
                    new_page.close()
                    new_page = next_new_page
                    new_page.wait_for_timeout(500)
                    
                except Exception as e:
                    print(f"[Chollometro] Erreur clic suivant: {str(e)[:30]}")
                    break
            
            try:
                new_page.close()
            except:
                pass
            
        except Exception as e:
            print(f"[Chollometro] ❌ Erreur: {str(e)}")
        
        browser.close()
    
    elapsed = time.time() - start_time
    return results, elapsed


if __name__ == "__main__":
    # Test avec une URL Chollometro
    test_url = "https://www.chollometro.com/cupones/shop.dyson.es"
    
    print("=" * 60)
    print("TEST CHOLLOMETRO - SINGLE URL")
    print(f"URL: {test_url}")
    print("=" * 60)
    
    results, elapsed = test_chollometro_single(test_url)
    
    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes en {elapsed:.1f}s")
    print("=" * 60)
    for i, r in enumerate(results):
        print(f"  [{i+1}] {r['code']} -> {r['title'][:50]}...")
    print("=" * 60)
