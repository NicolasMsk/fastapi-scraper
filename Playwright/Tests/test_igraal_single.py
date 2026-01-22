"""
Test script pour iGraal FR - Tester une seule URL
Basé sur la logique RetailMeNot/Ma-Reduc : cliquer sur un code pour révéler tous les autres,
puis récupérer via JavaScript
"""

from playwright.sync_api import sync_playwright


def scrape_igraal_test(page, context, url):
    """Test de scraping iGraal - même logique que RetailMeNot"""
    results = []
    
    try:
        print(f"[iGraal] Accès à l'URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Fermer cookie banner si présent
        try:
            page.click("button:has-text('Accepter'), button:has-text('Accept'), #onetrust-accept-btn-handler", timeout=3000)
            page.wait_for_timeout(1000)
        except:
            pass
        
        # Trouver tous les boutons "Afficher le code"
        # Les codes sont dans des cartes avec classe horizontalbasecard et ont un bouton "Afficher le code"
        code_buttons = page.locator("button:has-text('Afficher le code')")
        count = code_buttons.count()
        
        print(f"[iGraal] {count} boutons 'Afficher le code' trouvés")
        
        if count == 0:
            return results
        
        # Cliquer sur le premier bouton pour révéler les codes
        first_btn = code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        
        print("[iGraal] Clic sur le premier bouton 'Afficher le code'...")
        
        # Gérer le nouvel onglet potentiel
        with context.expect_page() as new_page_info:
            first_btn.click()
        
        try:
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)
            
            # Vérifier si c'est une page igraal
            if "igraal" in new_page.url:
                work_page = new_page
                print(f"[iGraal] Travail sur le nouvel onglet: {new_page.url[:60]}...")
            else:
                new_page.close()
                work_page = page
                print("[iGraal] Travail sur la page principale")
        except:
            work_page = page
            print("[iGraal] Travail sur la page principale (pas de nouvel onglet)")
        
        page.wait_for_timeout(2000)
        
        # Fermer la popup si présente (cliquer en dehors ou sur X)
        try:
            # Essayer de fermer avec Escape
            work_page.keyboard.press("Escape")
            work_page.wait_for_timeout(1500)
            print("[iGraal] Popup fermée via Escape")
        except Exception as e:
            print(f"[iGraal] ⚠️ Erreur fermeture popup: {str(e)[:40]}")
        
        # Scroll de la page pour charger tous les codes
        print("[iGraal] Scroll de la page...")
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
        # Les codes sont affichés dans les boutons après le clic (au lieu de "Afficher le code")
        # Le titre est dans h3._1t96igp3
        print("[iGraal] Récupération des codes via JavaScript...")
        codes_data = work_page.evaluate("""
            () => {
                var results = [];
                // Sélectionner les cartes de codes VALIDES uniquement (stt-vld = valide)
                // EXCLURE les expirés (stt-exp)
                var cards = document.querySelectorAll('div.horizontalbasecard.stt-vld:not(.stt-exp)');
                
                cards.forEach(function(card) {
                    // Le code est dans le bouton (après révélation, le texte change de "Afficher le code" au code réel)
                    var codeBtn = card.querySelector('button._1aujn430');
                    var code = null;
                    
                    if (codeBtn) {
                        var btnText = codeBtn.textContent.trim();
                        // Si le texte n'est pas "Afficher le code", c'est le code
                        if (btnText && btnText !== 'Afficher le code' && btnText !== 'Copier' && btnText.length >= 3) {
                            code = btnText;
                        }
                    }
                    
                    // Le titre est dans h3._1t96igp3 ou h3 avec id offerbasecard-title
                    var titleH3 = card.querySelector('h3._1t96igp3, h3#offerbasecard-title');
                    var title = titleH3 ? titleH3.textContent.trim() : null;
                    
                    if (code && title) {
                        results.push({code: code, title: title});
                    }
                });
                
                return results;
            }
        """)
        
        print(f"[iGraal] {len(codes_data)} codes trouvés via JavaScript")
        
        # Filtrer les doublons (uniquement sur le code)
        processed_codes = set()
        
        # Fonction pour vérifier si c'est un vrai code promo (alphanumerique sans espaces)
        def is_real_code(code):
            if not code:
                return False
            # Un vrai code n'a pas d'espaces et est alphanumérique (lettres/chiffres)
            # Exclure les textes comme "Activer le cashback", "En profiter", "Acheter un bon"
            if ' ' in code:
                return False
            # Vérifier que c'est principalement alphanumérique
            return code.replace('-', '').replace('_', '').isalnum()
        
        for item in codes_data:
            code = item['code']
            title = item['title']
            
            # Vérifier si c'est un vrai code promo
            if not is_real_code(code):
                print(f"[iGraal] ⚠️ Ignoré (pas un code): {code}")
                continue
            
            if code in processed_codes:
                print(f"[iGraal] ⚠️ Doublon ignoré: {code}")
                continue
            
            if code and title:
                processed_codes.add(code)
                results.append({"code": code, "title": title})
                print(f"[iGraal] ✅ AJOUTÉ: {code} -> {title[:50]}...")
        
        # Fermer le nouvel onglet si on en a ouvert un
        if work_page != page:
            try:
                work_page.close()
            except:
                pass
        
    except Exception as e:
        print(f"[iGraal] Erreur: {str(e)}")
    
    return results


def main():
    # URL de test - Cdiscount sur iGraal
    test_url = "https://fr.igraal.com/codes-promo/cdiscount/code-promo"
    
    print("=" * 60)
    print("TEST IGRAAL FR - SINGLE URL")
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
        
        results = scrape_igraal_test(page, context, test_url)
        
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
