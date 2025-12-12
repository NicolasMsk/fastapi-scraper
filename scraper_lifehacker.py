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
            "//button[contains(text(), 'OK')]",
            "//button[contains(@class, 'accept')]",
            "//*[@id='onetrust-accept-btn-handler']"
        ]
        for selector in cookie_selectors:
            try:
                cookie_button = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                cookie_button.click()
                print("[Lifehacker] Cookie banner fermé")
                time.sleep(1)
                return
            except:
                continue
    except:
        pass


def scrape_lifehacker_all(url):
    """
    Scrape TOUS les codes d'une page Lifehacker AU.
    
    Avantage: Les codes sont directement dans le HTML (span.btn-peel__secret)
    donc pas besoin de cliquer sur les boutons !
    
    On exclut les offres expirées (class promotion-discount-card--expired)
    
    Args:
        url: URL de la page Lifehacker (ex: https://au.lifehacker.com/coupons/emirates.com/)
    
    Returns:
        Liste de dict avec tous les codes trouvés
    """
    driver = get_driver()
    results = []
    
    try:
        print(f"[Lifehacker] Accès à l'URL: {url}")
        driver.get(url)
        time.sleep(3)
        
        close_cookie_banner(driver)
        
        # Trouver tous les boutons "Get Code" qui ne sont PAS dans une carte expirée
        # Les codes expirés ont la classe "promotion-discount-card--expired" sur leur parent
        code_buttons = driver.find_elements(
            By.XPATH, 
            "//div[contains(@class, 'btn-peel') and not(ancestor::*[contains(@class, 'promotion-discount-card--expired')])]"
        )
        
        total_buttons = len(code_buttons)
        print(f"[Lifehacker] {total_buttons} boutons 'Get Code' trouvés (hors expirés)")
        
        if total_buttons == 0:
            print("[Lifehacker] Aucun code disponible sur cette page")
            return results
        
        # Extraire les codes directement depuis le HTML (pas besoin de cliquer!)
        for idx, button in enumerate(code_buttons):
            try:
                # Le code est dans span.btn-peel__secret
                code_element = button.find_element(By.CSS_SELECTOR, "span.btn-peel__secret")
                code = code_element.text.strip()
                
                # Le titre est dans l'attribut data-promotion-title du bouton
                title = button.get_attribute("data-promotion-title")
                if not title:
                    title = f"Offre {idx + 1}"
                
                if code and len(code) >= 3:
                    # Vérifier que ce n'est pas un doublon
                    if code not in [r['code'] for r in results]:
                        results.append({
                            "success": True,
                            "code": code,
                            "title": title,
                            "message": "Code extrait avec succès"
                        })
                        print(f"[Lifehacker] ✅ Code: {code} -> {title[:50]}...")
                    else:
                        print(f"[Lifehacker] ⚠️ Code doublon ignoré: {code}")
                else:
                    print(f"[Lifehacker] ⚠️ Code invalide ou vide pour l'offre {idx + 1}")
                    
            except Exception as e:
                print(f"[Lifehacker] ⚠️ Erreur extraction code {idx + 1}: {str(e)[:30]}")
        
        print(f"[Lifehacker] Total: {len(results)} codes récupérés")
        return results
        
    except Exception as e:
        print(f"[Lifehacker] Erreur générale: {str(e)}")
        return results
    
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    test_url = "https://au.lifehacker.com/coupons/emirates.com/"
    
    print("=" * 60)
    print("TEST SCRAPER LIFEHACKER AU - TOUS LES CODES")
    print("=" * 60)
    
    results = scrape_lifehacker_all(test_url)
    
    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes trouvés")
    print("=" * 60)
    for i, result in enumerate(results):
        print(f"  [{i+1}] Code: {result['code']} -> {result['title'][:50]}...")
    print("=" * 60)
