from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time


def get_driver():
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
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # OPTIMISATIONS EXTRÊMES POUR RAILWAY (512MB RAM)
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_argument('--crash-dumps-dir=/tmp')
    chrome_options.add_argument('--disable-crash-reporter')
    chrome_options.add_argument('--disable-background-networking')
    chrome_options.add_argument('--disable-default-apps')
    chrome_options.add_argument('--disable-hang-monitor')
    chrome_options.add_argument('--disable-prompt-on-repost')
    chrome_options.add_argument('--disable-sync')
    chrome_options.add_argument('--disable-translate')
    chrome_options.add_argument('--metrics-recording-only')
    chrome_options.add_argument('--safebrowsing-disable-auto-update')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    
    # Bloquer le chargement des ressources lourdes
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
        "disk-cache-size": 4096
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.page_load_strategy = 'eager'  # Ne pas attendre que tout charge (juste le DOM)
    
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Bloquer les domaines de pub/tracking connus pour économiser la RAM
    driver.execute_cdp_cmd('Network.setBlockedURLs', {
        "urls": [
            "*.doubleclick.net", "*.google-analytics.com", "*.facebook.com", 
            "*.twitter.com", "*.googlesyndication.com", "*.criteo.com",
            "*.moatads.com", "*.amazon-adsystem.com", "*.adnxs.com"
        ]
    })
    driver.execute_cdp_cmd('Network.enable', {})
    
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


def close_cookie_banner(driver, timeout=0.5):
    try:
        cookie_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Consent')]"))
        )
        cookie_button.click()
        time.sleep(0.1)
    except:
        pass


def scrape_retailmenot_all(url):
    """
    Scrape TOUS les codes promo d'une page RetailMeNot.
    
    Args:
        url: URL de la page RetailMeNot (ex: https://www.retailmenot.com/view/asos.com)
    
    Returns:
        Liste de dict avec tous les codes trouvés
    """
    driver = get_driver()
    results = []
    
    try:
        print(f"[RetailMeNot] Accès à l'URL: {url}")
        driver.get(url)
        
        time.sleep(2)
        try:
            driver.execute_script("window.stop();")
        except:
            pass
        
        time.sleep(1)
        close_cookie_banner(driver, timeout=0.5)
        
        offer_links = driver.find_elements(By.XPATH, "//a[@data-component-class='offer_strip']")
        print(f"[RetailMeNot] {len(offer_links)} offres trouvées")
        
        if not offer_links:
            print("[RetailMeNot] Aucune offre trouvée")
            return results
        
        original_window = driver.current_window_handle
        original_windows = set(driver.window_handles)
        
        first_offer = offer_links[0]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", first_offer)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", first_offer)
        print("[RetailMeNot] Premier clic pour révéler les codes...")
        
        time.sleep(3)
        
        new_windows = set(driver.window_handles)
        new_tabs = new_windows - original_windows
        
        if new_tabs:
            retailmenot_window = None
            for new_window in new_tabs:
                driver.switch_to.window(new_window)
                current_url = driver.current_url
                print(f"[RetailMeNot] Nouvel onglet: {current_url}")
                
                if "retailmenot" in current_url:
                    retailmenot_window = new_window
                    time.sleep(2)
            
            if retailmenot_window:
                driver.switch_to.window(retailmenot_window)
            else:
                driver.switch_to.window(original_window)
        
        time.sleep(2)
        
        print("[RetailMeNot] Scroll de la page...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        print("[RetailMeNot] Récupération de tous les codes...")
        
        codes_data = driver.execute_script("""
            var results = [];
            var offers = document.querySelectorAll('a[data-component-class="offer_strip"]');
            
            offers.forEach(function(offer) {
                var codeDiv = offer.querySelector('div.font-bold.tracking-wider');
                var code = codeDiv ? codeDiv.textContent.trim() : null;
                
                var titleH3 = offer.querySelector('h3');
                var title = titleH3 ? titleH3.textContent.trim() : null;
                
                if (code && title && code.length >= 3) {
                    results.push({code: code, title: title});
                }
            });
            
            return results;
        """)
        
        print(f"[RetailMeNot] {len(codes_data)} offres trouvées via JavaScript")
        
        for item in codes_data:
            code = item['code']
            if code.lower() in ['get deal', 'see deal', 'show deal', 'view deal']:
                continue
                
            results.append({
                "success": True,
                "code": code,
                "title": item['title'],
                "message": "Code extrait avec succès"
            })
            print(f"[RetailMeNot] {code} -> {item['title'][:50]}...")
        
        print(f"[RetailMeNot] Total: {len(results)} codes récupérés")
        return results
        
    except Exception as e:
        print(f"[RetailMeNot] Erreur: {str(e)}")
        return results
    
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    test_url = "https://www.retailmenot.com/view/asos.com"
    
    print("=" * 60)
    print("TEST SCRAPER RETAILMENOT - TOUS LES CODES")
    print("=" * 60)
    
    results = scrape_retailmenot_all(test_url)
    
    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes trouvés")
    print("=" * 60)
    for i, result in enumerate(results):
        print(f"  [{i+1}] Code: {result['code']} -> {result['title'][:50]}...")
    print("=" * 60)
