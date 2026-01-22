"""
Script Playwright pour scraper TOUS les codes Cuponation Italie
- Plus rapide et stable que Selenium
- Logique identique au script FastAPI scraper_cuponation_it.py
- Filtre les offres avec "Codice" uniquement (pas "Offerta")
- Exclut les offres expirées et les offres similaires
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_cuponation_it_all(page, context, url):
    """
    Scrape TOUS les codes d'une page Cuponation Italie avec Playwright.
    Logique identique au script FastAPI (scraper_cuponation_it.py):
    1. Trouver les boutons UNIQUEMENT pour les offres avec "Codice" (pas "Offerta")
    2. Exclure les offres expirées (div.jkau50) et offres similaires
    3. Cliquer sur le premier bouton -> nouvel onglet s'ouvre avec popup
    4. Récupérer le code (h4 avec classe b8qpi79)
    5. Récupérer le titre (h4 avec classes az57m40 az57m46 sans b8qpi79)
    6. Fermer la popup (CloseIcon)
    7. Cliquer sur le bouton suivant
    8. Répéter jusqu'à avoir tous les codes
    """
    results = []
    
    try:
        print(f"[CuponationIT] Accès à l'URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Accepter cookies
        try:
            page.click("button:has-text('Accetta'), button:has-text('Accept')", timeout=3000)
            page.wait_for_timeout(1000)
        except:
            pass
        
        # Trouver les boutons cliquables UNIQUEMENT pour les offres avec "Codice" (pas "Offerta")
        # - Exclure les offres expirées (dans div.jkau50)
        # - Exclure les offres "similaires" d'autres marques
        # - Inclure seulement celles avec le label "Codice"
        
        # Sélecteur XPath: cartes voucher contenant "Codice", pas expirées, pas similaires
        get_code_buttons = page.locator(
            "xpath=//div[@data-testid='vouchers-ui-voucher-card'][.//div[contains(text(), 'Codice')]][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])][not(ancestor::div[@data-testid='similar-vouchers-widget'])]//div[contains(@class, 'p24wo04')]"
        )
        count = get_code_buttons.count()
        
        if count == 0:
            # Fallback: chercher les cartes avec la classe _6tavko6
            get_code_buttons = page.locator(
                "xpath=//div[contains(@class, '_6tavko6')][.//div[contains(text(), 'Codice')]][not(ancestor::div[contains(@class, 'jkau50')])]//div[contains(@class, 'p24wo04')]"
            )
            count = get_code_buttons.count()
        
        if count == 0:
            # Dernier fallback: tous les boutons p24wo04
            get_code_buttons = page.locator("div.p24wo04")
            count = get_code_buttons.count()
        
        print(f"[CuponationIT] {count} boutons 'Codice' trouvés (hors expirés et similaires)")
        
        if count == 0:
            print("[CuponationIT] Aucun code disponible sur cette page")
            return results
        
        processed_codes = set()
        processed_titles = set()
        
        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_btn = get_code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        
        # Récupérer le titre du premier code
        first_title = None
        try:
            container = first_btn.locator("xpath=ancestor::div[@data-testid='vouchers-ui-voucher-card-description']")
            first_title = container.locator("h3").first.inner_text().strip()
        except:
            pass  # Ne pas mettre de valeur par défaut
        
        if first_title:
            print(f"[CuponationIT] Clic sur le premier code: {first_title[:50]}...")
        else:
            print(f"[CuponationIT] Clic sur le premier code (titre non trouvé)")
        
        with context.expect_page() as new_page_info:
            first_btn.click()
        
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded")
        new_page.wait_for_timeout(2000)
        
        print("[CuponationIT] Switché vers le nouvel onglet")
        
        max_iterations = 30  # Sécurité
        clicked_count = 0  # Compteur de boutons cliqués
        
        for iteration in range(max_iterations):
            print(f"[CuponationIT] --- Itération {iteration + 1} ---")
            
            # Attendre que la popup soit bien chargée
            new_page.wait_for_timeout(2000)
            
            code = None
            current_title = None
            
            # 1. Récupérer le code affiché dans la popup (h4 avec classe b8qpi79)
            try:
                code_elem = new_page.locator("h4.b8qpi79").first
                if code_elem.count() > 0:
                    code = code_elem.inner_text().strip()
                    print(f"[CuponationIT] Code trouvé via h4.b8qpi79: {code}")
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
                            print(f"[CuponationIT] Code trouvé via fallback: {code}")
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
                            print(f"[CuponationIT] Titre trouvé: {current_title[:50]}...")
                            break
            except:
                pass
            
            # N'ajouter que si code ET titre sont trouvés (pas de valeur par défaut)
            if code and current_title and len(code) >= 3 and code not in processed_codes and current_title not in processed_titles:
                processed_codes.add(code)
                processed_titles.add(current_title)
                results.append({
                    "success": True,
                    "code": code,
                    "title": current_title,
                    "message": "Code extrait avec succès"
                })
                print(f"[CuponationIT] ✅ Code: {code} -> {current_title[:40]}...")
            else:
                print(f"[CuponationIT] ⚠️ Code ou titre non trouvé, ou doublon")
            
            # 3. Fermer la popup en cliquant sur l'icône CloseIcon
            popup_closed = False
            try:
                close_icon = new_page.locator("span[data-testid='CloseIcon']").first
                if close_icon.count() > 0:
                    close_icon.click()
                    popup_closed = True
                    print("[CuponationIT] Popup fermée via CloseIcon")
                    new_page.wait_for_timeout(1000)
            except:
                pass
            
            if not popup_closed:
                try:
                    close_btn = new_page.locator("button[aria-label='close'], button[aria-label='Close'], button[aria-label='chiudi']").first
                    if close_btn.count() > 0:
                        close_btn.click()
                        popup_closed = True
                        print("[CuponationIT] Popup fermée via aria-label")
                        new_page.wait_for_timeout(1000)
                except:
                    pass
            
            # 4. Chercher le prochain bouton sur cette page (UNIQUEMENT "Codice", pas "Offerta", pas "similaires")
            new_page.wait_for_timeout(500)
            
            next_buttons = new_page.locator(
                "xpath=//div[@data-testid='vouchers-ui-voucher-card'][.//div[contains(text(), 'Codice')]][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])][not(ancestor::div[@data-testid='similar-vouchers-widget'])]//div[contains(@class, 'p24wo04')]"
            )
            next_count = next_buttons.count()
            
            if next_count == 0:
                next_buttons = new_page.locator(
                    "xpath=//div[contains(@class, '_6tavko6')][.//div[contains(text(), 'Codice')]][not(ancestor::div[contains(@class, 'jkau50')])]//div[contains(@class, 'p24wo04')]"
                )
                next_count = next_buttons.count()
            
            if next_count == 0:
                next_buttons = new_page.locator("div.p24wo04")
                next_count = next_buttons.count()
            
            # Incrémenter le compteur de clics
            clicked_count += 1
            
            if clicked_count >= next_count:
                print("[CuponationIT] Plus de boutons disponibles")
                break
            
            # 5. Cliquer sur le bouton suivant
            next_btn = next_buttons.nth(clicked_count)
            try:
                next_btn.scroll_into_view_if_needed()
                new_page.wait_for_timeout(300)
                
                with context.expect_page() as next_page_info:
                    next_btn.click()
                
                next_new_page = next_page_info.value
                next_new_page.wait_for_load_state("domcontentloaded")
                print(f"[CuponationIT] Switché vers nouvel onglet pour code {clicked_count + 1}")
                new_page.close()
                new_page = next_new_page
                new_page.wait_for_timeout(1000)
                
            except Exception as e:
                print(f"[CuponationIT] Erreur clic suivant: {str(e)[:30]}")
                break
        
        try:
            new_page.close()
        except:
            pass
        
        print(f"[CuponationIT] Total: {len(results)} codes récupérés")
        
    except Exception as e:
        print(f"[CuponationIT] ❌ Erreur générale: {str(e)[:50]}")
    
    return results


def main():
    """Scrape Cuponation IT depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")
    
    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("IT", "cuponation")
    print(f"📍 Cuponation IT: {len(competitor_data)} URLs uniques")
    
    all_results = []
    
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
            
            print(f"\n[{idx}/{len(competitor_data)}] 🏪 {merchant_slug}")
            print(f"   URL: {url[:60]}...")
            
            try:
                codes = scrape_cuponation_it_all(page, context, url)
                print(f"   ✅ {len(codes)} codes trouvés")
                
                for code_info in codes:
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "IT",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "cuponation_it",
                        "Competitor_URL": url,
                        "Code": code_info.get("code", ""),
                        "Title": code_info.get("title", "")
                    })
            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:50]}")
            
            print(f"   📝 Total: {len(all_results)} codes")
        
        browser.close()
    
    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="Cuponation IT")
        
        print(f"\n{'='*60}")
        print(f"✅ CUPONATION IT TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")


if __name__ == "__main__":
    main()
