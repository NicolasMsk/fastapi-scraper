from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


def get_driver():
    """Crée et retourne une instance du webdriver Chrome en mode headless"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
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


def scrape_codicescontonet_all(url):
    """
    Scrape TOUS les codes d'une page codice-sconto.net (Italie).
    
    Process:
    1. Aller sur l'URL
    2. Cliquer sur le premier bouton "Vedi il codice" -> nouvel onglet s'ouvre
    3. Sur le nouvel onglet: récupérer le code et titre affichés dans la popup
    4. Fermer la popup (clic sur cd_close)
    5. Cliquer sur le bouton "Vedi il codice" suivant
    6. Répéter jusqu'à avoir tous les codes
    
    Args:
        url: URL de la page codice-sconto.net (ex: https://ubereats.codice-sconto.net/)
    
    Returns:
        Liste de dict avec tous les codes trouvés
    """
    driver = get_driver()
    results = []
    
    try:
        print(f"[CodiceSconto] Accès à l'URL: {url}")
        driver.get(url)
        time.sleep(3)
        
        # Accepter les cookies si présents
        try:
            cookie_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accetta') or contains(text(), 'accetta') or contains(text(), 'Accept') or contains(text(), 'OK')]"))
            )
            cookie_btn.click()
            time.sleep(1)
        except:
            pass
        
        original_window = driver.current_window_handle
        
        # Trouver les boutons "Vedi il codice" (liens avec classe _code_btn)
        see_code_buttons = driver.find_elements(By.CSS_SELECTOR, "a._code_btn")
        
        if not see_code_buttons:
            # Fallback: chercher par le texte "Vedi il codice"
            see_code_buttons = driver.find_elements(By.XPATH, "//a[.//p[contains(text(), 'Vedi il codice')]]")
        
        if not see_code_buttons:
            print("[CodiceSconto] Aucun code disponible sur cette page")
            return results
        
        print(f"[CodiceSconto] {len(see_code_buttons)} boutons 'Vedi il codice' trouvés")
        
        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_button = see_code_buttons[0]
        
        # Récupérer le titre du premier code (depuis la page principale - div.hidden_3)
        try:
            container = first_button.find_element(By.XPATH, "./ancestor::div[contains(@class, 'codice-scontonet_MYUVPJ')]")
            title_element = container.find_element(By.CSS_SELECTOR, "div.hidden_3")
            first_title = title_element.text.strip()
        except:
            first_title = "Offerta 1"
        
        print(f"[CodiceSconto] Clic sur le premier code: {first_title[:50]}...")
        
        windows_before = set(driver.window_handles)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_button)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", first_button)
        
        # Attendre le nouvel onglet
        time.sleep(2)
        
        windows_after = set(driver.window_handles)
        new_windows = windows_after - windows_before
        
        if not new_windows:
            print("[CodiceSconto] Aucun nouvel onglet ouvert")
            return results
        
        # Switcher vers le nouvel onglet
        new_window = new_windows.pop()
        driver.switch_to.window(new_window)
        print("[CodiceSconto] Switché vers le nouvel onglet")
        time.sleep(2)
        
        # Maintenant on est sur le nouvel onglet avec la popup ouverte
        # On va boucler: récupérer code -> fermer popup -> cliquer sur suivant
        
        max_iterations = 30  # Sécurité
        clicked_count = 0  # Compteur de boutons cliqués (indépendant des résultats)
        
        for iteration in range(max_iterations):
            print(f"[CodiceSconto] --- Itération {iteration + 1} ---")
            
            # 1. Attendre que la popup soit bien chargée
            time.sleep(2)
            
            # 2. Récupérer le code affiché dans la popup (div.undefined avec le code court)
            code = None
            try:
                # Le code est dans un div avec class "undefined codicescontonet" qui contient un texte court
                code_elements = driver.find_elements(By.CSS_SELECTOR, "div.undefined.codicescontonet")
                for el in code_elements:
                    text = el.text.strip()
                    # Le code est généralement court (5-15 caractères) et sans espaces
                    if text and len(text) >= 3 and len(text) <= 20 and ' ' not in text:
                        code = text
                        print(f"[CodiceSconto] Code trouvé: {code}")
                        break
            except Exception as e:
                print(f"[CodiceSconto] Erreur recherche code: {str(e)[:30]}")
            
            if not code:
                try:
                    # Alternative: chercher dans un span
                    code_elements = driver.find_elements(By.CSS_SELECTOR, "span.undefined.codicescontonet")
                    for el in code_elements:
                        text = el.text.strip()
                        if text and len(text) >= 3 and len(text) <= 20:
                            code = text
                            print(f"[CodiceSconto] Code trouvé via span: {code}")
                            break
                except:
                    pass
            
            # 3. Récupérer le titre de l'offre depuis la popup (p avec classe codice-scontonet_X1fs7j)
            current_title = None
            try:
                title_element = driver.find_element(By.CSS_SELECTOR, "p.codice-scontonet_X1fs7j")
                current_title = title_element.text.strip()
                print(f"[CodiceSconto] Titre trouvé: {current_title[:50]}...")
            except Exception as e:
                print(f"[CodiceSconto] Erreur titre popup: {str(e)[:30]}")
            
            if not current_title:
                current_title = f"Offerta {iteration + 1}"
            
            if code and len(code) >= 3 and code not in [r['code'] for r in results]:
                results.append({
                    "success": True,
                    "code": code,
                    "title": current_title,
                    "message": "Code extrait avec succès"
                })
                print(f"[CodiceSconto] ✅ Code: {code} -> {current_title[:40]}...")
            else:
                print(f"[CodiceSconto] ⚠️ Code non trouvé ou doublon")
            
            # 4. Fermer la popup en cliquant sur cd_close
            popup_closed = False
            try:
                close_icon = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.cd_close"))
                )
                driver.execute_script("arguments[0].click();", close_icon)
                popup_closed = True
                print("[CodiceSconto] Popup fermée via cd_close")
                time.sleep(1)
            except:
                pass
            
            if not popup_closed:
                try:
                    # Alternative: chercher par alt="close icon"
                    close_btn = driver.find_element(By.XPATH, "//img[@alt='close icon']/ancestor::div[1]")
                    driver.execute_script("arguments[0].click();", close_btn)
                    popup_closed = True
                    print("[CodiceSconto] Popup fermée via close icon")
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
            
            # 5. Chercher le prochain bouton "Vedi il codice" sur cette page
            time.sleep(0.5)
            
            next_buttons = driver.find_elements(By.CSS_SELECTOR, "a._code_btn")
            
            if not next_buttons:
                next_buttons = driver.find_elements(By.XPATH, "//a[.//p[contains(text(), 'Vedi il codice')]]")
            
            # Incrémenter le compteur de clics (indépendant du nombre de codes trouvés)
            clicked_count += 1
            
            if clicked_count >= len(next_buttons):
                print("[CodiceSconto] Plus de boutons 'Vedi il codice' disponibles")
                break
            
            # Cliquer sur le bouton suivant (à l'index clicked_count)
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
                    print(f"[CodiceSconto] Switché vers nouvel onglet pour code {clicked_count + 1}")
                    time.sleep(1)
                else:
                    print("[CodiceSconto] Pas de nouvel onglet détecté")
                    
            except Exception as e:
                print(f"[CodiceSconto] Erreur clic suivant: {str(e)[:30]}")
                break
        
        print(f"[CodiceSconto] Total: {len(results)} codes récupérés")
        return results
        
    except Exception as e:
        print(f"[CodiceSconto] Erreur générale: {str(e)}")
        return results
    
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    test_url = "https://ubereats.codice-sconto.net/"
    
    print("=" * 60)
    print("TEST SCRAPER CODICE-SCONTO.NET - TOUS LES CODES")
    print("=" * 60)
    
    results = scrape_codicescontonet_all(test_url)
    
    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes trouvés")
    print("=" * 60)
    for i, result in enumerate(results):
        print(f"  [{i+1}] Code: {result['code']} -> {result['title'][:50]}...")
    print("=" * 60)
