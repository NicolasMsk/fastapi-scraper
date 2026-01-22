"""
Test script pour Cuponation ES - Logique identique au ALL avec plus de logs
"""

from playwright.sync_api import sync_playwright
import time

# URL de test
TEST_URL = "https://www.cuponation.es/cupon-shein"

def test_cuponation_es_single():
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
        page.wait_for_timeout(2500)  # Optimisé: 4000 -> 2500
        print("[TEST] Page chargée")
        
        # Accepter les cookies
        try:
            cookie_btn = page.locator("button:has-text('Aceptar'), button:has-text('Accept')")
            if cookie_btn.count() > 0:
                cookie_btn.first.click()
                page.wait_for_timeout(1000)
                print("[TEST] Cookies acceptés")
            else:
                print("[TEST] Pas de bouton cookies trouvé")
        except Exception as e:
            print(f"[TEST] Exception cookies: {e}")
        
        # Trouver les boutons "Ver código" en excluant les offres expirées
        buttons_xpath = "//div[@role='button'][@title='Ver código'][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]"
        get_code_buttons = page.locator(f"xpath={buttons_xpath}")
        count = get_code_buttons.count()
        print(f"[TEST] Boutons 'Ver código' avec filtre complet: {count}")
        
        if count == 0:
            # Fallback sans _1hla7140
            get_code_buttons = page.locator("xpath=//div[@role='button'][@title='Ver código'][not(ancestor::div[contains(@class, 'jkau50')])]")
            count = get_code_buttons.count()
            print(f"[TEST] Fallback sans _1hla7140: {count} boutons")
        
        if count == 0:
            print("[TEST] ❌ Aucun bouton trouvé!")
            browser.close()
            return []
        
        results = []
        processed_codes = set()
        processed_titles = set()
        max_codes = 5
        
        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_btn = get_code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(300)  # Optimisé: 500 -> 300
        print("[TEST] Premier bouton scrollé en vue")
        
        print("[TEST] Clic sur le premier bouton...")
        with context.expect_page() as new_page_info:
            first_btn.click()
        
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded")
        new_page.wait_for_timeout(1500)  # Optimisé: 2000 -> 1500
        print(f"[TEST] Nouvel onglet ouvert, URL: {new_page.url[:60]}...")
        
        # Boucle d'extraction (comme le ALL)
        for iteration in range(max_codes):
            print(f"\n[TEST] ========== ITERATION {iteration + 1} ==========")
            
            # Attendre que la popup soit bien chargée
            new_page.wait_for_timeout(1500)  # Optimisé: 2000 -> 1500
            print("[TEST] Attente popup chargée")
            
            code = None
            current_title = None
            
            # 1. Récupérer le code dans la popup
            print("[TEST] Recherche du code...")
            try:
                code_elem = new_page.locator("h4.b8qpi79").first
                elem_count = code_elem.count()
                print(f"[TEST] h4.b8qpi79 count: {elem_count}")
                if elem_count > 0:
                    code = code_elem.inner_text().strip()
                    print(f"[TEST] Code via h4.b8qpi79: '{code}'")
            except Exception as e:
                print(f"[TEST] Exception h4.b8qpi79: {e}")
            
            if not code:
                try:
                    code_elem = new_page.locator("span[data-testid='voucherPopup-codeHolder-voucherType-code'] h4").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                        print(f"[TEST] Code via data-testid: '{code}'")
                except Exception as e:
                    print(f"[TEST] Exception data-testid: {e}")
            
            if not code:
                try:
                    code_elems = new_page.locator("h4[class*='b8qpi7']")
                    print(f"[TEST] h4[class*='b8qpi7'] count: {code_elems.count()}")
                    for i in range(code_elems.count()):
                        text = code_elems.nth(i).inner_text().strip()
                        print(f"[TEST]   h4 {i}: '{text}'")
                        if text and 3 <= len(text) <= 30:
                            code = text
                            break
                except Exception as e:
                    print(f"[TEST] Exception fallback code: {e}")
            
            # 2. Récupérer le titre
            print("[TEST] Recherche du titre...")
            try:
                title_elems = new_page.locator("h4.az57m40.az57m46")
                print(f"[TEST] h4.az57m40.az57m46 count: {title_elems.count()}")
                for i in range(title_elems.count()):
                    elem = title_elems.nth(i)
                    classes = elem.get_attribute("class") or ""
                    text = elem.inner_text().strip()
                    print(f"[TEST]   h4 {i}: classes='{classes[:30]}', text='{text[:40]}...'")
                    if "b8qpi79" not in classes and text and len(text) > 10:
                        current_title = text
                        break
            except Exception as e:
                print(f"[TEST] Exception titre principal: {e}")
            
            if not current_title:
                try:
                    h4_elems = new_page.locator("h4")
                    print(f"[TEST] Fallback h4 total: {h4_elems.count()}")
                    for i in range(min(h4_elems.count(), 5)):
                        text = h4_elems.nth(i).inner_text().strip()
                        print(f"[TEST]   h4 {i}: '{text[:40]}...'")
                        if text and text != code and len(text) > 15:
                            current_title = text
                            break
                except Exception as e:
                    print(f"[TEST] Exception fallback titre: {e}")
            
            # Valider et ajouter
            print(f"[TEST] Code final: '{code}', Titre final: '{current_title[:50] if current_title else None}...'")
            if code and current_title and len(code) >= 3 and code not in processed_codes and current_title not in processed_titles:
                processed_codes.add(code)
                processed_titles.add(current_title)
                results.append({"code": code, "title": current_title})
                print(f"[TEST] ✅ AJOUTÉ: {code}")
            else:
                reasons = []
                if not code: reasons.append("pas de code")
                if not current_title: reasons.append("pas de titre")
                if code and len(code) < 3: reasons.append("code trop court")
                if code in processed_codes: reasons.append("code doublon")
                if current_title in processed_titles: reasons.append("titre doublon")
                print(f"[TEST] ⚠️ NON AJOUTÉ: {', '.join(reasons)}")
            
            # 3. Fermer la popup
            print("[TEST] Tentative fermeture popup...")
            popup_closed = False
            try:
                close_icon = new_page.locator("span[data-testid='CloseIcon']").first
                close_count = close_icon.count()
                print(f"[TEST] CloseIcon count: {close_count}")
                if close_count > 0:
                    close_icon.click()
                    popup_closed = True
                    print("[TEST] Popup fermée via CloseIcon")
                    new_page.wait_for_timeout(500)  # Optimisé: 1000 -> 500
            except Exception as e:
                print(f"[TEST] Exception CloseIcon: {e}")
            
            if not popup_closed:
                try:
                    close_btn = new_page.locator("span[data-testid='CloseIcon']").locator("xpath=ancestor::*[@role='button'][1]").first
                    if close_btn.count() > 0:
                        close_btn.click()
                        popup_closed = True
                        print("[TEST] Popup fermée via bouton parent")
                        new_page.wait_for_timeout(500)  # Optimisé: 1000 -> 500
                except Exception as e:
                    print(f"[TEST] Exception bouton parent: {e}")
            
            if not popup_closed:
                print("[TEST] ❌ POPUP NON FERMÉE!")
            
            # 4. Chercher le prochain bouton sur cette page (new_page, pas page!)
            new_page.wait_for_timeout(300)  # Optimisé: 500 -> 300
            print("[TEST] Recherche boutons suivants sur new_page...")
            
            next_buttons = new_page.locator("xpath=//div[@role='button'][@title='Ver código'][not(ancestor::div[contains(@class, 'jkau50')])]")
            next_count = next_buttons.count()
            print(f"[TEST] Boutons 'Ver código' sur new_page: {next_count}")
            
            if next_count == 0:
                next_buttons = new_page.locator("div[role='button'][title='Ver código']")
                next_count = next_buttons.count()
                print(f"[TEST] Fallback sans filtre: {next_count}")
            
            # L'index du prochain bouton = iteration + 1 (on a déjà traité iteration+1 boutons)
            current_index = iteration + 1
            print(f"[TEST] Index à cliquer: {current_index}, total disponible: {next_count}")
            
            if current_index >= next_count:
                print("[TEST] Plus de boutons disponibles, FIN")
                break
            
            if iteration >= max_codes - 1:
                print("[TEST] Max codes atteint, FIN")
                break
            
            # 5. Cliquer sur le bouton suivant
            print(f"[TEST] Clic sur bouton index {current_index}...")
            next_btn = next_buttons.nth(current_index)
            try:
                next_btn.scroll_into_view_if_needed()
                new_page.wait_for_timeout(200)  # Optimisé: 300 -> 200
                
                with context.expect_page() as next_page_info:
                    next_btn.click()
                
                next_new_page = next_page_info.value
                next_new_page.wait_for_load_state("domcontentloaded")
                print(f"[TEST] Nouvel onglet ouvert: {next_new_page.url[:50]}...")
                
                print("[TEST] Fermeture ancien onglet...")
                new_page.close()
                new_page = next_new_page
                new_page.wait_for_timeout(800)  # Optimisé: 1000 -> 800
                print("[TEST] Switch vers nouvel onglet OK")
                
            except Exception as e:
                print(f"[TEST] ❌ ERREUR clic suivant: {e}")
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
    codes = test_cuponation_es_single()
    print("\n--- RÉSULTATS ---")
    for i, c in enumerate(codes, 1):
        print(f"{i}. {c['code']} | {c['title'][:60]}...")
