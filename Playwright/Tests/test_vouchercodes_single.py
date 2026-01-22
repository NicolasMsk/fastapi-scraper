"""
Test script pour VoucherCodes UK - Tester une seule URL
"""

from playwright.sync_api import sync_playwright


def scrape_vouchercodes_test(page, context, url):
    """Test de scraping VoucherCodes"""
    results = []
    
    try:
        print(f"[VoucherCodes] Accès à l'URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Fermer cookie banner
        try:
            page.click("button:has-text('Accept'), button:has-text('Agree')", timeout=3000)
            page.wait_for_timeout(1000)
        except:
            pass
        
        # Trouver tous les boutons "Get Code"
        get_code_buttons = page.locator("button:has-text('Get Code')")
        count = get_code_buttons.count()
        
        print(f"[VoucherCodes] {count} boutons 'Get Code' trouvés")
        
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
        
        print("[VoucherCodes] Switché vers le nouvel onglet")
        
        # Itérer sur tous les codes
        max_iterations = count + 5
        
        for iteration in range(max_iterations):
            try:
                print(f"\n[VoucherCodes] --- Itération {iteration + 1} ---")
                new_page.wait_for_timeout(1500)
                
                # Chercher le code dans la popup
                code = None
                title = None
                
                # Sélecteur principal pour VoucherCodes
                try:
                    code_elem = new_page.locator("p[data-qa='el:code']").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                        print(f"[VoucherCodes] Code trouvé via p[data-qa='el:code']: {code}")
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
                                print(f"[VoucherCodes] Code trouvé via p.font-bold: {code}")
                                break
                    except:
                        pass
                
                # Chercher le titre dans la popup
                try:
                    title_elem = new_page.locator("div[data-qa='el:offerTitle']").first
                    if title_elem.count() > 0:
                        title = title_elem.inner_text().strip()
                        print(f"[VoucherCodes] Titre trouvé: {title[:60]}...")
                except:
                    pass  # Ne pas mettre de valeur par défaut
                
                # N'ajouter que si code ET titre sont trouvés, et pas de doublon
                if code and title and code not in processed_codes and title not in processed_titles:
                    processed_codes.add(code)
                    processed_titles.add(title)
                    results.append({"code": code, "title": title})
                    print(f"[VoucherCodes] ✅ AJOUTÉ: {code} -> {title[:50]}...")
                elif code and not title:
                    print(f"[VoucherCodes] ⚠️ Titre non trouvé pour le code: {code}")
                else:
                    print(f"[VoucherCodes] ⚠️ Code non trouvé ou doublon")
                
                # Fermer la popup
                try:
                    close_btn = new_page.locator("button:has(svg[data-qa='el:closeIcon'])").first
                    close_btn.click()
                    new_page.wait_for_timeout(500)
                    print("[VoucherCodes] Popup fermée via closeIcon")
                except:
                    try:
                        close_btn = new_page.locator("button.rounded-full:has(svg)").first
                        close_btn.click()
                        new_page.wait_for_timeout(500)
                        print("[VoucherCodes] Popup fermée via fallback")
                    except:
                        print("[VoucherCodes] Impossible de fermer la popup")
                        pass
                
                # Cliquer sur le prochain bouton "Get Code" 
                # IMPORTANT: Chaque clic ouvre un NOUVEL onglet
                # On utilise iteration + 1 car on a déjà cliqué sur le bouton 0 (premier)
                next_index = iteration + 1
                next_buttons = new_page.locator("button:has-text('Get Code')")
                next_count = next_buttons.count()
                
                print(f"[VoucherCodes] {next_count} boutons 'Get Code' disponibles, prochain index: {next_index}")
                
                if next_index >= next_count:
                    print("[VoucherCodes] Plus de boutons disponibles")
                    break
                
                next_btn = next_buttons.nth(next_index)
                next_btn.scroll_into_view_if_needed()
                
                # Utiliser expect_page pour capturer le nouvel onglet
                try:
                    with context.expect_page(timeout=5000) as next_page_info:
                        next_btn.click()
                    next_new_page = next_page_info.value
                    next_new_page.wait_for_load_state("domcontentloaded")
                    next_new_page.wait_for_timeout(1500)
                    
                    # Fermer l'ancien onglet et utiliser le nouveau
                    new_page.close()
                    new_page = next_new_page
                    print(f"[VoucherCodes] Switché vers nouvel onglet après bouton {next_index + 1}")
                except Exception as e:
                    print(f"[VoucherCodes] Pas de nouvel onglet ouvert: {str(e)[:50]}")
                    break
                
            except Exception as e:
                print(f"[VoucherCodes] Erreur iteration {iteration}: {str(e)[:50]}")
                continue
        
        # Fermer le nouvel onglet
        try:
            new_page.close()
        except:
            pass
        
    except Exception as e:
        print(f"[VoucherCodes] Erreur globale: {str(e)}")
    
    return results


def main():
    # URL de test - ASOS UK sur VoucherCodes
    test_url = "https://www.vouchercodes.co.uk/asos.com"
    
    print("=" * 60)
    print("TEST VOUCHERCODES UK - SINGLE URL")
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
        
        results = scrape_vouchercodes_test(page, context, test_url)
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("RÉSULTATS")
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
