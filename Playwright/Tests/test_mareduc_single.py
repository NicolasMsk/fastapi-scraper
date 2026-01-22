"""
Test script pour Ma-Reduc FR - Tester une seule URL
Basé sur la logique RetailMeNot : cliquer sur un code pour révéler tous les autres,
puis récupérer via JavaScript
"""

from playwright.sync_api import sync_playwright


def scrape_mareduc_test(page, context, url):
    """Test de scraping Ma-Reduc - même logique que RetailMeNot"""
    results = []
    
    try:
        print(f"[Ma-Reduc] Accès à l'URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Fermer cookie banner si présent
        try:
            page.click("button:has-text('Accepter'), button:has-text('Accept'), #onetrust-accept-btn-handler", timeout=3000)
            page.wait_for_timeout(1000)
        except:
            pass
        
        # Trouver les boutons "Voir le code" UNIQUEMENT pour le marchand de la page
        # EXCLURE les offres d'autres marchands (competitor_outclick dans data-layer-push-on-click)
        # Les offres du bon marchand ont "offer_outclick", les autres ont "offer_competitor_outclick"
        code_buttons = page.locator("div.m-offer[data-offer-type='code']:not([data-layer-push-on-click*='competitor']) button.a-btnSlide")
        count = code_buttons.count()
        
        print(f"[Ma-Reduc] {count} boutons 'Voir le code' trouvés (marchand uniquement)")
        
        if count == 0:
            # Pas de codes pour ce marchand, retourner vide
            print("[Ma-Reduc] Aucun code trouvé pour ce marchand")
            return results
        
        # Cliquer sur le premier bouton pour révéler les codes
        first_btn = code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        
        print("[Ma-Reduc] Clic sur le premier bouton 'Voir le code'...")
        
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
                print(f"[Ma-Reduc] Travail sur le nouvel onglet: {new_page.url[:60]}...")
            else:
                new_page.close()
                work_page = page
                print("[Ma-Reduc] Travail sur la page principale")
        except:
            work_page = page
            print("[Ma-Reduc] Travail sur la page principale (pas de nouvel onglet)")
        
        page.wait_for_timeout(2000)
        
        # Fermer la popup si présente
        try:
            close_btn = work_page.locator("i.fa-xmark, button:has(i.fa-xmark), .o-dialog__close").first
            if close_btn.count() > 0:
                close_btn.click()
                work_page.wait_for_timeout(1500)
                print("[Ma-Reduc] Popup fermée via X")
            else:
                work_page.keyboard.press("Escape")
                work_page.wait_for_timeout(1500)
                print("[Ma-Reduc] Popup fermée via Escape")
        except Exception as e:
            print(f"[Ma-Reduc] ⚠️ Erreur fermeture popup: {str(e)[:40]}")
        
        # Scroll de la page pour charger tous les codes
        print("[Ma-Reduc] Scroll de la page...")
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
        print("[Ma-Reduc] Récupération des codes via JavaScript...")
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
        
        print(f"[Ma-Reduc] {len(codes_data)} codes trouvés via JavaScript")
        
        # Filtrer les doublons (uniquement sur le code)
        processed_codes = set()
        
        for item in codes_data:
            code = item['code']
            title = item['title']
            
            if code in processed_codes:
                print(f"[Ma-Reduc] ⚠️ Doublon ignoré: {code}")
                continue
            
            if code and title:
                processed_codes.add(code)
                results.append({"code": code, "title": title})
                print(f"[Ma-Reduc] ✅ AJOUTÉ: {code} -> {title[:50]}...")
        
        # Fermer le nouvel onglet si on en a ouvert un
        if work_page != page:
            try:
                work_page.close()
            except:
                pass
        
    except Exception as e:
        print(f"[Ma-Reduc] Erreur: {str(e)}")
    
    return results


def main():
    # URL de test - Ninja Kitchen sur Ma-Reduc
    test_url = "https://www.ma-reduc.com/reductions-pour-Meetic.php"
    
    print("=" * 60)
    print("TEST MA-REDUC FR - SINGLE URL")
    print("=" * 60)
    print(f"URL: {test_url}")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False pour voir
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        results = scrape_mareduc_test(page, context, test_url)
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("RÉSULTATS FINAUX")
    print("=" * 60)
    
    if results:
        for i, r in enumerate(results, 1):
            print(f"{i}. Code: {r['code']}")
            print(f"   Titre: {r['title']}")
            print()
    else:
        print("Aucun code trouvé")
    
    print(f"Total: {len(results)} codes uniques")


if __name__ == "__main__":
    main()
