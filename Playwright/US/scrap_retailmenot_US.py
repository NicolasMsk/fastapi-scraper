"""
Script Playwright pour scraper TOUS les codes RetailMeNot (US)
- Utilise la même logique que FastAPI/scraper_retailmenot.py
- Clique sur la première offre puis récupère tous les codes via JavaScript
"""

import os
import re
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

        # Scroll de la page listing pour charger tous les codes
        last_height = page.evaluate("document.body.scrollHeight")
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)

        # Cliquer tous les "See Details" sur la page listing (Alpine.js)
        try:
            for _ in range(50):
                see_details = page.locator("span:text-is('See Details')")
                if see_details.count() == 0:
                    break
                try:
                    see_details.first.click(timeout=1000)
                    page.wait_for_timeout(150)
                except:
                    break
            page.wait_for_timeout(300)
        except:
            pass

        # Pré-extraire title→terms depuis la page listing AVANT de cliquer
        title_to_terms = {}
        title_terms_pairs = page.evaluate("""
            () => {
                var pairs = [];
                var offers = document.querySelectorAll('a[data-component-class="offer_strip"]');
                offers.forEach(function(offer) {
                    var titleH3 = offer.querySelector('h3');
                    var title = titleH3 ? titleH3.textContent.trim() : '';
                    var parentDiv = offer.parentElement;
                    var termsDiv = parentDiv ? parentDiv.querySelector('details div.prose') : null;
                    var terms = termsDiv ? termsDiv.textContent.trim() : '';
                    if (title) {
                        pairs.push([title, terms]);
                    }
                });
                return pairs;
            }
        """)
        for pair in title_terms_pairs:
            if pair[0]:
                title_to_terms[pair[0]] = pair[1]

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

        # Récupérer tous les codes + titres via JavaScript
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
        
        # Regex pour trouver des dates dans le texte des terms
        months_pattern = r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'

        for item in codes_data:
            code = item['code']
            title = item['title']
            terms = title_to_terms.get(title, '')

            # Ignorer les faux codes
            if code.lower() in ['get deal', 'see deal', 'show deal', 'view deal']:
                continue

            # Vérifier uniquement si le code est un doublon
            if code in processed_codes:
                continue

            # Extraire expiration_date depuis le texte des terms
            expiration_date = ""
            if terms:
                dates = []
                # MM/DD/YYYY ou DD/MM/YYYY
                dates.extend(re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}', terms))
                # Month DDth, YYYY
                dates.extend(re.findall(rf'{months_pattern}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s*\d{{4}}', terms, re.IGNORECASE))
                # DD Month YYYY
                dates.extend(re.findall(rf'\d{{1,2}}\s+{months_pattern},?\s+\d{{4}}', terms, re.IGNORECASE))
                if dates:
                    expiration_date = dates[-1]  # Dernière date = date de fin

            # N'ajouter que si code ET titre sont présents
            if code and title:
                processed_codes.add(code)
                results.append({
                    "code": code,
                    "title": title,
                    "terms": terms,
                    "expiration_date": expiration_date
                })
                print(f"[RetailMeNot] ✅ Code: {code} | {title[:50]}...")
                print(f"[RetailMeNot]    📅 Expiry: {expiration_date if expiration_date else 'N/A'} | 📋 Terms: {'Yes' if terms else 'No'}")
        
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
                        "Title": code_info["title"],
                        "terms": code_info.get("terms", ""),
                        "expiration_date": code_info.get("expiration_date", "")
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
