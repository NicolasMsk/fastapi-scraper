"""
Test script pour VoucherCodes UK - Tester une seule URL
Exactement comme le script de production + capture lien affilié
"""

from playwright.sync_api import sync_playwright


def scrape_vouchercodes_test(page, context, url):
    """Scrape tous les codes d'une page VoucherCodes avec Playwright"""
    results = []
    affiliate_link = None
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        
        # Fermer cookie banner
        try:
            page.click("#onetrust-accept-btn-handler", timeout=3000)
            page.wait_for_timeout(500)
        except:
            pass
        
        # Trouver TOUS les boutons "Get Code" (on vérifiera l'exclusivité après clic)
        get_code_buttons = page.locator("button[data-qa='el:offerPrimaryButton']:has-text('Get Code')")
        count = get_code_buttons.count()

        if count == 0:
            get_code_buttons = page.locator("button:has-text('Get Code')")
            count = get_code_buttons.count()
        
        print(f"[VoucherCodes] {count} boutons 'Get Code' trouvés")
        
        if count == 0:
            return results, affiliate_link
        
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
        
        # === CAPTURE DU LIEN AFFILIÉ ===
        # La page originale se redirige vers le site marchand
        try:
            # Attendre que l'URL change (ne soit plus vouchercodes)
            for _ in range(10):  # Max 5 secondes
                current_url = page.url
                if "vouchercodes.co.uk" not in current_url:
                    affiliate_link = current_url
                    print(f"[VoucherCodes] ✅ Affiliate link: {affiliate_link[:80]}...")
                    break
                page.wait_for_timeout(500)
        except Exception as e:
            print(f"[VoucherCodes] ⚠️ Erreur capture affiliate: {e}")
        
        # Itérer sur tous les codes (on en a détecté 'count' au départ)
        # Pattern d'indexation: 0, 0, 1, 2, 3, ..., N-2
        for iteration in range(count):
            try:
                new_page.wait_for_timeout(1500)
                
                # Chercher le code dans la popup
                code = None
                title = None
                
                # Sélecteur principal pour VoucherCodes
                try:
                    code_elem = new_page.locator("p[data-qa='el:code']").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
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
                                break
                    except:
                        pass
                
                # Chercher le titre dans la popup
                try:
                    title_elem = new_page.locator("div[data-qa='el:offerTitle']").first
                    if title_elem.count() > 0:
                        title = title_elem.inner_text().strip()
                except:
                    pass
                
                # Vérifier si c'est une offre Exclusive (à ignorer)
                # On cherche le tag UNIQUEMENT dans le conteneur PARENT DIRECT du titre trouvé
                is_exclusive = False
                try:
                    if title_elem and title_elem.count() > 0:
                        parent_container = title_elem.locator("xpath=..")
                        exclusive_tag = parent_container.locator("span[data-qa='el:exclusiveTag']")
                        if exclusive_tag.count() > 0:
                            is_exclusive = True
                except:
                    pass
                
                # N'ajouter que si code ET titre sont trouvés ET pas Exclusive
                if code and title and not is_exclusive and code not in processed_codes and title not in processed_titles:
                    processed_codes.add(code)
                    processed_titles.add(title)
                    results.append({"code": code, "title": title, "affiliate_link": affiliate_link})
                    print(f"[VoucherCodes] ✅ Code: {code} | {title[:50]}...")
                else:
                    # Logger pourquoi le code n'est pas ajouté
                    if not code:
                        print(f"[VoucherCodes] ⚠️ Code non trouvé | Titre: {title[:50] if title else 'N/A'}...")
                    elif not title:
                        print(f"[VoucherCodes] ⚠️ Titre non trouvé (code: {code})")
                    elif is_exclusive:
                        print(f"[VoucherCodes] ⚠️ EXCLUSIVE ignorée: {code} | {title[:50]}...")
                    elif code in processed_codes:
                        print(f"[VoucherCodes] ⚠️ Code doublon: {code}")
                    elif title in processed_titles:
                        print(f"[VoucherCodes] ⚠️ Titre doublon: {title[:50]}...")
                
                # Fermer la popup - plusieurs sélecteurs possibles
                popup_closed = False
                close_selectors = [
                    "button.rounded-full.bg-white.absolute",
                    "button.absolute.right-0.top-0",
                    "button:has(svg[aria-label='close icon'])",
                    "button.rounded-full.bg-white:has(svg[data-qa='el:closeIcon'])",
                    "button:has(svg[data-qa='el:closeIcon'])",
                    "button.rounded-full:has(svg)",
                ]

                for selector in close_selectors:
                    try:
                        close_btn = new_page.locator(selector).first
                        if close_btn.count() > 0 and close_btn.is_visible():
                            close_btn.click()
                            new_page.wait_for_timeout(500)
                            popup_closed = True
                            break
                    except:
                        continue

                if not popup_closed:
                    try:
                        new_page.keyboard.press("Escape")
                        new_page.wait_for_timeout(500)
                    except:
                        pass
                
                # Si c'est la dernière itération, pas besoin de cliquer sur le prochain bouton
                if iteration == count - 1:
                    break
                
                # Cliquer sur le prochain bouton "Get Code"
                next_buttons = new_page.locator("button[data-qa='el:offerPrimaryButton']:has-text('Get Code')")
                if next_buttons.count() == 0:
                    next_buttons = new_page.locator("button:has-text('Get Code')")

                # S'il n'y a plus de boutons, on a terminé
                if next_buttons.count() == 0:
                    break

                # Calculer l'index: après iteration 0 → index 0, après iteration 1 → index 1, etc.
                next_index = iteration
                next_btn = next_buttons.nth(next_index)
                next_btn.scroll_into_view_if_needed()
                new_page.wait_for_timeout(300)
                
                # Ouvrir dans un nouvel onglet
                with context.expect_page() as next_page_info:
                    next_btn.click()
                
                next_new_page = next_page_info.value
                next_new_page.wait_for_load_state("domcontentloaded")
                
                # Fermer l'ancien onglet et utiliser le nouveau
                new_page.close()
                new_page = next_new_page
                
            except Exception as e:
                break
        
        # Fermer le dernier onglet
        try:
            new_page.close()
        except:
            pass
        
    except Exception as e:
        print(f"[VoucherCodes] ❌ Erreur: {str(e)[:50]}")
    
    return results, affiliate_link


def main():
    # URL de test - ASOS UK sur VoucherCodes
    test_url = "https://www.vouchercodes.co.uk/asos.com"
    
    print("=" * 60)
    print("TEST VOUCHERCODES UK - SINGLE URL")
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
        
        results, affiliate_link = scrape_vouchercodes_test(page, context, test_url)
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("RÉSULTATS")
    print("=" * 60)
    
    print(f"\n🔗 AFFILIATE LINK: {affiliate_link or 'Non capturé'}\n")
    
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
