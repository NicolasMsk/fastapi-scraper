from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


def get_driver():
    """Crée et retourne une instance du webdriver Chrome en mode headless"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')  # RÉACTIVÉ POUR DÉPLOIEMENT
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # ⚡ OPTIMISATIONS POUR FLY.IO ⚡
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


def close_popups(driver):
    """Ferme les popups et banners"""
    try:
        close_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'close') or contains(@aria-label, 'Close')]")
        for btn in close_buttons:
            try:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.3)
            except:
                pass
    except:
        pass


def scrape_hotukdeals_all(url):
    """
    Scrape TOUS les codes d'une page HotUKDeals.
    
    Process:
    1. Aller sur l'URL
    2. Cliquer sur le premier bouton "See Code*" -> nouvel onglet s'ouvre
    3. Sur le nouvel onglet: récupérer le code affiché dans la popup
    4. Fermer la popup (clic sur X)
    5. Cliquer sur le bouton "See Code*" suivant (sur ce même onglet)
    6. Répéter jusqu'à avoir tous les codes
    
    Args:
        url: URL de la page HotUKDeals (ex: https://www.hotukdeals.com/vouchers/asos.com)
    
    Returns:
        Liste de dict avec tous les codes trouvés
    """
    driver = get_driver()
    results = []
    
    try:
        print(f"[HotUKDeals] Accès à l'URL: {url}")
        driver.get(url)
        time.sleep(3)
        
        close_popups(driver)
        
        original_window = driver.current_window_handle
        
        # Trouver le premier bouton "See Code*" dans une offre VALIDE (avec h3, pas div)
        # Les offres expirées ont un div au lieu de h3 pour le titre
        see_code_buttons = driver.find_elements(By.XPATH, "//div[@data-testid='vouchers-ui-voucher-card-description'][.//h3]//div[@role='button' and contains(@title, 'See Code')]")
        if not see_code_buttons:
            see_code_buttons = driver.find_elements(By.XPATH, "//div[@data-testid='vouchers-ui-voucher-card-description'][.//h3]//div[@role='button' and contains(., 'See Code')]")
        
        if not see_code_buttons:
            # Fallback: chercher tous les boutons mais filtrer ceux avec h3
            all_buttons = driver.find_elements(By.XPATH, "//div[@role='button' and contains(@title, 'See Code')]")
            if not all_buttons:
                all_buttons = driver.find_elements(By.XPATH, "//div[@role='button' and contains(., 'See Code')]")
            
            for btn in all_buttons:
                try:
                    # Vérifier si le conteneur parent a un h3 (offre valide)
                    container = btn.find_element(By.XPATH, "./ancestor::div[@data-testid='vouchers-ui-voucher-card-description']")
                    h3_elements = container.find_elements(By.TAG_NAME, "h3")
                    if h3_elements:
                        see_code_buttons.append(btn)
                except:
                    pass
        
        if not see_code_buttons:
            print("[HotUKDeals] Aucun code disponible sur cette page")
            return results
        
        print(f"[HotUKDeals] {len(see_code_buttons)} boutons 'See Code' trouvés sur la page d'origine")
        
        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_button = see_code_buttons[0]
        
        # Récupérer le titre du premier code
        try:
            container = first_button.find_element(By.XPATH, "./ancestor::div[.//h3][1]")
            title_element = container.find_element(By.XPATH, ".//h3")
            first_title = title_element.text.strip()
        except:
            first_title = "Offre 1"
        
        print(f"[HotUKDeals] Clic sur le premier code: {first_title[:50]}...")
        
        windows_before = set(driver.window_handles)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_button)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", first_button)
        
        # Attendre le nouvel onglet
        time.sleep(2)
        
        windows_after = set(driver.window_handles)
        new_windows = windows_after - windows_before
        
        if not new_windows:
            print("[HotUKDeals] Aucun nouvel onglet ouvert")
            return results
        
        # Switcher vers le nouvel onglet
        new_window = new_windows.pop()
        driver.switch_to.window(new_window)
        print("[HotUKDeals] Switché vers le nouvel onglet")
        time.sleep(2)
        
        # Maintenant on est sur le nouvel onglet avec la popup ouverte
        # On va boucler: récupérer code -> fermer popup -> cliquer sur suivant
        
        processed_titles = set()
        max_iterations = 20  # Sécurité
        
        for iteration in range(max_iterations):
            print(f"[HotUKDeals] --- Itération {iteration + 1} ---")
            
            # 1. Attendre que la popup soit bien chargée
            time.sleep(2)
            
            # 2. Récupérer le code affiché dans la popup
            code = None
            try:
                code_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//h4[contains(@class, 'b8qpi7')]"))
                )
                code = code_element.text.strip()
                print(f"[HotUKDeals] Code trouvé via h4.b8qpi7: {code}")
            except Exception as e:
                print(f"[HotUKDeals] h4.b8qpi7 non trouvé: {str(e)[:30]}")
            
            if not code:
                try:
                    # Chercher tous les h4 et prendre celui qui ressemble à un code
                    code_elements = driver.find_elements(By.TAG_NAME, "h4")
                    print(f"[HotUKDeals] {len(code_elements)} éléments h4 trouvés")
                    for el in code_elements:
                        text = el.text.strip()
                        print(f"[HotUKDeals]   h4 text: '{text}'")
                        if text and len(text) >= 3 and len(text) <= 30:
                            code = text
                            print(f"[HotUKDeals] Code sélectionné: {code}")
                            break
                except Exception as e:
                    print(f"[HotUKDeals] Erreur recherche h4: {str(e)[:30]}")
            
            if not code:
                try:
                    # Chercher le bouton "Copy code" et le code à côté
                    copy_btn = driver.find_element(By.XPATH, "//div[@role='button' and contains(., 'Copy code')]")
                    print("[HotUKDeals] Bouton 'Copy code' trouvé")
                    # Le code est souvent dans un élément frère ou parent
                    parent = copy_btn.find_element(By.XPATH, "./..")
                    all_text = parent.text
                    print(f"[HotUKDeals] Texte parent: {all_text[:100]}")
                    # Extraire le code (première ligne avant "Copy code")
                    lines = all_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and line != "Copy code" and len(line) >= 3 and len(line) <= 30:
                            code = line
                            print(f"[HotUKDeals] Code extrait du parent: {code}")
                            break
                except Exception as e:
                    print(f"[HotUKDeals] Erreur recherche Copy code: {str(e)[:30]}")
            
            # 2. Récupérer le titre de l'offre actuelle
            current_title = None
            try:
                # Chercher le titre dans la popup ou près du code
                title_elements = driver.find_elements(By.XPATH, "//h3 | //h2")
                for el in title_elements:
                    text = el.text.strip()
                    if text and len(text) > 10 and text not in processed_titles:
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
                processed_titles.add(current_title)
                print(f"[HotUKDeals] [{len(results)}] ✅ Code: {code} -> {current_title[:40]}...")
            
            # 3. Fermer la popup en cliquant sur l'icône X
            popup_closed = False
            try:
                close_icon = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, "//*[@data-testid='CloseIcon'] | //button[contains(@aria-label, 'close') or contains(@aria-label, 'Close')]"))
                )
                driver.execute_script("arguments[0].click();", close_icon)
                popup_closed = True
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
            
            # 4. Chercher le prochain bouton "See Code*" sur cette page (offres VALIDES seulement)
            time.sleep(0.5)
            
            # Chercher les boutons dans des offres valides (avec h3)
            next_buttons = driver.find_elements(By.XPATH, "//div[@data-testid='vouchers-ui-voucher-card-description'][.//h3]//div[@role='button' and contains(@title, 'See Code')]")
            if not next_buttons:
                next_buttons = driver.find_elements(By.XPATH, "//div[@data-testid='vouchers-ui-voucher-card-description'][.//h3]//div[@role='button' and contains(., 'See Code')]")
            
            if not next_buttons:
                # Fallback: filtrer manuellement
                all_buttons = driver.find_elements(By.XPATH, "//div[@role='button' and contains(@title, 'See Code')]")
                if not all_buttons:
                    all_buttons = driver.find_elements(By.XPATH, "//div[@role='button' and contains(., 'See Code')]")
                
                next_buttons = []
                for btn in all_buttons:
                    try:
                        container = btn.find_element(By.XPATH, "./ancestor::div[@data-testid='vouchers-ui-voucher-card-description']")
                        h3_elements = container.find_elements(By.TAG_NAME, "h3")
                        if h3_elements:
                            next_buttons.append(btn)
                    except:
                        pass
            
            # On doit cliquer sur le bouton à l'index correspondant au nombre de codes déjà récupérés
            # Car les boutons précédents ont déjà été traités
            current_index = len(results)  # Le prochain bouton à cliquer
            
            if current_index >= len(next_buttons):
                print("[HotUKDeals] Plus de boutons 'See Code' disponibles")
                break
            
            # Cliquer sur le bouton suivant (pas le premier, mais celui à l'index courant)
            next_button = next_buttons[current_index]
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
                    print(f"[HotUKDeals] Switché vers nouvel onglet pour code {current_index + 1}")
                    time.sleep(1)
                else:
                    print("[HotUKDeals] Pas de nouvel onglet détecté")
                    
            except Exception as e:
                print(f"[HotUKDeals] Erreur clic suivant: {str(e)[:30]}")
                break
        
        print(f"[HotUKDeals] Total: {len(results)} codes récupérés")
        return results
        
    except Exception as e:
        print(f"[HotUKDeals] Erreur générale: {str(e)}")
        return results
    
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    test_url = "https://www.hotukdeals.com/vouchers/asos.com"
    
    print("=" * 60)
    print("TEST SCRAPER HOTUKDEALS - TOUS LES CODES")
    print("=" * 60)
    
    results = scrape_hotukdeals_all(test_url)
    
    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes trouvés")
    print("=" * 60)
    for i, result in enumerate(results):
        print(f"  [{i+1}] Code: {result['code']} -> {result['title'][:50]}...")
    print("=" * 60)
