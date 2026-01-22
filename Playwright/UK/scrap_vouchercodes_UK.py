"""
Script Playwright pour scraper TOUS les codes VoucherCodes (UK)
- Plus rapide et stable que Selenium
- Extrait les URLs uniques VoucherCodes du CSV
- Récupère TOUS les codes de chaque page
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_vouchercodes_all(page, context, url):
    """Scrape tous les codes d'une page VoucherCodes avec Playwright"""
    results = []
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        
        # Fermer cookie banner
        try:
            page.click("#onetrust-accept-btn-handler", timeout=3000)
            page.wait_for_timeout(500)
        except:
            pass
        
        # Trouver tous les boutons "Get Code" (exclure les offres Exclusive)
        # On cherche les boutons qui n'ont PAS de tag Exclusive dans leur conteneur parent
        get_code_buttons = page.locator("div.flex-offer:not(:has(span[data-qa='el:exclusiveTag'])) button[data-qa='el:offerPrimaryButton']:has-text('Get Code')")
        count = get_code_buttons.count()
        
        if count == 0:
            # Fallback sans filtre Exclusive
            get_code_buttons = page.locator("button[data-qa='el:offerPrimaryButton']:has-text('Get Code')")
            count = get_code_buttons.count()
        
        if count == 0:
            get_code_buttons = page.locator("button:has-text('Get Code')")
            count = get_code_buttons.count()
        
        if count == 0:
            return results
        
        processed_codes = set()
        processed_titles = set()
        
        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_btn = get_code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        
        with context.expect_page() as new_page_info:
            first_btn.click()
        
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded")
        new_page.wait_for_timeout(2000)
        
        # Itérer sur tous les codes
        max_iterations = count + 5
        
        for iteration in range(max_iterations):
            try:
                new_page.wait_for_timeout(1500)
                
                # Chercher le code dans la popup
                code = None
                title = None
                
                # Sélecteur principal pour VoucherCodes
                try:
                    code_elem = new_page.locator("p[data-qa='el:code']").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                except:
                    pass
                
                if not code:
                    # Fallback: chercher p.font-bold
                    try:
                        elems = new_page.locator("p.font-bold")
                        for i in range(elems.count()):
                            text = elems.nth(i).inner_text().strip()
                            if text and 3 <= len(text) <= 30:
                                code = text
                                break
                    except:
                        pass
                
                # Chercher le titre dans la popup
                try:
                    title_elem = new_page.locator("div[data-qa='el:offerTitle']").first
                    if title_elem.count() > 0:
                        title = title_elem.inner_text().strip()
                except:
                    pass  # Ne pas mettre de valeur par défaut
                
                # Vérifier si c'est une offre Exclusive (à ignorer)
                is_exclusive = False
                try:
                    exclusive_tag = new_page.locator("span[data-qa='el:exclusiveTag']")
                    if exclusive_tag.count() > 0:
                        is_exclusive = True
                except:
                    pass
                
                # N'ajouter que si code ET titre sont trouvés ET pas Exclusive
                if code and title and not is_exclusive and code not in processed_codes and title not in processed_titles:
                    processed_codes.add(code)
                    processed_titles.add(title)
                    results.append({"code": code, "title": title})
                
                # Fermer la popup
                try:
                    close_btn = new_page.locator("button:has(svg[data-qa='el:closeIcon'])").first
                    close_btn.click()
                    new_page.wait_for_timeout(500)
                except:
                    try:
                        close_btn = new_page.locator("button.rounded-full:has(svg)").first
                        close_btn.click()
                        new_page.wait_for_timeout(500)
                    except:
                        pass
                
                # Cliquer sur le prochain bouton "Get Code" (exclure Exclusive)
                next_buttons = new_page.locator("div.flex-offer:not(:has(span[data-qa='el:exclusiveTag'])) button[data-qa='el:offerPrimaryButton']:has-text('Get Code')")
                if next_buttons.count() == 0:
                    next_buttons = new_page.locator("button[data-qa='el:offerPrimaryButton']:has-text('Get Code')")
                if next_buttons.count() == 0:
                    next_buttons = new_page.locator("button:has-text('Get Code')")
                
                # L'index pour le prochain bouton est l'itération en cours (0-based devient 1 pour le 2ème bouton)
                current_index = iteration + 1
                
                if current_index >= next_buttons.count():
                    break
                
                next_btn = next_buttons.nth(current_index)
                next_btn.scroll_into_view_if_needed()
                new_page.wait_for_timeout(300)
                
                # Ouvrir dans un nouvel onglet
                with context.expect_page() as next_page_info:
                    next_btn.click()
                
                next_new_page = next_page_info.value
                next_new_page.wait_for_load_state("domcontentloaded")
                
                # Fermer l'ancien onglet et utiliser le nouveau
                new_page.close()
                new_page = next_new_page
                
            except Exception as e:
                break
        
        # Fermer le dernier onglet
        try:
            new_page.close()
        except:
            pass
        
    except Exception as e:
        print(f"      ❌ Erreur: {str(e)[:50]}")
    
    return results


def main():
    """Scrape VoucherCodes UK depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")
    
    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("UK", "vouchercodes")
    print(f"📍 VoucherCodes: {len(competitor_data)} URLs uniques")
    
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
                codes = scrape_vouchercodes_all(page, context, url)
                print(f"   ✅ {len(codes)} codes trouvés")
                
                for code_info in codes:
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "UK",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "vouchercodes",
                        "Competitor_URL": url,
                        "Code": code_info["code"],
                        "Title": code_info["title"]
                    })
            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:50]}")
            
            print(f"   📝 Total: {len(all_results)} codes")
        
        browser.close()
    
    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="VoucherCodes UK")
        
        print(f"\n{'='*60}")
        print(f"✅ VOUCHERCODES UK TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")


if __name__ == "__main__":
    main()
