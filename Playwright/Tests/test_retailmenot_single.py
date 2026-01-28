"""
Test script pour RetailMeNot US - Tester une seule URL
"""

from playwright.sync_api import sync_playwright


def scrape_retailmenot_test(page, context, url):
    """Test de scraping RetailMeNot"""
    results = []
    affiliate_link = None

    try:
        print(f"[RetailMeNot] Accès à l'URL: {url}")
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
        
        print(f"[RetailMeNot] {count} offres trouvées")
        
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

            # CAPTURE DU LIEN AFFILIÉ - La page ORIGINALE se redirige vers le marchand
            try:
                for _ in range(10):
                    current_url = page.url
                    if "retailmenot" not in current_url.lower():
                        affiliate_link = current_url
                        print(f"[RetailMeNot] Lien affilié capturé: {affiliate_link[:60]}...")
                        break
                    page.wait_for_timeout(500)
            except Exception as e:
                print(f"[RetailMeNot] ⚠️ Erreur capture affiliate: {str(e)[:40]}")

            if "retailmenot" in new_page.url:
                work_page = new_page
                print("[RetailMeNot] Travail sur le nouvel onglet")
            else:
                new_page.close()
                work_page = page
                print("[RetailMeNot] Travail sur la page principale")
        except:
            work_page = page
        
        page.wait_for_timeout(2000)
        
        # Scroll pour charger tous les codes
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
        
        # Récupérer tous les codes via JavaScript
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
        
        print(f"[RetailMeNot] {len(codes_data)} codes bruts trouvés via JS")
        
        # Filtrer les faux codes et doublons (uniquement sur le code)
        processed_codes = set()
        
        for item in codes_data:
            code = item['code']
            title = item['title']
            
            # Ignorer les faux codes
            if code.lower() in ['get deal', 'see deal', 'show deal', 'view deal']:
                print(f"[RetailMeNot] ⚠️ Ignoré (faux code): {code}")
                continue
            
            # Vérifier uniquement si le code est un doublon
            if code in processed_codes:
                print(f"[RetailMeNot] ⚠️ Doublon ignoré: {code}")
                continue
            
            # N'ajouter que si code ET titre sont présents
            if code and title:
                processed_codes.add(code)
                results.append({"code": code, "title": title, "affiliate_link": affiliate_link})
                print(f"[RetailMeNot] ✅ AJOUTÉ: {code} -> {title[:50]}...")
        
        # Fermer le nouvel onglet si nécessaire
        if work_page != page:
            try:
                work_page.close()
            except:
                pass
        
    except Exception as e:
        print(f"[RetailMeNot] Erreur: {str(e)}")
    
    return results


def main():
    # URL de test - Target sur RetailMeNot
    test_url = "https://www.retailmenot.com/view/target.com"
    
    print("=" * 60)
    print("TEST RETAILMENOT US - SINGLE URL")
    print("=" * 60)
    print(f"URL: {test_url}")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        results = scrape_retailmenot_test(page, context, test_url)
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("RÉSULTATS")
    print("=" * 60)
    
    if results:
        print(f"Affiliate Link: {results[0].get('affiliate_link', 'N/A')}\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. Code: {r['code']}")
            print(f"   Titre: {r['title']}")
            print()
    else:
        print("Aucun code trouvé")

    print(f"Total: {len(results)} codes uniques (sans doublons)")


if __name__ == "__main__":
    main()
