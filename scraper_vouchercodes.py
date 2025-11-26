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


def scrape_vouchercodes_single(url, title):
    """
    Scrape un seul code VoucherCodes pour un titre donné
    
    Args:
        url: URL de la page VoucherCodes
        title: Titre de l'offre à chercher
    
    Returns:
        Dict avec le statut et le code trouvé
    """
    driver = get_driver()
    
    try:
        print(f"\n🔍 Chargement de: {url}")
        driver.get(url)
        time.sleep(1.5)
        
        # Arrêter le chargement immédiatement
        try:
            driver.execute_script("window.stop();")
        except:
            pass
        
        time.sleep(0.3)
        
        # Gérer le cookie banner
        try:
            cookie_button = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            cookie_button.click()
            print("   ✅ Cookie banner fermé")
            time.sleep(0.5)
        except:
            print("   ℹ️ Pas de cookie banner")
            time.sleep(0.2)
        
        vouchercodes_window = driver.current_window_handle
        
        # Attendre que les offres se chargent (IMPORTANT pour le contenu dynamique)
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.align-middle"))
            )
            print(f"   ✅ Offres chargées")
        except:
            print(f"   ⚠️ Timeout: offres non trouvées avec le sélecteur")
        
        # Chercher tous les titres d'offres
        offer_spans = driver.find_elements(By.CSS_SELECTOR, "span.align-middle")
        print(f"   🔎 {len(offer_spans)} offres sur la page")
        
        # Matching exact (ignorer la casse et espaces multiples)
        expected_clean = ' '.join(title.lower().split())
        
        for span_idx, offer_span in enumerate(offer_spans):
            try:
                offer_title = offer_span.text.strip()
                
                if not offer_title:
                    continue
                
                offer_clean = ' '.join(offer_title.lower().split())
                
                if expected_clean == offer_clean:
                    print(f"   ✅ Match exact trouvé: {offer_title[:50]}")
                    
                    # Trouver le conteneur parent
                    try:
                        container = offer_span.find_element(By.XPATH, "./ancestor::article[1]")
                    except:
                        try:
                            container = offer_span.find_element(By.XPATH, "./ancestor::div[contains(@class, 'relative') and .//button][1]")
                        except:
                            container = offer_span.find_element(By.XPATH, "./ancestor::*[.//button[contains(., 'Get Code')]][1]")
                    
                    # Chercher le bouton "Get Code"
                    button = container.find_element(By.XPATH, ".//button[contains(., 'Get Code')]")
                    print(f"   🎯 Bouton 'Get Code' trouvé")
                    
                    # Mémoriser les onglets avant le clic
                    windows_before = set(driver.window_handles)
                    print(f"   📌 Onglets avant clic: {len(windows_before)}")
                    
                    # Scroll et clic
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(0.1)
                    button.click()
                    print(f"   ✅ Clic effectué sur le bouton")
                    
                    # Attendre qu'un nouvel onglet s'ouvre
                    time.sleep(1.5)
                    
                    # Trouver le nouvel onglet
                    windows_after = set(driver.window_handles)
                    new_windows = windows_after - windows_before
                    print(f"   📌 Onglets après clic: {len(windows_after)}")
                    print(f"   📌 Nouveaux onglets: {len(new_windows)}")
                    
                    if new_windows:
                        new_window = new_windows.pop()
                        driver.switch_to.window(new_window)
                        print(f"   📱 Switché vers nouvel onglet")
                        driver.execute_script("window.stop();")
                        time.sleep(1)
                        
                        # Récupérer le code et FINI !
                        try:
                            print(f"   🔍 Recherche du code...")
                            code_element = WebDriverWait(driver, 4).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "p[data-qa='el:code']"))
                            )
                            code = code_element.text.strip()
                            print(f"   ✅ CODE TROUVÉ: {code}")
                            
                            return {
                                "success": True,
                                "code": code,
                                "title": offer_title,
                                "message": "Code trouvé avec succès"
                            }
                            
                        except Exception as e:
                            print(f"   ❌ Code non trouvé avec CSS selector, tentative avec XPath: {e}")
                            # Essayer avec d'autres sélecteurs
                            try:
                                code_element = driver.find_element(By.XPATH, "//p[contains(@class, 'font-bold') and contains(@class, 'tracking-wide')]")
                                code = code_element.text.strip()
                                print(f"   ✅ CODE TROUVÉ (XPath): {code}")
                                
                                return {
                                    "success": True,
                                    "code": code,
                                    "title": offer_title,
                                    "message": "Code trouvé avec succès"
                                }
                            except:
                                print(f"   ❌ Code vraiment introuvable")
                                return {
                                    "success": False,
                                    "code": None,
                                    "title": offer_title,
                                    "message": f"Code non trouvé: {str(e)}"
                                }
                    else:
                        print(f"   ⚠️ PROBLÈME: Aucun nouvel onglet ne s'est ouvert!")
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
