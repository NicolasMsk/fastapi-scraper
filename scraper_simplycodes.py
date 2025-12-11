from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time


def get_chrome_options():
    """Configure les options Chrome pour le scraping"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return options


def scrape_simplycodes_all(url: str) -> list:
    """
    Récupère TOUS les codes d'une page SimplyCodes en cliquant UNE SEULE FOIS
    sur le premier bouton "Show Code" pour déclencher l'authentification,
    puis en récupérant tous les codes visibles.
    
    Args:
        url: URL de la page SimplyCodes (ex: https://simplycodes.com/store/autodesk.com)
    
    Returns:
        Liste de dictionnaires avec success, code, title, message
    """
    driver = None
    results = []
    
    try:
        print(f"\n[SimplyCodes ALL] Démarrage pour: {url}")
        
        options = get_chrome_options()
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        
        time.sleep(5)
        print("[SimplyCodes ALL] Page chargée")
        
        # Trouver tous les boutons "Show Code"
        show_code_buttons = driver.find_elements(By.CSS_SELECTOR, "[data-testid='promotion-copy-code-button']")
        print(f"[SimplyCodes ALL] {len(show_code_buttons)} boutons 'Show Code' trouvés")
        
        if not show_code_buttons:
            return results
        
        # Cliquer sur le PREMIER bouton pour déclencher l'authentification
        original_windows = set(driver.window_handles)
        original_window = driver.current_window_handle
        
        first_button = show_code_buttons[0]
        
        # Récupérer le titre du premier code AVANT de cliquer
        first_title = None
        try:
            current = first_button
            for _ in range(10):
                try:
                    current = current.find_element(By.XPATH, "./..")
                    title_elems = current.find_elements(By.CSS_SELECTOR, "[data-testid='promotion-subtitle']")
                    if title_elems:
                        first_title = title_elems[0].text.strip()
                        break
                except:
                    break
        except:
            pass
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_button)
        time.sleep(1)
        
        actions = ActionChains(driver)
        actions.move_to_element(first_button).click().perform()
        print("[SimplyCodes ALL] Premier bouton cliqué")
        time.sleep(4)
        
        # Gérer le nouvel onglet
        new_windows = set(driver.window_handles)
        new_tabs = new_windows - original_windows
        
        if new_tabs:
            simplycodes_window = None
            for new_window in new_tabs:
                driver.switch_to.window(new_window)
                current_url = driver.current_url
                print(f"[SimplyCodes ALL] Nouvel onglet: {current_url}")
                
                if "simplycodes" in current_url:
                    simplycodes_window = new_window
                    time.sleep(2)
                    
                    # RÉCUPÉRER LE PREMIER CODE DEPUIS LA POPUP
                    try:
                        # Le code est dans un input ou span dans la popup
                        popup_code = None
                        
                        # Essayer de trouver le code dans la popup (souvent dans un input readonly ou span)
                        code_elements = driver.find_elements(By.CSS_SELECTOR, "input[readonly], span.font-bold.uppercase.truncate, div.font-bold.uppercase")
                        for elem in code_elements:
                            text = elem.get_attribute("value") or elem.text
                            if text and len(text) > 3 and text not in ["Show Code", "Copied!", "Copy"]:
                                popup_code = text.strip()
                                break
                        
                        if popup_code and first_title:
                            results.append({
                                "success": True,
                                "code": popup_code,
                                "title": first_title,
                                "message": "Code extrait depuis la popup"
                            })
                            print(f"[SimplyCodes ALL] ✓ POPUP: {popup_code} -> {first_title[:50]}...")
                    except Exception as e:
                        print(f"[SimplyCodes ALL] Erreur récupération popup: {e}")
                    
                    # Fermer la popup
                    try:
                        close_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "[class*='i-ph'][class*='x']"))
                        )
                        actions = ActionChains(driver)
                        actions.move_to_element(close_button).click().perform()
                        print("[SimplyCodes ALL] Popup fermée avec le bouton X")
                        time.sleep(2)
                    except Exception as e:
                        print(f"[SimplyCodes ALL] Pas de bouton X trouvé: {e}")
            
            if simplycodes_window:
                driver.switch_to.window(simplycodes_window)
            else:
                driver.switch_to.window(original_window)
        
        time.sleep(2)
        
        # Maintenant récupérer TOUS les codes visibles sur la page
        print("[SimplyCodes ALL] Récupération de tous les codes visibles...")
        
        # Codes déjà récupérés (pour éviter les doublons)
        existing_codes = {r["code"] for r in results}
        
        all_buttons = driver.find_elements(By.CSS_SELECTOR, "[data-testid='promotion-copy-code-button']")
        print(f"[SimplyCodes ALL] {len(all_buttons)} boutons trouvés")
        
        for button in all_buttons:
            try:
                # Trouver le code dans le bouton
                code_span = button.find_element(By.CSS_SELECTOR, "span.truncate")
                code = code_span.text.strip()
                
                # Ignorer les textes qui ne sont pas des codes + éviter les doublons
                if code and code not in ["Show Code", "Copied!", "Copy"] and len(code) > 2 and code not in existing_codes:
                    # Remonter pour trouver le titre associé
                    current = button
                    title = None
                    for _ in range(10):
                        try:
                            current = current.find_element(By.XPATH, "./..")
                            title_elems = current.find_elements(By.CSS_SELECTOR, "[data-testid='promotion-subtitle']")
                            if title_elems:
                                title = title_elems[0].text.strip()
                                break
                        except:
                            break
                    
                    if title and code:
                        results.append({
                            "success": True,
                            "code": code,
                            "title": title,
                            "message": "Code extrait avec succès"
                        })
                        existing_codes.add(code)
                        print(f"[SimplyCodes ALL] ✓ {code} -> {title[:50]}...")
            except:
                continue
        
        print(f"\n[SimplyCodes ALL] Total: {len(results)} codes récupérés")
        return results
        
    except Exception as e:
        print(f"[SimplyCodes ALL] Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        return results
    
    finally:
        if driver:
            driver.quit()


# Test du scraper
if __name__ == "__main__":
    test_url = "https://simplycodes.com/store/autodesk.com"
    
    print("=" * 60)
    print("TEST SCRAPER SIMPLYCODES - TOUS LES CODES")
    print("=" * 60)
    
    results = scrape_simplycodes_all(test_url)
    
    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes trouvés")
    print("=" * 60)
    for i, result in enumerate(results):
        print(f"\n  [{i+1}] Code: {result['code']}")
        print(f"      Title: {result['title'][:60]}...")
        print(f"      Success: {result['success']}")
    print("=" * 60)
