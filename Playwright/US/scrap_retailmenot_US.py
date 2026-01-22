"""
Script Playwright pour scraper TOUS les codes RetailMeNot (US)
- Utilise la même logique que FastAPI/scraper_retailmenot.py
- Clique sur la première offre puis récupère tous les codes via JavaScript
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_retailmenot_all(page, context, url):
    """
    Scrape TOUS les codes d'une page RetailMeNot avec Playwright.
    Même logique que le scraper FastAPI.
    """
    results = []
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        
        # Fermer cookie banner
        try:
            page.click("button:has-text('Accept'), button:has-text('Consent')", timeout=1000)
        except:
            pass
        
        # Trouver les offres
        offer_links = page.locator("a[data-component-class='offer_strip']")
        count = offer_links.count()
        
        if count == 0:
            return results
        
        # Cliquer sur la première offre pour révéler les codes
        first_offer = offer_links.first
        first_offer.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        
        # Gérer le nouvel onglet potentiel
        with context.expect_page() as new_page_info:
            first_offer.click()
        
        try:
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)
            
            # Vérifier si c'est une page RetailMeNot
            if "retailmenot" in new_page.url:
                work_page = new_page
            else:
                new_page.close()
                work_page = page
        except:
            work_page = page
        
        page.wait_for_timeout(2000)
        
        # Scroll de la page pour charger tous les codes
        last_height = work_page.evaluate("document.body.scrollHeight")
        while True:
            work_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            work_page.wait_for_timeout(1000)
            new_height = work_page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        work_page.evaluate("window.scrollTo(0, 0)")
        work_page.wait_for_timeout(1000)
        
        # Récupérer tous les codes via JavaScript (même script que FastAPI)
        codes_data = work_page.evaluate("""
            () => {
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
            }
        """)
        
        # Filtrer les faux codes et doublons (uniquement sur le code)
        processed_codes = set()
        
        for item in codes_data:
            code = item['code']
            title = item['title']
            
            # Ignorer les faux codes
            if code.lower() in ['get deal', 'see deal', 'show deal', 'view deal']:
                continue
            
            # Vérifier uniquement si le code est un doublon
            if code in processed_codes:
                continue
            
            # N'ajouter que si code ET titre sont présents
            if code and title:
                processed_codes.add(code)
                results.append({
                    "code": code,
                    "title": title
                })
        
        # Fermer le nouvel onglet si on en a ouvert un
        if work_page != page:
            try:
                work_page.close()
            except:
                pass
        
    except Exception as e:
        print(f"      ❌ Erreur: {str(e)[:50]}")
    
    return results


def main():
    """Scrape RetailMeNot US depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")
    
    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("US", "retailmenot")
    print(f"📍 RetailMeNot: {len(competitor_data)} URLs uniques")
    
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
                codes = scrape_retailmenot_all(page, context, url)
                print(f"   ✅ {len(codes)} codes trouvés")
                
                for code_info in codes:
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "US",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "retailmenot",
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
        append_to_gsheet(all_results, source_name="RetailMeNot US")
        
        print(f"\n{'='*60}")
        print(f"✅ RETAILMENOT US TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")


if __name__ == "__main__":
    main()
