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
        cookie_button = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        cookie_button.click()
        print("[VoucherCodes] Cookie banner fermé")
        time.sleep(1)
    except:
        pass


def scrape_vouchercodes_all(url):
    """
    Scrape TOUS les codes d'une page VoucherCodes.
    
    Process:
    1. Aller sur l'URL
    2. Cliquer sur le premier bouton "Get Code" -> nouvel onglet s'ouvre avec popup
    3. Récupérer le code dans la popup (p[data-qa='el:code'])
    4. Fermer la popup (bouton avec closeIcon)
    5. Rester sur le même onglet, cliquer sur le bouton "Get Code" suivant (index+1)
    6. Répéter jusqu'à avoir tous les codes
    
    Args:
        url: URL de la page VoucherCodes (ex: https://www.vouchercodes.co.uk/trip.com)
    
    Returns:
        Liste de dict avec tous les codes trouvés
    """
    driver = get_driver()
    results = []
    
    try:
        print(f"[VoucherCodes] Accès à l'URL: {url}")
        driver.get(url)
        time.sleep(4)
        
        close_cookie_banner(driver)
        
        original_window = driver.current_window_handle
        
        # Trouver tous les boutons "Get Code" sur la page
        get_code_buttons = driver.find_elements(By.XPATH, "//button[@data-qa='el:offerPrimaryButton' and contains(., 'Get Code')]")
        if not get_code_buttons:
            get_code_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Get Code')]")
        
        total_buttons = len(get_code_buttons)
        print(f"[VoucherCodes] {total_buttons} boutons 'Get Code' trouvés")
        
        if total_buttons == 0:
            print("[VoucherCodes] Aucun code disponible sur cette page")
            return results
        
        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_button = get_code_buttons[0]
        
        # Récupérer le titre du premier code
        try:
            container = first_button.find_element(By.XPATH, "./ancestor::div[contains(@class, 'flex items-start')]")
            title_element = container.find_element(By.XPATH, ".//h3[@data-qa='el:offerTitle']//span")
            first_title = title_element.text.strip()
        except:
            first_title = "Offre 1"
        
        print(f"[VoucherCodes] Clic sur le premier code: {first_title[:50]}...")
        
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
            print("[VoucherCodes] Switché vers le nouvel onglet")
            time.sleep(2)
        
        # Maintenant on est sur le nouvel onglet avec la popup ouverte
        # Boucle: récupérer code -> fermer popup -> cliquer sur suivant
        
        max_iterations = total_buttons + 5
        
        for iteration in range(max_iterations):
            print(f"[VoucherCodes] --- Itération {iteration + 1} ---")
            
            # Attendre que la popup soit bien chargée
            time.sleep(2)
            
            # Récupérer le code dans la popup avec p[data-qa='el:code']
            code = None
            try:
                code_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//p[@data-qa='el:code']"))
                )
                code = code_element.text.strip()
                print(f"[VoucherCodes] Code trouvé: {code}")
            except Exception as e:
                print(f"[VoucherCodes] p[@data-qa='el:code'] non trouvé: {str(e)[:30]}")
            
            if not code:
                try:
                    # Fallback: chercher p avec les classes spécifiques
                    code_elements = driver.find_elements(By.CSS_SELECTOR, "p.font-bold.tracking-wide")
                    for el in code_elements:
                        text = el.text.strip()
                        print(f"[VoucherCodes] p.font-bold trouvé: '{text}'")
                        if text and len(text) >= 3 and len(text) <= 30:
                            code = text
                            break
                except:
                    pass
            
            # Récupérer le titre de l'offre actuelle
            current_title = None
            try:
                title_elements = driver.find_elements(By.XPATH, "//h3//span | //h2")
                for el in title_elements:
                    text = el.text.strip()
                    if text and len(text) > 10:
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
                print(f"[VoucherCodes] ✅ Code: {code} -> {current_title[:40]}...")
            else:
                print(f"[VoucherCodes] ⚠️ Code non trouvé ou doublon")
            
            # Fermer la popup en cliquant sur le bouton X (svg avec data-qa='el:closeIcon')
            popup_closed = False
            try:
                close_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[.//svg[@data-qa='el:closeIcon']]"))
                )
                driver.execute_script("arguments[0].click();", close_button)
                popup_closed = True
                print("[VoucherCodes] Popup fermée via closeIcon")
                time.sleep(1)
            except:
                pass
            
            if not popup_closed:
                try:
                    # Fallback: bouton rond avec svg
                    close_button = driver.find_element(By.XPATH, "//button[contains(@class, 'rounded-full') and .//svg]")
                    driver.execute_script("arguments[0].click();", close_button)
                    popup_closed = True
                    print("[VoucherCodes] Popup fermée via bouton rond")
                    time.sleep(1)
                except:
                    pass
            
            # Chercher le prochain bouton "Get Code" sur cette page
            time.sleep(0.5)
            next_buttons = driver.find_elements(By.XPATH, "//button[@data-qa='el:offerPrimaryButton' and contains(., 'Get Code')]")
            if not next_buttons:
                next_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Get Code')]")
            
            # On doit cliquer sur le bouton à l'index = nombre de codes récupérés - 1
            # Car on a déjà récupéré le premier code avant de cliquer
            current_index = len(results) - 1 
            
            if current_index >= len(next_buttons):
                print("[VoucherCodes] Plus de boutons 'Get Code' disponibles")
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
                    print(f"[VoucherCodes] Switché vers nouvel onglet pour code {current_index + 1}")
                    time.sleep(1)
                    
            except Exception as e:
                print(f"[VoucherCodes] Erreur clic suivant: {str(e)[:30]}")
                break
        
        print(f"[VoucherCodes] Total: {len(results)} codes récupérés")
        return results
        
    except Exception as e:
        print(f"[VoucherCodes] Erreur générale: {str(e)}")
        return results
    
    finally:
        if driver:
            driver.quit()


# Garder l'ancienne fonction pour rétrocompatibilité (utilise la nouvelle)
def scrape_vouchercodes_single(url, title):
    """
    DEPRECATED: Utiliser scrape_vouchercodes_all() à la place.
    """
    all_codes = scrape_vouchercodes_all(url)
    
    expected_clean = ' '.join(title.lower().split())
    
    for result in all_codes:
        result_clean = ' '.join(result['title'].lower().split())
        if expected_clean in result_clean or result_clean in expected_clean:
            return result
    
    if all_codes:
        return all_codes[0]
    
    return {
        "success": False,
        "code": None,
        "title": title,
        "message": "Titre non trouvé sur la page"
    }


if __name__ == "__main__":
    test_url = "https://www.vouchercodes.co.uk/trip.com"
    
    print("=" * 60)
    print("TEST SCRAPER VOUCHERCODES - TOUS LES CODES")
    print("=" * 60)
    
    results = scrape_vouchercodes_all(test_url)
    
    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes trouvés")
    print("=" * 60)
    for i, result in enumerate(results):
        print(f"  [{i+1}] Code: {result['code']} -> {result['title'][:50]}...")
    print("=" * 60)
