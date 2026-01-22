"""
Test script pour Cuponation IT - Test sur une seule URL
Filtre les offres avec "Codice" uniquement (pas "Offerta")
"""

from playwright.sync_api import sync_playwright
import time

# URL de test
TEST_URL = "https://www.cuponation.it/codice-sconto-shein"

def test_cuponation_it_single():
    start_time = time.time()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        print(f"[TEST] Navigation vers {TEST_URL}")
        page.goto(TEST_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        print("[TEST] Page chargée")
        
        # Accepter cookies
        try:
            cookie_btn = page.locator("button:has-text('Accetta'), button:has-text('Accept')")
            if cookie_btn.count() > 0:
                cookie_btn.first.click()
                page.wait_for_timeout(500)
                print("[TEST] Cookies acceptés")
        except:
            pass
        
        # Trouver les boutons avec "Codice" uniquement (pas "Offerta")
        # Exclure expirés (jkau50) et similaires (_1hla7140)
        get_code_buttons = page.locator(
            "xpath=//div[@data-testid='vouchers-ui-voucher-card'][.//div[contains(text(), 'Codice')]][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])][not(ancestor::div[@data-testid='similar-vouchers-widget'])]//div[contains(@class, 'p24wo04')]"
        )
        count = get_code_buttons.count()
        print(f"[TEST] Boutons 'Codice' (hors expirés): {count}")
        
        if count == 0:
            get_code_buttons = page.locator(
                "xpath=//div[contains(@class, '_6tavko6')][.//div[contains(text(), 'Codice')]][not(ancestor::div[contains(@class, 'jkau50')])]//div[contains(@class, 'p24wo04')]"
            )
            count = get_code_buttons.count()
            print(f"[TEST] Fallback: {count}")
        
        if count == 0:
            print("[TEST] ❌ Aucun bouton trouvé!")
            browser.close()
            return []
        
        results = []
        processed_codes = set()
        processed_titles = set()
        max_codes = 5
        
        # Premier clic
        first_btn = get_code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        
        print("[TEST] Clic sur le premier bouton...")
        with context.expect_page() as new_page_info:
            first_btn.click()
        
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded")
        new_page.wait_for_timeout(1500)
        print(f"[TEST] Nouvel onglet ouvert")
        
        # Boucle d'extraction
        for iteration in range(min(max_codes, count)):
            print(f"\n[TEST] ========== ITERATION {iteration + 1} ==========")
            
            new_page.wait_for_timeout(1500)
            
            code = None
            current_title = None
            
            # 1. Récupérer le code
            try:
                code_elem = new_page.locator("h4.b8qpi79").first
                if code_elem.count() > 0:
                    code = code_elem.inner_text().strip()
                    print(f"[TEST] Code: {code}")
            except:
                pass
            
            if not code:
                try:
                    code_elems = new_page.locator("h4[class*='b8qpi7']")
                    for i in range(code_elems.count()):
                        text = code_elems.nth(i).inner_text().strip()
                        if text and 3 <= len(text) <= 30:
                            code = text
                            print(f"[TEST] Code fallback: {code}")
                            break
                except:
                    pass
            
            # 2. Récupérer le titre
            try:
                title_elems = new_page.locator("h4.az57m40.az57m46")
                for i in range(title_elems.count()):
                    elem = title_elems.nth(i)
                    classes = elem.get_attribute("class") or ""
                    if "b8qpi79" not in classes:
                        text = elem.inner_text().strip()
                        if text and len(text) > 10:
                            current_title = text
                            print(f"[TEST] Titre: {current_title[:50]}...")
                            break
            except:
                pass
            
            # Valider et ajouter
            if code and current_title and len(code) >= 3 and code not in processed_codes and current_title not in processed_titles:
                processed_codes.add(code)
                processed_titles.add(current_title)
                results.append({"code": code, "title": current_title})
                print(f"[TEST] ✅ AJOUTÉ: {code}")
            else:
                print(f"[TEST] ⚠️ NON AJOUTÉ")
            
            # 3. Fermer la popup
            try:
                close_icon = new_page.locator("span[data-testid='CloseIcon']").first
                if close_icon.count() > 0:
                    close_icon.click()
                    print("[TEST] Popup fermée")
                    new_page.wait_for_timeout(500)
            except:
                pass
            
            # 4. Chercher le bouton suivant
            new_page.wait_for_timeout(300)
            
            next_buttons = new_page.locator(
                "xpath=//div[@data-testid='vouchers-ui-voucher-card'][.//div[contains(text(), 'Codice')]][not(ancestor::div[contains(@class, 'jkau50')])]//div[contains(@class, 'p24wo04')]"
            )
            next_count = next_buttons.count()
            
            if next_count == 0:
                next_buttons = new_page.locator("div.p24wo04")
                next_count = next_buttons.count()
            
            current_index = iteration + 1
            print(f"[TEST] Index suivant: {current_index}, total: {next_count}")
            
            if current_index >= next_count:
                print("[TEST] Plus de boutons disponibles, FIN")
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
                print(f"[TEST] Switch vers nouvel onglet")
                new_page.close()
                new_page = next_new_page
                new_page.wait_for_timeout(800)
                
            except Exception as e:
                print(f"[TEST] ❌ Erreur: {str(e)[:50]}")
                break
        
        try:
            new_page.close()
        except:
            pass
        
        browser.close()
        
        elapsed = time.time() - start_time
        print(f"\n[TEST] ✅ Terminé en {elapsed:.1f}s - {len(results)} codes extraits")
        
        return results


if __name__ == "__main__":
    codes = test_cuponation_it_single()
    print("\n--- RÉSULTATS ---")
    for i, c in enumerate(codes, 1):
        print(f"{i}. {c['code']} | {c['title'][:60]}...")
