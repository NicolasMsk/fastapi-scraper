"""
Test script pour Sparwelt DE - Tester une seule URL
LOGIQUE (même que MyDealz):
1. Page principale → clic sur premier "Gutschein anzeigen" → ouvre nouvel onglet
2. Switch vers nouvel onglet → récupérer code+titre dans popup
3. Fermer popup avec X → on reste sur nouvel onglet (page Sparwelt)
4. Sur ce nouvel onglet, cliquer sur "Gutschein anzeigen" index+1 → popup → répéter
"""

from playwright.sync_api import sync_playwright


def test_sparwelt_single(url):
    """Test scraping sur une seule URL Sparwelt"""
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            print(f"[Sparwelt] Accès à l'URL: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Fermer popups cookies
            try:
                page.click("button:has-text('Akzeptieren'), button:has-text('Accept'), #onetrust-accept-btn-handler", timeout=3000)
                page.wait_for_timeout(1000)
            except:
                pass
            
            # Sélecteur: boutons "Gutschein anzeigen" (pas "Zum Angebot" ni "Cashback")
            # EXCLURE les codes expirés qui ont la classe "filter grayscale"
            code_selector = "div[data-voucher-id]:not(.grayscale) button:has-text('Gutschein anzeigen')"
            
            see_code_buttons = page.locator(code_selector)
            total_count = see_code_buttons.count()
            
            print(f"[Sparwelt] {total_count} boutons 'Gutschein anzeigen' trouvés")
            
            if total_count == 0:
                print("[Sparwelt] Aucun code disponible")
                browser.close()
                return results
            
            processed_codes = set()
            
            # === ÉTAPE 1: Cliquer sur le premier bouton → ouvre nouvel onglet ===
            first_btn = see_code_buttons.first
            first_btn.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            
            print(f"[Sparwelt] Clic sur le premier bouton...")
            pages_before = len(context.pages)
            page.evaluate("(el) => el.click()", first_btn.element_handle())
            page.wait_for_timeout(2000)
            
            # Vérifier si nouvel onglet ouvert
            if len(context.pages) > pages_before:
                work_page = context.pages[-1]
                print(f"[Sparwelt] Nouvel onglet ouvert, switch dessus")
            else:
                work_page = page
                print(f"[Sparwelt] Pas de nouvel onglet, on reste sur la page")
            
            # === ÉTAPE 2: Boucle sur work_page ===
            max_iterations = 20
            
            for iteration in range(max_iterations):
                print(f"\n[Sparwelt] --- Itération {iteration + 1} ---")
                
                work_page.wait_for_timeout(2000)
                
                # 1. Récupérer le code dans la popup
                # Le code est dans: div.border.font-bold span (dans le conteneur p-4)
                code = None
                try:
                    code_elem = work_page.locator("div.p-4 div.border.font-bold span").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                        # Vérifier que c'est un vrai code (pas vide, pas trop long avec espaces)
                        if not code or ' ' in code or len(code) > 30:
                            print(f"[Sparwelt] ⚠️ Pas un vrai code: {code}")
                            code = None
                        else:
                            print(f"[Sparwelt] Code trouvé: {code}")
                except Exception as e:
                    print(f"[Sparwelt] ⚠️ Erreur code: {str(e)[:40]}")
                
                # 2. Récupérer le titre dans la popup
                # Le titre est dans: div.p-4 div.text-xl (le titre de l'offre, pas la newsletter)
                current_title = None
                try:
                    title_elem = work_page.locator("div.p-4 div.text-xl").first
                    if title_elem.count() > 0:
                        current_title = title_elem.inner_text().strip()
                        print(f"[Sparwelt] Titre: {current_title[:60]}...")
                except:
                    pass
                
                if current_title is None:
                    current_title = f"Offre {iteration + 1}"
                
                if code and code not in processed_codes:
                    processed_codes.add(code)
                    results.append({
                        "code": code,
                        "title": current_title
                    })
                    print(f"[Sparwelt] ✅ Ajouté: {code}")
                
                # 3. Fermer la popup avec le X (SVG)
                # Le X est: svg.fill-gray-400.absolute.top-4.right-4
                try:
                    close_btn = work_page.locator("svg.absolute.top-4.right-4, svg.fill-gray-400.absolute").first
                    if close_btn.count() > 0:
                        close_btn.click(timeout=3000)
                        print("[Sparwelt] Popup fermée")
                        work_page.wait_for_timeout(1500)
                except Exception as e:
                    print(f"[Sparwelt] ⚠️ Erreur fermeture: {str(e)[:30]}")
                    # Essayer Escape comme alternative
                    try:
                        work_page.keyboard.press("Escape")
                        work_page.wait_for_timeout(1000)
                    except:
                        pass
                
                # Scroll vers le haut pour s'assurer que les boutons sont visibles
                work_page.evaluate("window.scrollTo(0, 0)")
                work_page.wait_for_timeout(1000)
                
                # 4. Chercher le prochain bouton sur work_page (même onglet)
                next_buttons = work_page.locator(code_selector)
                next_count = next_buttons.count()
                
                # Index = iteration + 1 (on a déjà traité iteration boutons)
                next_index = iteration + 1
                print(f"[Sparwelt] Boutons: {next_count}, prochain index: {next_index}")
                
                if next_index >= next_count:
                    print("[Sparwelt] Plus de boutons disponibles")
                    break
                
                # 5. Cliquer sur le prochain bouton → ouvre nouvel onglet → switch
                next_btn = next_buttons.nth(next_index)
                
                try:
                    next_btn.scroll_into_view_if_needed(timeout=5000)
                    work_page.wait_for_timeout(500)
                except:
                    # Si scroll échoue, essayer de scroller manuellement
                    work_page.evaluate("window.scrollBy(0, 300)")
                    work_page.wait_for_timeout(500)
                
                print(f"[Sparwelt] Clic sur bouton {next_index + 1}...")
                pages_before = len(context.pages)
                
                try:
                    work_page.evaluate("(el) => el.click()", next_btn.element_handle())
                except:
                    # Alternative: forcer le clic
                    next_btn.click(force=True, timeout=5000)
                
                work_page.wait_for_timeout(2000)
                
                # Switch vers le nouvel onglet
                if len(context.pages) > pages_before:
                    work_page = context.pages[-1]
                    print(f"[Sparwelt] Switch vers nouvel onglet")
            
        except Exception as e:
            print(f"[Sparwelt] Erreur: {str(e)}")
            import traceback
            traceback.print_exc()
        
        browser.close()
    
    return results


def main():
    # URL de test - Congstar sur Sparwelt
    test_url = "https://www.sparwelt.de/gutscheine/congstar"
    
    print("=" * 60)
    print("TEST SPARWELT DE - SINGLE URL")
    print("=" * 60)
    print(f"URL: {test_url}")
    print("=" * 60)
    
    results = test_sparwelt_single(test_url)
    
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
