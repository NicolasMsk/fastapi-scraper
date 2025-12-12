from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


def get_driver():
    """Crée et retourne une instance du webdriver Chrome en mode headless"""
    chrome_options = Options()
    #chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # ⚡ OPTIMISATIONS POUR DÉPLOIEMENT ⚡
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
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
    
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.page_load_strategy = 'eager'
    
    return webdriver.Chrome(options=chrome_options)


def scrape_cuponation_it_all(url):
    """
    Scrape TOUS les codes d'une page Cuponation Italie.
    
    Process:
    1. Aller sur l'URL
    2. Cliquer sur le premier bouton (flèche) -> nouvel onglet s'ouvre
    3. Sur le nouvel onglet: récupérer le code (h4.b8qpi79) et titre (h4.az57m40.az57m46 sans b8qpi79)
    4. Fermer la popup (clic sur CloseIcon)
    5. Cliquer sur le bouton suivant
    6. Répéter jusqu'à avoir tous les codes
    
    Args:
        url: URL de la page Cuponation Italie (ex: https://www.cuponation.it/codice-sconto-groupon)
    
    Returns:
        Liste de dict avec tous les codes trouvés
    """
    driver = get_driver()
    results = []
    
    try:
        print(f"[CuponationIT] Accès à l'URL: {url}")
        driver.get(url)
        time.sleep(3)
        
        # Accepter les cookies si présents
        try:
            cookie_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accetta') or contains(text(), 'accetta') or contains(text(), 'Accept')]"))
            )
            cookie_btn.click()
            time.sleep(1)
        except:
            pass
        
        original_window = driver.current_window_handle
        
        # Trouver les boutons cliquables UNIQUEMENT pour les offres avec "Codice" (pas "Offerta")
        # - Exclure les offres expirées (dans div.jkau50)
        # - Exclure les offres "similaires" d'autres marques (dans div._1hla7140 ou similar-vouchers-widget)
        # - Inclure seulement celles avec le label "Codice"
        see_code_buttons = driver.find_elements(By.XPATH, 
            "//div[@data-testid='vouchers-ui-voucher-card'][.//div[contains(text(), 'Codice')]][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])][not(ancestor::div[@data-testid='similar-vouchers-widget'])]//div[contains(@class, 'p24wo04')]"
        )
        
        if not see_code_buttons:
            # Fallback: chercher les cartes avec "Codice" dans les labels
            see_code_buttons = driver.find_elements(By.XPATH, 
                "//div[contains(@class, '_6tavko6')][.//div[contains(text(), 'Codice')]][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])][not(ancestor::div[@data-testid='similar-vouchers-widget'])]//div[contains(@class, 'p24wo04')]"
            )
        
        if not see_code_buttons:
            print("[CuponationIT] Aucun code disponible sur cette page")
            return results
        
        print(f"[CuponationIT] {len(see_code_buttons)} boutons trouvés (hors expirés)")
        
        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_button = see_code_buttons[0]
        
        # Récupérer le titre du premier code (depuis la page principale)
        try:
            container = first_button.find_element(By.XPATH, "./ancestor::div[@data-testid='vouchers-ui-voucher-card-description']")
            title_element = container.find_element(By.XPATH, ".//h3")
            first_title = title_element.text.strip()
        except:
            first_title = "Offerta 1"
        
        print(f"[CuponationIT] Clic sur le premier code: {first_title[:50]}...")
        
        windows_before = set(driver.window_handles)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_button)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", first_button)
        
        # Attendre le nouvel onglet
        time.sleep(2)
        
        windows_after = set(driver.window_handles)
        new_windows = windows_after - windows_before
        
        if not new_windows:
            print("[CuponationIT] Aucun nouvel onglet ouvert")
            return results
        
        # Switcher vers le nouvel onglet
        new_window = new_windows.pop()
        driver.switch_to.window(new_window)
        print("[CuponationIT] Switché vers le nouvel onglet")
        time.sleep(2)
        
        # Maintenant on est sur le nouvel onglet avec la popup ouverte
        # On va boucler: récupérer code -> fermer popup -> cliquer sur suivant
        
        max_iterations = 30  # Sécurité
        clicked_count = 0  # Compteur de boutons cliqués
        
        for iteration in range(max_iterations):
            print(f"[CuponationIT] --- Itération {iteration + 1} ---")
            
            # 1. Attendre que la popup soit bien chargée
            time.sleep(2)
            
            # 2. Récupérer le code affiché dans la popup (h4 avec classe b8qpi79)
            code = None
            try:
                code_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h4.b8qpi79"))
                )
                code = code_element.text.strip()
                print(f"[CuponationIT] Code trouvé via h4.b8qpi79: {code}")
            except Exception as e:
                print(f"[CuponationIT] h4.b8qpi79 non trouvé: {str(e)[:30]}")
            
            if not code:
                try:
                    # Alternative: chercher h4 avec les classes
                    code_elements = driver.find_elements(By.XPATH, "//h4[contains(@class, 'b8qpi7')]")
                    for el in code_elements:
                        text = el.text.strip()
                        if text and len(text) >= 3 and len(text) <= 30:
                            code = text
                            print(f"[CuponationIT] Code trouvé via XPath: {code}")
                            break
                except Exception as e:
                    print(f"[CuponationIT] Erreur recherche code: {str(e)[:30]}")
            
            # 3. Récupérer le titre de l'offre depuis la popup (h4 avec az57m40 az57m46 SANS b8qpi79)
            current_title = None
            try:
                # Le titre est dans un h4 avec classes az57m40 et az57m46 mais SANS b8qpi79
                title_elements = driver.find_elements(By.CSS_SELECTOR, "h4.az57m40.az57m46")
                for el in title_elements:
                    classes = el.get_attribute("class")
                    # Exclure l'élément qui contient le code (b8qpi79)
                    if "b8qpi79" not in classes:
                        text = el.text.strip()
                        if text and len(text) > 10:
                            current_title = text
                            print(f"[CuponationIT] Titre trouvé: {current_title[:50]}...")
                            break
            except Exception as e:
                print(f"[CuponationIT] Erreur titre popup: {str(e)[:30]}")
            
            if not current_title:
                current_title = f"Offerta {iteration + 1}"
            
            if code and len(code) >= 3 and code not in [r['code'] for r in results]:
                results.append({
                    "success": True,
                    "code": code,
                    "title": current_title,
                    "message": "Code extrait avec succès"
                })
                print(f"[CuponationIT] ✅ Code: {code} -> {current_title[:40]}...")
            else:
                print(f"[CuponationIT] ⚠️ Code non trouvé ou doublon")
            
            # 4. Fermer la popup en cliquant sur l'icône CloseIcon
            popup_closed = False
            try:
                close_icon = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[@data-testid='CloseIcon']"))
                )
                driver.execute_script("arguments[0].click();", close_icon)
                popup_closed = True
                print("[CuponationIT] Popup fermée via CloseIcon")
                time.sleep(1)
            except:
                pass
            
            if not popup_closed:
                try:
                    # Alternative: bouton avec aria-label close
                    close_btn = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'close') or contains(@aria-label, 'Close') or contains(@aria-label, 'chiudi')]")
                    driver.execute_script("arguments[0].click();", close_btn)
                    popup_closed = True
                    print("[CuponationIT] Popup fermée via aria-label")
                    time.sleep(1)
                except:
                    pass
            
            if not popup_closed:
                try:
                    # Essayer de cliquer ailleurs pour fermer
                    driver.find_element(By.TAG_NAME, "body").click()
                    time.sleep(0.5)
                except:
                    pass
            
            # 5. Chercher le prochain bouton sur cette page (UNIQUEMENT "Codice", pas "Offerta", pas "similaires")
            time.sleep(0.5)
            
            # Chercher les boutons UNIQUEMENT pour les offres avec "Codice" (pas "Offerta", pas offres similaires)
            next_buttons = driver.find_elements(By.XPATH, 
                "//div[@data-testid='vouchers-ui-voucher-card'][.//div[contains(text(), 'Codice')]][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])][not(ancestor::div[@data-testid='similar-vouchers-widget'])]//div[contains(@class, 'p24wo04')]"
            )
            
            if not next_buttons:
                # Fallback
                next_buttons = driver.find_elements(By.XPATH, 
                    "//div[contains(@class, '_6tavko6')][.//div[contains(text(), 'Codice')]][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])][not(ancestor::div[@data-testid='similar-vouchers-widget'])]//div[contains(@class, 'p24wo04')]"
                )
            
            # Incrémenter le compteur de clics
            clicked_count += 1
            
            if clicked_count >= len(next_buttons):
                print("[CuponationIT] Plus de boutons disponibles")
                break
            
            # Cliquer sur le bouton suivant
            next_button = next_buttons[clicked_count]
            try:
                # Mémoriser les onglets avant le clic
                windows_before = set(driver.window_handles)
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(2)
                
                # Switcher vers le nouvel onglet qui vient de s'ouvrir
                windows_after = set(driver.window_handles)
                new_windows = windows_after - windows_before
                
                if new_windows:
                    new_window = new_windows.pop()
                    driver.switch_to.window(new_window)
                    print(f"[CuponationIT] Switché vers nouvel onglet pour code {clicked_count + 1}")
                    time.sleep(1)
                else:
                    print("[CuponationIT] Pas de nouvel onglet détecté")
                    
            except Exception as e:
                print(f"[CuponationIT] Erreur clic suivant: {str(e)[:30]}")
                break
        
        print(f"[CuponationIT] Total: {len(results)} codes récupérés")
        return results
        
    except Exception as e:
        print(f"[CuponationIT] Erreur générale: {str(e)}")
        return results
    
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    test_url = "https://www.cuponation.it/codice-sconto-groupon"
    
    print("=" * 60)
    print("TEST SCRAPER CUPONATION ITALIE - TOUS LES CODES")
    print("=" * 60)
    
    results = scrape_cuponation_it_all(test_url)
    
    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes trouvés")
    print("=" * 60)
    for i, result in enumerate(results):
        print(f"  [{i+1}] Code: {result['code']} -> {result['title'][:50]}...")
    print("=" * 60)
