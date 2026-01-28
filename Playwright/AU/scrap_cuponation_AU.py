"""
Script Playwright pour scraper TOUS les codes Cuponation Australie (AU uniquement)
- Plus rapide et stable que Selenium
- Scrape JUSTE les marchands australiens Cuponation
- Charge les données depuis Google Sheets
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Ajouter le dossier parent pour importer gsheet_loader
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls
from gsheet_writer import append_to_gsheet


def scrape_cuponation_all(page, context, url):
    """
    Scrape TOUS les codes d'une page Cuponation avec Playwright.
    Logique identique au script FastAPI (scraper_cuponation_es.py):
    1. Cliquer sur le premier bouton "Ver código" -> nouvel onglet s'ouvre avec popup
    2. Récupérer le code (h4 avec classe b8qpi79)
    3. Récupérer le titre (h4 avec classes az57m40 az57m46 sans b8qpi79)
    4. Fermer la popup (CloseIcon)
    5. Cliquer sur le bouton suivant
    6. Répéter jusqu'à avoir tous les codes
    """
    results = []
    affiliate_link = None
    
    try:
        print(f"[Cuponation] Accès à l'URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)  # Optimisé: 4000 -> 2500
        
        # Accepter cookies
        try:
            page.click("button:has-text('Accept'), button:has-text('Accepter'), button:has-text('Aceptar'), button:has-text('Accetta'), button:has-text('Agree')", timeout=3000)
            page.wait_for_timeout(500)  # Optimisé: 1000 -> 500
        except:
            pass
        
        # Trouver tous les boutons de code (exclure section expirée jkau50 et marcas similares _1hla7140)
        # Utilisation de XPath car :has-ancestor n'est pas supporté par Playwright
        # Essayer "See code" (AU) en premier
        get_code_buttons = page.locator("xpath=//div[@role='button'][@title='See code'][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]")
        count = get_code_buttons.count()
        
        if count == 0:
            # Essayer avec "Ver código" (ES)
            get_code_buttons = page.locator("xpath=//div[@role='button'][@title='Ver código'][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]")
            count = get_code_buttons.count()
        
        if count == 0:
            # Essayer avec "Get Code"
            get_code_buttons = page.locator("xpath=//div[@role='button'][@title='Get Code'][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]")
            count = get_code_buttons.count()
        
        if count == 0:
            # Essayer avec "Ottieni codice" (IT)
            get_code_buttons = page.locator("xpath=//div[@role='button'][@title='Ottieni codice'][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]")
            count = get_code_buttons.count()
        
        if count == 0:
            # Fallback générique - tous les boutons avec "code" dans le title
            get_code_buttons = page.locator("xpath=//div[@role='button'][contains(translate(@title, 'CODE', 'code'), 'code')][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]")
            count = get_code_buttons.count()
        
        print(f"[Cuponation] {count} boutons de code trouvés")
        
        if count == 0:
            print("[Cuponation] Aucun code disponible sur cette page")
            return results
        
        processed_codes = set()
        processed_titles = set()  # Éviter doublons de titres aussi
        
        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_btn = get_code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(300)  # Optimisé: 500 -> 300
        
        # Récupérer le titre du premier code
        first_title = None
        try:
            card = first_btn.locator("xpath=ancestor::div[@data-testid='vouchers-ui-voucher-card']")
            first_title = card.locator("div[data-testid='vouchers-ui-voucher-card-description'] h3, div[class*='az57m4e']").first.inner_text().strip()
        except:
            pass  # Ne pas mettre de valeur par défaut
        
        if first_title:
            print(f"[Cuponation] Clic sur le premier code: {first_title[:50]}...")
        else:
            print(f"[Cuponation] Clic sur le premier code (titre non trouvé)")
        
        with context.expect_page() as new_page_info:
            first_btn.click()
        
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded")
        new_page.wait_for_timeout(1500)  # Optimisé: 2000 -> 1500
        
        # CAPTURE DU LIEN AFFILIÉ - La page ORIGINALE se redirige vers le marchand
        try:
            for _ in range(10):
                current_url = page.url
                if "cuponation" not in current_url.lower():
                    affiliate_link = current_url
                    print(f"[Cuponation] 🔗 Affiliate captured: {affiliate_link[:60]}...")
                    break
                page.wait_for_timeout(500)
            if not affiliate_link:
                print(f"[Cuponation] ⚠️ No affiliate link captured (page stayed on cuponation)")
        except Exception as e:
            print(f"[Cuponation] ⚠️ Error capturing affiliate: {str(e)[:30]}")
        
        print("[Cuponation] Switché vers le nouvel onglet")
        
        max_iterations = count + 5
        
        for iteration in range(max_iterations):
            print(f"[Cuponation] --- Itération {iteration + 1} ---")
            
            # Attendre que la popup soit bien chargée
            new_page.wait_for_timeout(1500)  # Optimisé: 2000 -> 1500
            
            code = None
            current_title = None
            
            # 1. Récupérer le code dans la popup (h4 avec classe b8qpi79)
            try:
                code_elem = new_page.locator("h4.b8qpi79").first
                if code_elem.count() > 0:
                    code = code_elem.inner_text().strip()
                    print(f"[Cuponation] Code trouvé via h4.b8qpi79: {code}")
            except:
                pass
            
            if not code:
                try:
                    # Fallback: chercher via data-testid
                    code_elem = new_page.locator("span[data-testid='voucherPopup-codeHolder-voucherType-code'] h4").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                        print(f"[Cuponation] Code trouvé via data-testid: {code}")
                except:
                    pass
            
            if not code:
                try:
                    # Fallback: h4 avec classe b8qpi7*
                    code_elems = new_page.locator("h4[class*='b8qpi7']")
                    for i in range(code_elems.count()):
                        text = code_elems.nth(i).inner_text().strip()
                        if text and 3 <= len(text) <= 30:
                            code = text
                            print(f"[Cuponation] Code trouvé via fallback: {code}")
                            break
                except:
                    pass
            
            # 2. Récupérer le titre de l'offre depuis la popup (h4 avec classes az57m40 az57m46 sans b8qpi79)
            try:
                title_elem = new_page.locator("h4.az57m40.az57m46:not(.b8qpi79)").first
                if title_elem.count() > 0:
                    current_title = title_elem.inner_text().strip()
                    print(f"[Cuponation] Titre trouvé: {current_title[:50]}...")
            except:
                pass
            
            # Fallback: chercher h4 qui n'est pas le code
            if not current_title:
                try:
                    h4_elems = new_page.locator("h4")
                    for i in range(h4_elems.count()):
                        text = h4_elems.nth(i).inner_text().strip()
                        if text and text != code and len(text) > 15:
                            current_title = text
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
                print(f"[Cuponation] ✅ Code: {code} -> {current_title[:40]}...")
            else:
                print(f"[Cuponation] ⚠️ Code non trouvé ou doublon (code ou titre)")
            
            # 3. Fermer la popup en cliquant sur l'icône CloseIcon
            popup_closed = False
            try:
                close_icon = new_page.locator("span[data-testid='CloseIcon']").first
                if close_icon.count() > 0:
                    close_icon.click()
                    popup_closed = True
                    print("[Cuponation] Popup fermée via CloseIcon")
                    new_page.wait_for_timeout(500)  # Optimisé: 1000 -> 500
            except:
                pass
            
            if not popup_closed:
                try:
                    # Fallback: bouton parent du CloseIcon
                    close_btn = new_page.locator("span[data-testid='CloseIcon']").locator("xpath=ancestor::*[@role='button'][1]").first
                    if close_btn.count() > 0:
                        close_btn.click()
                        popup_closed = True
                        print("[Cuponation] Popup fermée via bouton parent")
                        new_page.wait_for_timeout(500)  # Optimisé: 1000 -> 500
                except:
                    pass
            
            # 4. Chercher le prochain bouton sur cette page
            new_page.wait_for_timeout(300)  # Optimisé: 500 -> 300
            
            # Essayer "See code" (AU) en premier
            next_buttons = new_page.locator("xpath=//div[@role='button'][@title='See code'][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]")
            next_count = next_buttons.count()
            
            if next_count == 0:
                # Essayer avec "Ver código" (ES)
                next_buttons = new_page.locator("xpath=//div[@role='button'][@title='Ver código'][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]")
                next_count = next_buttons.count()
            
            if next_count == 0:
                next_buttons = new_page.locator("xpath=//div[@role='button'][@title='Get Code'][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]")
                next_count = next_buttons.count()
            
            if next_count == 0:
                next_buttons = new_page.locator("xpath=//div[@role='button'][@title='Ottieni codice'][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]")
                next_count = next_buttons.count()
            
            if next_count == 0:
                next_buttons = new_page.locator("xpath=//div[@role='button'][contains(translate(@title, 'CODE', 'code'), 'code')][not(ancestor::div[contains(@class, 'jkau50')])][not(ancestor::div[contains(@class, '_1hla7140')])]")
                next_count = next_buttons.count()
            
            # On doit cliquer sur le bouton à l'index = iteration + 1 (on a déjà traité iteration+1 boutons)
            current_index = iteration + 1
            
            if current_index >= next_count:
                print("[Cuponation] Plus de boutons disponibles")
                break
            
            # 5. Cliquer sur le bouton suivant
            next_btn = next_buttons.nth(current_index)
            try:
                next_btn.scroll_into_view_if_needed()
                new_page.wait_for_timeout(200)  # Optimisé: 300 -> 200
                
                with context.expect_page() as next_page_info:
                    next_btn.click()
                
                next_new_page = next_page_info.value
                next_new_page.wait_for_load_state("domcontentloaded")
                print(f"[Cuponation] Switché vers nouvel onglet pour code {current_index + 1}")
                new_page.close()
                new_page = next_new_page
                new_page.wait_for_timeout(800)  # Optimisé: 1000 -> 800
                
            except Exception as e:
                print(f"[Cuponation] Erreur clic suivant: {str(e)[:30]}")
                break
        
        try:
            new_page.close()
        except:
            pass
        
        print(f"[Cuponation] Total: {len(results)} codes récupérés")
        
    except Exception as e:
        print(f"[Cuponation] ❌ Erreur générale: {str(e)[:50]}")
    
    return results, affiliate_link


def main():
    # Charger les données depuis Google Sheets
    competitor_data = get_competitor_urls("AU", "cuponation")
    
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
            merchant_name = merchant_row.get('Merchant_slug', 'Unknown')
            country = merchant_row.get('Country', 'AU')
            
            print(f"\n[{idx}/{len(competitor_data)}] 🏪 {merchant_name} ({country})")
            print(f"   URL: {url[:60]}...")
            
            try:
                codes, affiliate_link = scrape_cuponation_all(page, context, url)
                print(f"   ✅ {len(codes)} codes trouvés")
                
                for code_info in codes:
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": country,
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_name,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "cuponation",
                        "Competitor_URL": url,
                        "Affiliate_Link": affiliate_link or "",
                        "Code": code_info.get("code", ""),
                        "Title": code_info.get("title", "")
                    })
            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:50]}")
            
            print(f"   📝 Total: {len(all_results)} codes")
        
        browser.close()
    
    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="Cuponation AU")
        
        print(f"\n{'='*60}")
        print(f"✅ CUPONATION AU TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")


if __name__ == "__main__":
    main()
