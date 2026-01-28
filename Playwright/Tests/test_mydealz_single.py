"""
Test script pour MyDealz DE - Tester une seule URL
LOGIQUE:
1. Page principale → clic sur premier "Code anzeigen" → ouvre nouvel onglet
2. Switch vers nouvel onglet → récupérer code+titre dans popup
3. Fermer popup avec CloseIcon → on reste sur nouvel onglet (page MyDealz)
4. Sur ce nouvel onglet, cliquer sur "Code anzeigen" index+1 → popup → répéter
"""

from playwright.sync_api import sync_playwright


def test_mydealz_single(url):
    """Test scraping sur une seule URL MyDealz"""
    results = []
    affiliate_link = None
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            print(f"[MyDealz] Accès à l'URL: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Fermer popups cookies
            try:
                page.click("button:has-text('Akzeptieren'), button:has-text('Accept'), #onetrust-accept-btn-handler", timeout=3000)
                page.wait_for_timeout(1000)
            except:
                pass
            
            # Sélecteur simple : uniquement "Code anzeigen" dans active-vouchers-widget
            code_selector = "div[data-testid='active-vouchers-widget'] div[title='Code anzeigen']"
            
            see_code_buttons = page.locator(code_selector)
            total_count = see_code_buttons.count()
            
            print(f"[MyDealz] {total_count} boutons 'Code anzeigen' trouvés")
            
            if total_count == 0:
                print("[MyDealz] Aucun code disponible")
                browser.close()
                return results
            
            processed_codes = set()
            
            # === ÉTAPE 1: Cliquer sur le premier bouton → ouvre nouvel onglet ===
            first_btn = see_code_buttons.first
            first_btn.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            
            print(f"[MyDealz] Clic sur le premier bouton...")
            pages_before = len(context.pages)
            page.evaluate("(el) => el.click()", first_btn.element_handle())
            page.wait_for_timeout(2000)
            
            # Vérifier si nouvel onglet ouvert
            if len(context.pages) > pages_before:
                work_page = context.pages[-1]
                print(f"[MyDealz] Nouvel onglet ouvert, switch dessus")
            else:
                work_page = page
                print(f"[MyDealz] Pas de nouvel onglet, on reste sur la page")

            # === CAPTURE DU LIEN AFFILIÉ ===
            # La page originale se redirige vers le site marchand
            try:
                for _ in range(10):  # Max 5 secondes
                    current_url = page.url
                    if "mydealz.de" not in current_url:
                        affiliate_link = current_url
                        print(f"[MyDealz] ✅ Affiliate link: {affiliate_link[:80]}...")
                        break
                    page.wait_for_timeout(500)
                if not affiliate_link:
                    print(f"[MyDealz] ⚠️ Pas de lien affilié capturé (page restée sur mydealz)")
            except Exception as e:
                print(f"[MyDealz] ⚠️ Erreur capture affiliate: {e}")

            # === ÉTAPE 2: Boucle sur work_page ===
            max_iterations = 20
            
            for iteration in range(max_iterations):
                print(f"\n[MyDealz] --- Itération {iteration + 1} ---")
                
                work_page.wait_for_timeout(2000)
                
                # 1. Récupérer le code dans la popup
                code = None
                try:
                    code_elem = work_page.locator("[data-testid='voucherPopup-codeHolder-voucherType-code'] h4").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                        if code == "Siehe Details" or ' ' in code:
                            print(f"[MyDealz] ⚠️ Pas un vrai code: {code}")
                            code = None
                        else:
                            print(f"[MyDealz] Code trouvé: {code}")
                except Exception as e:
                    print(f"[MyDealz] ⚠️ Erreur code: {str(e)[:40]}")
                
                # 2. Récupérer le titre dans la popup
                current_title = None
                try:
                    title_elem = work_page.locator("[data-testid='voucherPopup-header-popupTitleWrapper'] h4").first
                    if title_elem.count() > 0:
                        current_title = title_elem.inner_text().strip()
                        print(f"[MyDealz] Titre: {current_title[:60]}...")
                except:
                    pass
                
                if current_title is None:
                    current_title = f"Offre {iteration + 1}"
                
                if code and code not in processed_codes:
                    processed_codes.add(code)
                    results.append({
                        "code": code,
                        "title": current_title,
                        "affiliate_link": affiliate_link
                    })
                    print(f"[MyDealz] ✅ Ajouté: {code}")
                
                # 3. Fermer la popup avec CloseIcon
                try:
                    close_icon = work_page.locator("[data-testid='CloseIcon']").first
                    if close_icon.count() > 0:
                        close_icon.click(timeout=3000)
                        print("[MyDealz] Popup fermée")
                        work_page.wait_for_timeout(1500)
                except Exception as e:
                    print(f"[MyDealz] ⚠️ Erreur fermeture: {str(e)[:30]}")
                
                # 4. Chercher le prochain bouton sur work_page (même onglet)
                next_buttons = work_page.locator(code_selector)
                next_count = next_buttons.count()
                
                # Index = iteration + 1 (on a déjà traité iteration boutons)
                next_index = iteration + 1
                print(f"[MyDealz] Boutons: {next_count}, prochain index: {next_index}")
                
                if next_index >= next_count:
                    print("[MyDealz] Plus de boutons disponibles")
                    break
                
                # 5. Cliquer sur le prochain bouton → ouvre nouvel onglet → switch
                next_btn = next_buttons.nth(next_index)
                next_btn.scroll_into_view_if_needed()
                work_page.wait_for_timeout(500)
                
                print(f"[MyDealz] Clic sur bouton {next_index + 1}...")
                pages_before = len(context.pages)
                work_page.evaluate("(el) => el.click()", next_btn.element_handle())
                work_page.wait_for_timeout(2000)
                
                # Switch vers le nouvel onglet
                if len(context.pages) > pages_before:
                    work_page = context.pages[-1]
                    print(f"[MyDealz] Switch vers nouvel onglet")
            
        except Exception as e:
            print(f"[MyDealz] Erreur: {str(e)}")
            import traceback
            traceback.print_exc()
        
        browser.close()
    
    return results


def main():
    # URL de test - Bonprix sur MyDealz
    test_url = "https://www.mydealz.de/gutscheine/samsung-de"
    
    print("=" * 60)
    print("TEST MYDEALZ DE - SINGLE URL")
    print("=" * 60)
    print(f"URL: {test_url}")
    print("=" * 60)
    
    results = test_mydealz_single(test_url)
    
    print("\n" + "=" * 60)
    print("RÉSULTATS FINAUX")
    print("=" * 60)

    if results:
        if results[0].get("affiliate_link"):
            print(f"🔗 Affiliate Link: {results[0]['affiliate_link']}")
            print("-" * 60)
        for i, r in enumerate(results, 1):
            print(f"{i}. Code: {r['code']}")
            print(f"   Titre: {r['title']}")
            print()
    else:
        print("Aucun code trouvé")

    print(f"Total: {len(results)} codes uniques")


if __name__ == "__main__":
    main()
