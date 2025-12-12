from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


def get_driver():
    """Crée et retourne une instance du webdriver Chrome en mode headless"""
    chrome_options = Options()
    #chrome_options.add_argument('--headless=new')  # RÉACTIVÉ POUR DÉPLOIEMENT
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # ⚡ OPTIMISATIONS POUR DÉPLOIEMENT ⚡
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--disable-background-networking')
    chrome_options.add_argument('--disable-default-apps')
    chrome_options.add_argument('--disable-sync')
    chrome_options.add_argument('--disable-translate')
    
    chrome_options.page_load_strategy = 'eager'
    
    return webdriver.Chrome(options=chrome_options)


def close_cookie_banner(driver):
    """Ferme le cookie banner si présent"""
    try:
        cookie_selectors = [
            "//button[contains(text(), 'Accept')]",
            "//button[contains(text(), 'Agree')]",
            "//button[contains(@class, 'accept')]",
        ]
        for selector in cookie_selectors:
            try:
                cookie_button = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                cookie_button.click()
                print("[Cuponation] Cookie banner fermé")
                time.sleep(1)
                return
            except:
                continue
    except:
        pass


def scrape_cuponation_all(url):
    """
    Scrape TOUS les codes d'une page Cuponation.
    
    Process:
    1. Aller sur l'URL
    2. Cliquer sur le premier bouton "See code" -> nouvel onglet s'ouvre avec popup
    3. Récupérer le code dans la popup (span[@data-testid='voucherPopup-codeHolder-voucherType-code']//h4)
    4. Fermer la popup (bouton avec CloseIcon)
    5. Rester sur le même onglet, cliquer sur le bouton "See code" suivant (index+1)
    6. Répéter jusqu'à avoir tous les codes
    
    Args:
        url: URL de la page Cuponation (ex: https://www.cuponation.com.au/qatar-airways-promo-code)
    
    Returns:
        Liste de dict avec tous les codes trouvés
    """
    driver = get_driver()
    results = []
    
    try:
        print(f"[Cuponation] Accès à l'URL: {url}")
        driver.get(url)
        time.sleep(4)
        
        close_cookie_banner(driver)
        
        original_window = driver.current_window_handle
        
        # Trouver tous les boutons "See code" sur la page (exclure section expirée jkau50)
        get_code_buttons = driver.find_elements(
            By.XPATH, 
            "//div[@role='button' and @title='See code' and not(ancestor::div[contains(@class, 'jkau50')])]"
        )
        
        total_buttons = len(get_code_buttons)
        print(f"[Cuponation] {total_buttons} boutons 'See code' trouvés")
        
        if total_buttons == 0:
            print("[Cuponation] Aucun code disponible sur cette page")
            return results
        
        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_button = get_code_buttons[0]
        
        # Récupérer le titre du premier code
        try:
            card = first_button.find_element(By.XPATH, "./ancestor::div[@data-testid='vouchers-ui-voucher-card']")
            title_element = card.find_element(By.XPATH, ".//div[@data-testid='vouchers-ui-voucher-card-description']//h3 | .//div[contains(@class, 'az57m4e')]")
            first_title = title_element.text.strip()
        except:
            first_title = "Offre 1"
        
        print(f"[Cuponation] Clic sur le premier code: {first_title[:50]}...")
        
        windows_before = set(driver.window_handles)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_button)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", first_button)
        
        # Attendre le nouvel onglet
        time.sleep(2)
        
        windows_after = set(driver.window_handles)
        new_windows = windows_after - windows_before
        
        if new_windows:
            # Switcher vers le nouvel onglet
            new_window = new_windows.pop()
            driver.switch_to.window(new_window)
            print("[Cuponation] Switché vers le nouvel onglet")
            time.sleep(2)
        
        # Maintenant on est sur le nouvel onglet avec la popup ouverte
        # Boucle: récupérer code -> fermer popup -> cliquer sur suivant
        
        max_iterations = total_buttons + 5
        
        for iteration in range(max_iterations):
            print(f"[Cuponation] --- Itération {iteration + 1} ---")
            
            # Attendre que la popup soit bien chargée
            time.sleep(2)
            
            # Récupérer le code dans la popup avec span[@data-testid='voucherPopup-codeHolder-voucherType-code']//h4
            code = None
            try:
                code_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//span[@data-testid='voucherPopup-codeHolder-voucherType-code']//h4"))
                )
                code = code_element.text.strip()
                print(f"[Cuponation] Code trouvé: {code}")
            except Exception as e:
                print(f"[Cuponation] data-testid non trouvé: {str(e)[:30]}")
            
            if not code:
                try:
                    # Fallback: chercher h4 avec classe b8qpi79
                    code_element = driver.find_element(By.CSS_SELECTOR, "h4.b8qpi79")
                    code = code_element.text.strip()
                    print(f"[Cuponation] Code trouvé via h4.b8qpi79: {code}")
                except:
                    pass
            
            # Récupérer le titre de l'offre depuis la popup (h4 avec classes az57m40 az57m46)
            current_title = None
            try:
                # Le titre est dans un h4 avec les classes az57m40 et az57m46 (pas b8qpi79 qui est le code)
                title_element = driver.find_element(By.XPATH, "//h4[contains(@class, 'az57m40') and contains(@class, 'az57m46') and not(contains(@class, 'b8qpi79'))]")
                current_title = title_element.text.strip()
                print(f"[Cuponation] Titre trouvé via h4.az57m40.az57m46: {current_title[:50]}...")
            except:
                pass
            
            # Fallback: chercher h4 qui n'est pas le code
            if not current_title:
                try:
                    h4_elements = driver.find_elements(By.XPATH, "//h4")
                    for el in h4_elements:
                        text = el.text.strip()
                        # Ignorer le code (qui est aussi dans un h4)
                        if text and text != code and len(text) > 15:
                            current_title = text
                            break
                except:
                    pass

            if not current_title:
                current_title = f"Offre {iteration + 1}"
            
            if code and len(code) >= 3 and code not in [r['code'] for r in results]:
                results.append({
                    "success": True,
                    "code": code,
                    "title": current_title,
                    "message": "Code extrait avec succès"
                })
                print(f"[Cuponation] ✅ Code: {code} -> {current_title[:40]}...")
            else:
                print(f"[Cuponation] ⚠️ Code non trouvé ou doublon")
            
            # Fermer la popup en cliquant sur le bouton X (span[@data-testid='CloseIcon'])
            popup_closed = False
            try:
                close_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[@data-testid='CloseIcon']"))
                )
                driver.execute_script("arguments[0].click();", close_button)
                popup_closed = True
                print("[Cuponation] Popup fermée via CloseIcon")
                time.sleep(1)
            except:
                pass
            
            if not popup_closed:
                try:
                    # Fallback: bouton parent du CloseIcon
                    close_button = driver.find_element(By.XPATH, "//span[@data-testid='CloseIcon']/ancestor::*[@role='button'][1]")
                    driver.execute_script("arguments[0].click();", close_button)
                    popup_closed = True
                    print("[Cuponation] Popup fermée via bouton parent")
                    time.sleep(1)
                except:
                    pass
            
            # Chercher le prochain bouton "See code" sur cette page
            time.sleep(0.5)
            next_buttons = driver.find_elements(
                By.XPATH, 
                "//div[@role='button' and @title='See code' and not(ancestor::div[contains(@class, 'jkau50')])]"
            )
            
            # On doit cliquer sur le bouton à l'index = iteration (on a déjà traité iteration boutons)
            current_index = iteration
            
            if current_index >= len(next_buttons):
                print("[Cuponation] Plus de boutons 'See code' disponibles")
                break
            
            # Cliquer sur le bouton suivant
            next_button = next_buttons[current_index]
            try:
                # Mémoriser les onglets avant le clic
                windows_before = set(driver.window_handles)
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(2)
                
                # Switcher vers le nouvel onglet si un nouveau s'est ouvert
                windows_after = set(driver.window_handles)
                new_windows = windows_after - windows_before
                
                if new_windows:
                    new_window = new_windows.pop()
                    driver.switch_to.window(new_window)
                    print(f"[Cuponation] Switché vers nouvel onglet pour code {current_index + 1}")
                    time.sleep(1)
                    
            except Exception as e:
                print(f"[Cuponation] Erreur clic suivant: {str(e)[:30]}")
                break
        
        print(f"[Cuponation] Total: {len(results)} codes récupérés")
        return results
        
    except Exception as e:
        print(f"[Cuponation] Erreur générale: {str(e)}")
        return results
    
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    test_url = "https://www.cuponation.com.au/qatar-airways-promo-code"
    
    print("=" * 60)
    print("TEST SCRAPER CUPONATION - TOUS LES CODES")
    print("=" * 60)
    
    results = scrape_cuponation_all(test_url)
    
    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes trouvés")
    print("=" * 60)
    for i, result in enumerate(results):
        print(f"  [{i+1}] Code: {result['code']} -> {result['title'][:50]}...")
    print("=" * 60)
