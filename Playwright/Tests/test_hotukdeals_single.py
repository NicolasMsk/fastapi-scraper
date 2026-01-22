"""
Test HotUKDeals sur une seule URL pour debug
"""

from playwright.sync_api import sync_playwright


def test_hotukdeals_single(url):
    """Test scraping sur une seule URL HotUKDeals"""
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False pour voir ce qui se passe
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            print(f"[HotUKDeals] Accès à l'URL: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)  # Réduit de 3000 à 1500
            
            # Fermer popups cookies
            try:
                page.click("button:has-text('Accept'), button:has-text('Agree'), #onetrust-accept-btn-handler", timeout=2000)
                page.wait_for_timeout(500)  # Réduit de 1000 à 500
            except:
                pass
            
            # ===================================================================
            # IMPORTANT: On cible UNIQUEMENT les codes du marchand principal
            # On EXCLUT:
            # - div._1hla7140 = "Active vouchers for retailers similar to..."
            # - div.jkau50 = "Great discounts that have expired..."
            # 
            # Les codes valides du marchand sont dans des cartes avec:
            # - h3 (pas div) pour le titre = offre non expirée
            # - PAS dans les conteneurs _1hla7140 ou jkau50
            # ===================================================================
            
            # XPath pour trouver les boutons "See Code" VALIDES:
            # 1. Dans une carte avec h3 (pas expirée)
            # 2. PAS dans le conteneur "similar vouchers" (_1hla7140)
            # 3. PAS dans le conteneur "expired" (jkau50)
            xpath_valid_codes = """
                //div[@data-testid='vouchers-ui-voucher-card-description'][.//h3]
                    [not(ancestor::div[contains(@class, '_1hla7140')])]
                    [not(ancestor::div[contains(@class, 'jkau5')])]
                //div[@role='button' and contains(@title, 'See Code')]
            """.replace('\n', '').replace('    ', '')
            
            see_code_buttons = page.locator(f"xpath={xpath_valid_codes}")
            total_count = see_code_buttons.count()
            
            print(f"[HotUKDeals] {total_count} boutons 'See Code' valides trouvés (hors similaires et expirés)")
            
            if total_count == 0:
                print("[HotUKDeals] Aucun code disponible pour ce marchand")
                browser.close()
                return results
            
            processed_codes = set()
            
            # === ÉTAPE 1: Cliquer sur le premier bouton pour ouvrir le nouvel onglet ===
            first_btn = see_code_buttons.first
            first_btn.scroll_into_view_if_needed()
            page.wait_for_timeout(300)  # Réduit de 500 à 300
            
            # Récupérer le titre du premier code
            try:
                container = first_btn.locator("xpath=ancestor::div[@data-testid='vouchers-ui-voucher-card-description']")
                first_title = container.locator("h3").first.inner_text().strip()
            except:
                first_title = "Offre 1"
            
            print(f"[HotUKDeals] Clic sur le premier code: {first_title[:50]}...")
            
            # Cliquer avec JavaScript
            pages_before = len(context.pages)
            page.evaluate("(el) => el.click()", first_btn.element_handle())
            page.wait_for_timeout(1000)  # Réduit de 2000 à 1000
            
            if len(context.pages) <= pages_before:
                print("[HotUKDeals] Aucun nouvel onglet ouvert")
                browser.close()
                return results
            
            new_page = context.pages[-1]
            print("[HotUKDeals] Switché vers le nouvel onglet")
            new_page.wait_for_timeout(1000)  # Réduit de 2000 à 1000
            
            # === ÉTAPE 2: Boucle sur le nouvel onglet ===
            max_iterations = 20
            
            for iteration in range(max_iterations):
                print(f"\n[HotUKDeals] --- Itération {iteration + 1} ---")
                
                new_page.wait_for_timeout(1000)  # Réduit de 2000 à 1000
                
                # 1. Récupérer le code affiché dans la popup (h4 avec classe b8qpi7*)
                code = None
                try:
                    # Le code est dans h4.b8qpi79 (classe commence par b8qpi)
                    code_elem = new_page.locator("h4[class*='b8qpi']").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                        print(f"[HotUKDeals] Code trouvé via h4.b8qpi: {code}")
                except:
                    pass
                
                if not code:
                    # Fallback: tous les h4
                    try:
                        h4_elems = new_page.locator("h4")
                        for i in range(h4_elems.count()):
                            text = h4_elems.nth(i).inner_text().strip()
                            print(f"[HotUKDeals]   h4[{i}]: '{text}'")
                            if text and 3 <= len(text) <= 30 and text not in processed_codes:
                                code = text
                                print(f"[HotUKDeals] Code sélectionné: {code}")
                                break
                    except:
                        pass
                
                # 2. Récupérer le titre depuis la POPUP (pas la page principale)
                # Dans la popup, le titre est dans un h4 avec classe az57m40 az57m46 mais SANS b8qpi
                current_title = None
                try:
                    # Méthode 1: h4 avec az57m mais pas b8qpi (titre dans la popup)
                    title_elems = new_page.locator("xpath=//h4[contains(@class, 'az57m') and not(contains(@class, 'b8qpi'))]")
                    if title_elems.count() > 0:
                        current_title = title_elems.first.inner_text().strip()
                        print(f"[HotUKDeals] Titre popup (h4.az57m): {current_title[:60]}...")
                except:
                    pass
                
                # Méthode 2: Si pas trouvé, chercher dans la description de la carte
                if not current_title:
                    try:
                        # Le titre peut aussi être dans un h3 de la carte voucher
                        h3_elems = new_page.locator("div[data-testid='vouchers-ui-voucher-card-description'] h3")
                        if h3_elems.count() > 0:
                            # On prend le h3 correspondant à l'index actuel
                            idx = len(results)
                            if idx < h3_elems.count():
                                current_title = h3_elems.nth(idx).inner_text().strip()
                                print(f"[HotUKDeals] Titre carte (h3): {current_title[:60]}...")
                    except:
                        pass
                
                if not current_title:
                    try:
                        h3_elem = new_page.locator("h3").first
                        if h3_elem.count() > 0:
                            current_title = h3_elem.inner_text().strip()
                    except:
                        current_title = f"Offre {iteration + 1}"
                
                if code and code not in processed_codes:
                    processed_codes.add(code)
                    results.append({
                        "code": code,
                        "title": current_title or f"Offre {len(results)+1}"
                    })
                    print(f"[HotUKDeals] ✅ Code: {code} -> {current_title[:40] if current_title else 'N/A'}...")
                else:
                    print(f"[HotUKDeals] ⚠️ Code non trouvé ou doublon: {code}")
                
                # 3. Fermer la popup (span avec data-testid='CloseIcon')
                try:
                    close_icon = new_page.locator("span[data-testid='CloseIcon'], svg[data-testid='CloseIcon'], button[aria-label*='close' i]").first
                    if close_icon.count() > 0:
                        close_icon.click(timeout=2000)
                        print("[HotUKDeals] Popup fermée")
                        new_page.wait_for_timeout(500)  # Réduit de 1000 à 500
                except Exception as e:
                    print(f"[HotUKDeals] ⚠️ Erreur fermeture popup: {str(e)[:30]}")
                
                # 4. Chercher le prochain bouton "See Code" SUR CE NOUVEL ONGLET
                # Avec les MÊMES exclusions (similaires + expirés)
                new_page.wait_for_timeout(300)  # Réduit de 500 à 300
                
                xpath_next_codes = """
                    //div[@data-testid='vouchers-ui-voucher-card-description'][.//h3]
                        [not(ancestor::div[contains(@class, '_1hla7140')])]
                        [not(ancestor::div[contains(@class, 'jkau5')])]
                    //div[@role='button' and contains(@title, 'See Code')]
                """.replace('\n', '').replace('    ', '')
                
                next_buttons = new_page.locator(f"xpath={xpath_next_codes}")
                next_count = next_buttons.count()
                
                current_index = len(results)
                print(f"[HotUKDeals] Boutons restants: {next_count}, index actuel: {current_index}")
                
                if current_index >= next_count:
                    print("[HotUKDeals] Plus de boutons 'See Code' disponibles")
                    break
                
                # 5. Cliquer sur le bouton suivant
                next_btn = next_buttons.nth(current_index)
                try:
                    next_btn.scroll_into_view_if_needed()
                    new_page.wait_for_timeout(200)  # Réduit de 300 à 200
                    
                    pages_before = len(context.pages)
                    new_page.evaluate("(el) => el.click()", next_btn.element_handle())
                    new_page.wait_for_timeout(1000)  # Réduit de 2000 à 1000
                    
                    # Si un nouvel onglet s'est ouvert, switcher
                    if len(context.pages) > pages_before:
                        new_page = context.pages[-1]
                        print(f"[HotUKDeals] Switché vers nouvel onglet pour code {current_index + 1}")
                        new_page.wait_for_timeout(500)  # Réduit de 1000 à 500
                    
                except Exception as e:
                    print(f"[HotUKDeals] Erreur clic suivant: {str(e)[:30]}")
                    break
            
            # Fermer les onglets
            for p in context.pages[1:]:
                try:
                    p.close()
                except:
                    pass
            
        except Exception as e:
            print(f"[HotUKDeals] ❌ Erreur générale: {str(e)}")
        
        browser.close()
    
    return results


if __name__ == "__main__":
    # Test avec ASOS qui devrait avoir des codes valides
    test_url = "https://www.hotukdeals.com/vouchers/asos.com"
    
    print("=" * 60)
    print("TEST SCRAPER HOTUKDEALS - SINGLE URL")
    print(f"URL: {test_url}")
    print("=" * 60)
    
    results = test_hotukdeals_single(test_url)
    
    print("\n" + "=" * 60)
    print(f"RÉSULTATS: {len(results)} codes trouvés")
    print("=" * 60)
    for i, r in enumerate(results):
        print(f"  [{i+1}] Code: {r['code']} -> {r['title'][:50]}...")
    print("=" * 60)
