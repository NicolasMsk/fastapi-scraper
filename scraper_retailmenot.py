from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import re


def get_driver():
    """Crée et retourne une instance du webdriver Chrome en mode headless"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # ⚡ OPTIMISATIONS DE VITESSE ⚡
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')  # Désactiver les images
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Bloquer les ressources inutiles (CSS, fonts, etc.)
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.cookies": 1,
        "profile.managed_default_content_settings.javascript": 1,
        "profile.managed_default_content_settings.plugins": 2,
        "profile.managed_default_content_settings.popups": 2,
        "profile.managed_default_content_settings.geolocation": 2,
        "profile.managed_default_content_settings.media_stream": 2,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.page_load_strategy = 'none'
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


def close_cookie_banner(driver, timeout=0.5):
    """Ferme la bannière de cookies"""
    try:
        cookie_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Consent')]"))
        )
        cookie_button.click()
        time.sleep(0.1)
    except:
        pass


def extract_code_from_copy_button(copy_button):
    """Extrait le code du bouton COPY"""
    try:
        onclick_attr = copy_button.get_attribute("onclick")
        if onclick_attr:
            match = re.search(r"navigator\.clipboard\.writeText\(['\"]([A-Z0-9]+)['\"]\)", onclick_attr)
            if match:
                return match.group(1)
        
        click_attr = copy_button.get_attribute("@click")
        if click_attr:
            match = re.search(r"navigator\.clipboard\.writeText\(['\"]([A-Z0-9]+)['\"]\)", click_attr)
            if match:
                return match.group(1)
        
        for attr in [onclick_attr, click_attr]:
            if attr:
                match = re.search(r"writeText\(['\"]([^'\"]+)['\"]\)", attr)
                if match:
                    code = match.group(1).strip()
                    if 3 <= len(code) <= 50:
                        return code
        
        return None
    except:
        return None


def extract_code_from_modal(driver, timeout=8):
    """Extrait le code de la modal - VERSION ROBUSTE"""
    try:
        driver.execute_script("window.onbeforeunload = null;")
    except:
        pass
    
    # Attendre un peu plus que la modal soit chargée
    time.sleep(1)
    
    # Essayer différents sélecteurs pour trouver le bouton copy
    selectors = [
        "//button[@data-component-class='copy_code']",
        "//button[contains(@class, 'copy')]",
        "//button[contains(text(), 'Copy')]",
        "//button[contains(@data-code, '')]"
    ]
    
    for selector in selectors:
        try:
            copy_button = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, selector))
            )
            
            code = extract_code_from_copy_button(copy_button)
            if code:
                return code
        except:
            continue
    
    # Si aucun bouton trouvé, essayer de chercher le code directement dans le DOM
    try:
        code_elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'code') or contains(@data-code, '')]")
        for elem in code_elements:
            text = elem.text.strip()
            if text and 3 <= len(text) <= 50:
                return text
    except:
        pass
    
    return None


def scrape_retailmenot_single(url, title):
    """
    Scrape un seul code RetailMeNot pour un titre donné
    
    Args:
        url: URL de la page RetailMeNot
        title: Titre de l'offre à chercher
    
    Returns:
        Dict avec le statut et le code trouvé
    """
    driver = get_driver()
    
    try:
        print(f"\n🔍 Chargement de: {url}")
        original_window = driver.current_window_handle
        
        # Charger la page avec gestion d'erreur
        try:
            driver.get(url)
        except Exception as e:
            print(f"   ⚠️ Erreur de chargement (ignorée): {e}")
        
        # Attendre le minimum que le contenu se charge
        time.sleep(1.5)
        
        # Arrêter le chargement immédiatement
        try:
            driver.execute_script("window.stop();")
        except:
            pass
        
        time.sleep(0.3)
        close_cookie_banner(driver, timeout=0.5)
        time.sleep(0.2)
        
        # Chercher les offres
        offer_links = driver.find_elements(By.XPATH, "//a[@data-component-class='offer_strip']")
        print(f"   🔎 {len(offer_links)} offres sur la page")
        
        if not offer_links:
            return {
                "success": False,
                "code": None,
                "title": title,
                "message": "Aucune offre trouvée sur la page"
            }
        
        # Normaliser le titre cherché
        target_normalized = ' '.join(title.lower().split())
        matching_index = None

        for i, offer in enumerate(offer_links):
            try:
                title_elem = offer.find_element(By.XPATH, ".//h3")
                title_text = title_elem.text.strip()
                title_normalized = ' '.join(title_text.lower().split())

                if title_normalized == target_normalized:
                    matching_index = i
                    print(f"   ✅ Match exact trouvé: {title_text[:50]}")
                    break
            except:
                continue

        if matching_index is None:
            return {
                "success": False,
                "code": None,
                "title": title,
                "message": "Titre non trouvé sur la page"
            }
        
        # Cliquer sur l'offre (LOGIQUE ORIGINALE QUI MARCHE)
        offer_links_fresh = driver.find_elements(By.XPATH, "//a[@data-component-class='offer_strip']")
        offer_to_click = offer_links_fresh[matching_index]
        
        driver.execute_script("arguments[0].scrollIntoView(true);", offer_to_click)
        time.sleep(0.1)
        driver.execute_script("arguments[0].click();", offer_to_click)
        print(f"   🎯 Clic effectué sur l'offre")
        
        # Attendre le nouvel onglet (timeout plus long)
        try:
            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
        except:
            return {
                "success": False,
                "code": None,
                "title": title,
                "message": "Aucun nouvel onglet détecté"
            }
        
        # Passer au nouvel onglet
        new_window = [w for w in driver.window_handles if w != original_window][0]
        driver.switch_to.window(new_window)
        print(f"   📱 Switché vers nouvel onglet")
        
        # Attendre plus longtemps que la modal se charge complètement
        time.sleep(1.5)
        
        # Extraire le code et FINI !
        print(f"   🔍 Recherche du code...")
        code = extract_code_from_modal(driver, timeout=8)
        
        if code:
            print(f"   ✅ CODE TROUVÉ: {code}")
            return {
                "success": True,
                "code": code,
                "title": title,
                "message": "Code trouvé avec succès"
            }
        else:
            return {
                "success": False,
                "code": None,
                "title": title,
                "message": "Code non trouvé dans la modal"
            }
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return {
            "success": False,
            "code": None,
            "title": title,
            "message": f"Erreur lors du scraping: {str(e)}"
        }
    
    finally:
        try:
            # Nettoyer tous les onglets supplémentaires
            for window in driver.window_handles[1:]:
                driver.switch_to.window(window)
                driver.close()
            driver.quit()
        except:
            pass
