"""
Script Playwright pour scraper TOUS les codes Ma-Reduc (FR)
- Basé sur la logique RetailMeNot
- Clique sur le premier code pour révéler tous les autres
- Récupère tous les codes et titres de la page
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_mareduc_all(page, context, url):
    """
    Scrape TOUS les codes d'une page Ma-Reduc avec Playwright.
    Logique RetailMeNot : Cliquer sur un code pour révéler tous les autres,
    puis récupérer via JavaScript.
    """
    results = []
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Fermer cookie banner si présent
        try:
            page.click("button:has-text('Accepter'), button:has-text('Accept'), #onetrust-accept-btn-handler", timeout=2000)
            page.wait_for_timeout(500)
        except:
            pass
        
        # Trouver les boutons "Voir le code" UNIQUEMENT pour le marchand de la page
        # EXCLURE les offres d'autres marchands (competitor_outclick dans data-layer-push-on-click)
        # Les offres du bon marchand ont "offer_outclick", les autres ont "offer_competitor_outclick"
        code_buttons = page.locator("div.m-offer[data-offer-type='code']:not([data-layer-push-on-click*='competitor']) button.a-btnSlide")
        count = code_buttons.count()
        
        if count == 0:
            # Pas de codes pour ce marchand, retourner vide
            return results
        
        # Cliquer sur le premier bouton pour révéler les codes
        first_btn = code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        
        # Gérer le nouvel onglet potentiel
        with context.expect_page() as new_page_info:
            first_btn.click()
        
        try:
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)
            
            # Vérifier si c'est une page ma-reduc
            if "ma-reduc" in new_page.url:
                work_page = new_page
            else:
                new_page.close()
                work_page = page
        except:
            work_page = page
        
        page.wait_for_timeout(2000)
        
        # Fermer la popup si présente
        try:
            close_btn = work_page.locator("i.fa-xmark, button:has(i.fa-xmark), .o-dialog__close").first
            if close_btn.count() > 0:
                close_btn.click()
                work_page.wait_for_timeout(1500)
            else:
                work_page.keyboard.press("Escape")
                work_page.wait_for_timeout(1500)
        except:
            pass
        
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
        
        # Récupérer tous les codes via JavaScript (même logique que RetailMeNot)
        # IMPORTANT: Exclure les codes expirés (classe -disabled)
        # IMPORTANT: Exclure les offres d'autres marchands (section similar-offers)
        codes_data = work_page.evaluate("""
            () => {
                var results = [];
                // Sélectionner uniquement les offres NON expirées (sans classe -disabled)
                var offers = document.querySelectorAll('div.m-offer[data-offer-type="code"]:not(.-disabled)');
                
                offers.forEach(function(offer) {
                    // EXCLURE les offres d'autres marchands (section similar-offers)
                    // Ces offres ont un lien .m-offer__footer vers une autre page marchand
                    var footerLink = offer.querySelector('a.m-offer__footer');
                    if (footerLink) {
                        // Si le footer contient "Plus d'offres" c'est une offre d'un autre marchand
                        return;
                    }
                    
                    // EXCLURE aussi les offres dans les conteneurs "similar-offers" ou "competitors"
                    var parent = offer.closest('[class*="similar"], [class*="competitor"], [data-redirections*="similar"]');
                    if (parent) {
                        return;
                    }
                    
                    // Vérifier aussi via data-layer-push-on-click s'il s'agit d'un "competitor"
                    var dataLayer = offer.getAttribute('data-layer-push-on-click');
                    if (dataLayer && dataLayer.includes('competitor')) {
                        return;
                    }
                    
                    // Le code est dans input.a-revealedCode__inputCode
                    var codeInput = offer.querySelector('input.a-revealedCode__inputCode');
                    var code = codeInput ? codeInput.value : null;
                    
                    // Le titre est dans h2.m-offer__title
                    var titleH2 = offer.querySelector('h2.m-offer__title');
                    var title = titleH2 ? titleH2.textContent.trim() : null;
                    
                    if (code && title && code.length >= 3) {
                        results.push({code: code, title: title});
                    }
                });
                
                return results;
            }
        """)
        
        # Filtrer les doublons (uniquement sur le code)
        processed_codes = set()
        
        for item in codes_data:
            code = item['code']
            title = item['title']
            
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
    """Scrape Ma-Reduc FR depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")
    
    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("FR", "mareduc")
    print(f"📍 Ma-Reduc: {len(competitor_data)} URLs uniques")
    
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
                codes = scrape_mareduc_all(page, context, url)
                print(f"   ✅ {len(codes)} codes trouvés")
                
                for code_info in codes:
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "FR",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "mareduc",
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
        append_to_gsheet(all_results, source_name="Ma-Reduc FR")
        
        print(f"\n{'='*60}")
        print(f"✅ MA-REDUC FR TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")


if __name__ == "__main__":
    main()
