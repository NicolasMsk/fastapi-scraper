"""
Script Playwright pour scraper TOUS les codes Chollometro (Espagne)
- Plus rapide et stable que Selenium
- Extrait les URLs uniques Chollometro du CSV
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_chollometro_all(page, context, url):
    """
    Scrape TOUS les codes d'une page Chollometro avec Playwright.
    Logique identique au script FastAPI:
    1. Cliquer sur le premier bouton "Ver cupón" -> nouvel onglet s'ouvre
    2. Récupérer le code (h4.b8qpi79) et le titre (h4.az57m40.az57m46) dans la popup
    3. Fermer la popup (CloseIcon)
    4. Cliquer sur le bouton suivant
    5. Répéter jusqu'à avoir tous les codes
    """
    results = []
    affiliate_link = None
    
    try:
        print(f"[Chollometro] Accès à l'URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)  # Réduit de 3000 à 1500
        
        # Accepter cookies
        try:
            page.click("button:has-text('Aceptar'), button:has-text('Accept')", timeout=2000)
            page.wait_for_timeout(500)
        except:
            pass
        
        # Fermer popups
        try:
            page.click("button[aria-label='Close'], button[aria-label='close'], button[aria-label='cerrar']", timeout=1000)
        except:
            pass
        
        # Trouver les boutons "Ver cupón" dans des offres VALIDES
        # Exclure les codes expirés (jkau50) et les codes d'autres marchands (_1hla7140)
        see_code_buttons = page.locator("xpath=//div[@role='button'][@title='Ver cupón'][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]")
        count = see_code_buttons.count()
        
        if count == 0:
            # Fallback: chercher tous les boutons Ver cupón sans jkau50
            see_code_buttons = page.locator("xpath=//div[@role='button'][@title='Ver cupón'][not(ancestor::div[contains(@class, 'jkau50')])]")
            count = see_code_buttons.count()
        
        if count == 0:
            print("[Chollometro] Aucun code disponible sur cette page")
            return results
        
        print(f"[Chollometro] {count} boutons 'Ver cupón' trouvés")
        
        processed_codes = set()
        processed_titles = set()
        
        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_btn = see_code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(300)  # Réduit de 500 à 300
        
        # Récupérer le titre du premier code depuis la page principale
        first_title = None
        try:
            container = first_btn.locator("xpath=ancestor::div[.//h3][1]")
            first_title = container.locator("h3").first.inner_text().strip()
        except:
            pass  # Ne pas mettre de valeur par défaut
        
        if first_title:
            print(f"[Chollometro] Clic sur le premier code: {first_title[:50]}...")
        else:
            print(f"[Chollometro] Clic sur le premier code (titre non trouvé)")
        
        try:
            with context.expect_page(timeout=15000) as new_page_info:
                first_btn.click()
            
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded", timeout=15000)
            new_page.wait_for_timeout(1000)
            
            # CAPTURE DU LIEN AFFILIÉ - La page ORIGINALE se redirige vers le marchand
            try:
                for _ in range(10):
                    current_url = page.url
                    if "chollometro" not in current_url.lower():
                        affiliate_link = current_url
                        print(f"[Chollometro] 🔗 Affiliate captured: {affiliate_link[:60]}...")
                        break
                    page.wait_for_timeout(500)
                if not affiliate_link:
                    print(f"[Chollometro] ⚠️ No affiliate link captured (page stayed on chollometro)")
            except Exception as e:
                print(f"[Chollometro] ⚠️ Error capturing affiliate: {str(e)[:30]}")

            print("[Chollometro] Switché vers le nouvel onglet")
        except PlaywrightTimeout:
            print("[Chollometro] ⚠️ Timeout sur le premier onglet, abandon")
            return results
        
        max_iterations = count + 5
        
        for iteration in range(max_iterations):
            print(f"[Chollometro] --- Itération {iteration + 1} ---")
            
            # Attendre que la popup soit bien chargée
            new_page.wait_for_timeout(1000)  # Réduit de 2000 à 1000
            
            code = None
            current_title = None
            
            # 1. Récupérer le code affiché dans la popup (h4 avec classe b8qpi79)
            try:
                code_elem = new_page.locator("h4.b8qpi79").first
                if code_elem.count() > 0:
                    code = code_elem.inner_text().strip()
                    print(f"[Chollometro] Code trouvé via h4.b8qpi79: {code}")
            except:
                pass
            
            if not code:
                try:
                    # Alternative: chercher h4 avec les classes b8qpi7*
                    code_elems = new_page.locator("h4[class*='b8qpi7']")
                    for i in range(code_elems.count()):
                        text = code_elems.nth(i).inner_text().strip()
                        if text and 3 <= len(text) <= 30:
                            code = text
                            print(f"[Chollometro] Code trouvé via XPath: {code}")
                            break
                except:
                    pass
            
            # 2. Récupérer le titre de l'offre depuis la popup (h4 avec az57m40 az57m46 SANS b8qpi79)
            try:
                title_elems = new_page.locator("h4.az57m40.az57m46")
                for i in range(title_elems.count()):
                    elem = title_elems.nth(i)
                    classes = elem.get_attribute("class") or ""
                    if "b8qpi79" not in classes:
                        text = elem.inner_text().strip()
                        if text and len(text) > 10:
                            current_title = text
                            print(f"[Chollometro] Titre trouvé: {current_title[:50]}...")
                            break
            except:
                pass
            
            # N'ajouter que si code ET titre sont trouvés (pas de valeur par défaut)
            if code and current_title and code not in processed_codes and current_title not in processed_titles:
                processed_codes.add(code)
                processed_titles.add(current_title)
                results.append({
                    "success": True,
                    "code": code,
                    "title": current_title,
                    "message": "Code extrait avec succès"
                })
                print(f"[Chollometro] ✅ Code: {code} -> {current_title[:40]}...")
            else:
                print(f"[Chollometro] ⚠️ Code non trouvé ou doublon")
            
            # 3. Fermer la popup en cliquant sur l'icône CloseIcon
            popup_closed = False
            try:
                close_icon = new_page.locator("span[data-testid='CloseIcon']").first
                if close_icon.count() > 0:
                    close_icon.click()
                    popup_closed = True
                    print("[Chollometro] Popup fermée via CloseIcon")
                    new_page.wait_for_timeout(500)  # Réduit de 1000 à 500
            except:
                pass
            
            if not popup_closed:
                try:
                    close_btn = new_page.locator("button[aria-label='close'], button[aria-label='Close'], button[aria-label='cerrar']").first
                    if close_btn.count() > 0:
                        close_btn.click()
                        popup_closed = True
                        print("[Chollometro] Popup fermée via aria-label")
                        new_page.wait_for_timeout(500)  # Réduit de 1000 à 500
                except:
                    pass
            
            # 4. Chercher le prochain bouton "Ver cupón" sur cette page (offres VALIDES seulement)
            new_page.wait_for_timeout(300)  # Réduit de 500 à 300
            
            next_buttons = new_page.locator("div[data-testid='vouchers-ui-voucher-card-description']:has(h3) div[role='button'][title='Ver cupón']")
            next_count = next_buttons.count()
            
            if next_count == 0:
                next_buttons = new_page.locator("div[role='button'][title='Ver cupón']")
                next_count = next_buttons.count()
            
            # On doit cliquer sur le bouton à l'index correspondant au nombre de codes déjà récupérés
            current_index = len(results)
            
            if current_index >= next_count:
                print("[Chollometro] Plus de boutons 'Ver cupón' disponibles")
                break
            
            # 5. Cliquer sur le bouton suivant
            next_btn = next_buttons.nth(current_index)
            try:
                next_btn.scroll_into_view_if_needed()
                new_page.wait_for_timeout(200)
                
                try:
                    with context.expect_page(timeout=15000) as next_page_info:
                        next_btn.click()
                    
                    next_new_page = next_page_info.value
                    next_new_page.wait_for_load_state("domcontentloaded", timeout=15000)
                    print(f"[Chollometro] Switché vers nouvel onglet pour code {current_index + 1}")
                    try:
                        new_page.close()
                    except:
                        pass
                    new_page = next_new_page
                    new_page.wait_for_timeout(500)
                except PlaywrightTimeout:
                    print(f"[Chollometro] ⚠️ Timeout switch onglet {current_index + 1}, skip")
                    continue
                
            except Exception as e:
                print(f"[Chollometro] Erreur clic suivant: {str(e)[:30]}")
                break
        
        try:
            new_page.close()
        except:
            pass
        
        print(f"[Chollometro] Total: {len(results)} codes récupérés")
        
    except Exception as e:
        print(f"[Chollometro] ❌ Erreur générale: {str(e)[:50]}")
    
    return results, affiliate_link


def main():
    """Scrape Chollometro ES depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")
    
    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("ES", "chollometro")
    print(f"📍 Chollometro: {len(competitor_data)} URLs uniques")
    
    all_results = []
    
    # Configuration pour éviter les "Page crashed"
    PAGE_REFRESH_INTERVAL = 25
    
    print(f"\n🚀 Lancement de Playwright...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        for idx, (merchant_row, url) in enumerate(competitor_data, 1):
            merchant_slug = merchant_row.get('Merchant_slug', 'Unknown')
            
            # Recréer la page périodiquement
            if idx > 1 and (idx - 1) % PAGE_REFRESH_INTERVAL == 0:
                print(f"\n🔄 Refresh de la page (prévention memory leak)...")
                try:
                    page.close()
                except:
                    pass
                for p_tab in context.pages:
                    try:
                        p_tab.close()
                    except:
                        pass
                page = context.new_page()
            
            print(f"\n[{idx}/{len(competitor_data)}] 🏪 {merchant_slug}")
            print(f"   URL: {url[:60]}...")
            
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    codes, affiliate_link = scrape_chollometro_all(page, context, url)
                    print(f"   ✅ {len(codes)} codes trouvés")
                    
                    for code_info in codes:
                        all_results.append({
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Country": "ES",
                            "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                            "Merchant_slug": merchant_slug,
                            "GPN_URL": merchant_row.get("GPN_URL", ""),
                            "Competitor_Source": "chollometro",
                            "Competitor_URL": url,
                            "Affiliate_Link": affiliate_link or "",
                            "Code": code_info.get("code", ""),
                            "Title": code_info.get("title", "")
                        })
                    break
                    
                except Exception as e:
                    error_msg = str(e)
                    if "Page crashed" in error_msg or "Target closed" in error_msg:
                        print(f"   ⚠️ Page crashed (attempt {attempt + 1}/{max_retries}), recréation...")
                        try:
                            page.close()
                        except:
                            pass
                        for p_tab in context.pages:
                            try:
                                p_tab.close()
                            except:
                                pass
                        page = context.new_page()
                        if attempt == max_retries - 1:
                            print(f"   ❌ Échec après {max_retries} tentatives")
                    else:
                        print(f"   ❌ Erreur: {error_msg[:50]}")
                        break
            
            print(f"   📝 Total: {len(all_results)} codes")
        
        browser.close()
    
    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="Chollometro ES")
        
        print(f"\n{'='*60}")
        print(f"✅ CHOLLOMETRO ES TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")


if __name__ == "__main__":
    main()
