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
    
    # ⚡ OPTIMISATIONS DE VITESSE ⚡
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.page_load_strategy = 'none'
    
    return webdriver.Chrome(options=chrome_options)


def scrape_hotukdeals_single(url, title):
    """
    Scrape un seul code HotUKDeals pour un titre donné
    
    Args:
        url: URL de la page HotUKDeals
        title: Titre de l'offre à chercher
    
    Returns:
        Dict avec le statut et le code trouvé
    """
    driver = get_driver()
    
    try:
        print(f"\n🔍 Chargement de: {url}")
        driver.get(url)
        time.sleep(3)
        
        # Gérer les popups/banners
        try:
            close_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'close') or contains(@aria-label, 'Close')]")
            for btn in close_buttons:
                try:
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.5)
                except:
                    pass
        except:
            pass
        
        hotkudeals_window = driver.current_window_handle
        
        # Chercher tous les titres d'offres dans les h3
        offer_h3s = driver.find_elements(By.XPATH, "//h3")
        print(f"   🔎 {len(offer_h3s)} offres sur la page")
        
        # Matching exact (ignorer la casse et espaces multiples)
        expected_clean = ' '.join(title.lower().split())
        
        for span_idx, offer_h3 in enumerate(offer_h3s):
            try:
                offer_title = offer_h3.text.strip()
                
                if not offer_title:
                    continue
                
                offer_clean = ' '.join(offer_title.lower().split())
                
                if expected_clean == offer_clean:
                    print(f"   ✅ Match exact trouvé: {offer_title[:50]}")
                    
                    # Trouver le conteneur parent
                    try:
                        container = offer_h3.find_element(By.XPATH, "./ancestor::div[@class='_6tavkoc']")
                    except:
                        container = offer_h3.find_element(By.XPATH, "./ancestor::div[.//div[@role='button' and contains(., 'See Code')]][1]")
                    
                    # Chercher le bouton "See Code"
                    try:
                        see_code_button = container.find_element(By.XPATH, ".//div[@role='button' and contains(., 'See Code')]")
                    except:
                        see_code_button = container.find_element(By.XPATH, ".//*[contains(text(), 'See Code')]")
                    
                    # Mémoriser les onglets avant le clic
                    windows_before = set(driver.window_handles)
                    
                    # Scroll et clic
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", see_code_button)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", see_code_button)
                    
                    # Attendre qu'un nouvel onglet s'ouvre
                    time.sleep(3)
                    
                    # Trouver le nouvel onglet
                    windows_after = set(driver.window_handles)
                    new_windows = windows_after - windows_before
                    
                    if new_windows:
                        new_window = new_windows.pop()
                        driver.switch_to.window(new_window)
                        print(f"      📱 Switché vers nouvel onglet")
                        time.sleep(2)
                        
                        # Récupérer le code et FINI !
                        try:
                            code_element = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, "//h4[contains(@class, 'b8qpi79')]"))
                            )
                            code = code_element.text.strip()
                            print(f"      ✅ CODE: {code}")
                            
                            return {
                                "success": True,
                                "code": code,
                                "title": offer_title,
                                "message": "Code trouvé avec succès"
                            }
                            
                        except Exception as e:
                            print(f"      ❌ Code non trouvé: {e}")
                            return {
                                "success": False,
                                "code": None,
                                "title": offer_title,
                                "message": f"Code non trouvé: {str(e)}"
                            }
                    else:
                        return {
                            "success": False,
                            "code": None,
                            "title": offer_title,
                                "message": "Aucun nouvel onglet détecté"
                            }
                        
            except Exception as e:
                continue
        
        return {
            "success": False,
            "code": None,
            "title": title,
            "message": "Titre non trouvé sur la page"
        }
        
    except Exception as e:
        return {
            "success": False,
            "code": None,
            "title": title,
            "message": f"Erreur lors du scraping: {str(e)}"
        }
    
    finally:
        try:
            driver.quit()
        except:
            pass
