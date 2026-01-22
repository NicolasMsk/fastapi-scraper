"""
Test script pour SimplyCodes US - Tester une seule URL
Basé sur la logique FastAPI/scraper_simplycodes.py
"""

from playwright.sync_api import sync_playwright


def scrape_simplycodes_test(page, context, url):
    """Test de scraping SimplyCodes - basé sur FastAPI - OPTIMISÉ"""
    results = []
    
    try:
        print(f"[SimplyCodes] Accès à l'URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)  # Réduit de 5000 à 2000
        
        # Trouver tous les boutons "Show Code"
        show_code_buttons = page.locator("[data-testid='promotion-copy-code-button']")
        count = show_code_buttons.count()
        
        print(f"[SimplyCodes] {count} boutons 'Show Code' trouvés")
        
        if count == 0:
            print("[SimplyCodes] Aucun bouton trouvé, fin du test")
            return results
        
        # Récupérer le titre du premier code AVANT de cliquer
        first_title = None
        try:
            first_btn = show_code_buttons.first
            # Remonter pour trouver le conteneur parent
            container = first_btn.locator("xpath=ancestor::div[contains(@class, 'promotion') or contains(@class, 'card')]").first
            title_elem = container.locator("[data-testid='promotion-subtitle']").first
            if title_elem.count() > 0:
                first_title = title_elem.inner_text().strip()
                print(f"[SimplyCodes] Premier titre: {first_title[:50]}...")
        except Exception as e:
            print(f"[SimplyCodes] Erreur récup titre: {str(e)[:40]}")
        
        # Cliquer sur le PREMIER bouton pour déclencher l'authentification
        first_btn = show_code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(300)  # Réduit de 1000 à 300
        
        # Cliquer et capturer le nouvel onglet
        with context.expect_page(timeout=10000) as new_page_info:
            first_btn.click()
        
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded")
        new_page.wait_for_timeout(1500)  # Réduit de 3000 à 1500
        
        print(f"[SimplyCodes] Nouvel onglet ouvert: {new_page.url[:60]}...")
        
        # Récupérer le code depuis la popup
        popup_code = None
        try:
            # Le code est souvent dans un input readonly ou span
            code_selectors = [
                "input[readonly]",
                "span.font-bold.uppercase.truncate",
                "div.font-bold.uppercase",
                "[data-testid*='code']"
            ]
            
            for selector in code_selectors:
                try:
                    elem = new_page.locator(selector).first
                    if elem.count() > 0:
                        text = elem.get_attribute("value") or elem.inner_text()
                        if text and len(text.strip()) > 3 and text.strip() not in ["Show Code", "Copied!", "Copy"]:
                            popup_code = text.strip()
                            print(f"[SimplyCodes] Code trouvé via {selector}: {popup_code}")
                            break
                except:
                    continue
            
            if popup_code and first_title:
                results.append({"code": popup_code, "title": first_title})
                print(f"[SimplyCodes] ✅ AJOUTÉ (popup): {popup_code} -> {first_title[:50]}...")
            elif popup_code:
                print(f"[SimplyCodes] ⚠️ Code trouvé mais pas de titre: {popup_code}")
        except Exception as e:
            print(f"[SimplyCodes] Erreur récup popup: {str(e)[:40]}")
        
        # Fermer la popup (bouton X)
        try:
            close_btn = new_page.locator("[class*='i-ph'][class*='x'], button:has(svg), .close-button").first
            if close_btn.count() > 0:
                close_btn.click()
                new_page.wait_for_timeout(500)  # Réduit de 2000 à 500
                print("[SimplyCodes] Popup fermée")
        except:
            print("[SimplyCodes] Pas de bouton fermer trouvé")
        
        # Récupérer TOUS les codes visibles d'un coup via JavaScript (pas de scroll!)
        print("\n[SimplyCodes] Récupération de tous les codes visibles...")
        
        processed_codes = {r["code"] for r in results}
        
        # Extraction rapide via JavaScript - pas de scroll, pas de boucle lente
        all_codes_data = new_page.evaluate("""() => {
            const results = [];
            const buttons = document.querySelectorAll("[data-testid='promotion-copy-code-button']");
            
            buttons.forEach(btn => {
                // Chercher le code dans le span à côté du bouton
                const container = btn.closest('div');
                const codeElem = container ? container.querySelector('span.font-bold, span.uppercase') : null;
                const code = codeElem ? codeElem.textContent.trim() : null;
                
                // Chercher le titre dans le parent
                const card = btn.closest('[class*="promotion"], [class*="card"]') || btn.parentElement?.parentElement?.parentElement;
                const titleElem = card ? card.querySelector("[data-testid='promotion-subtitle']") : null;
                const title = titleElem ? titleElem.textContent.trim() : null;
                
                if (code && title && code.length > 3 && !['Show Code', 'Copy', 'Copied!'].includes(code)) {
                    results.push({code, title});
                }
            });
            
            return results;
        }""")
        
        print(f"[SimplyCodes] {len(all_codes_data)} codes trouvés via JS")
        
        for item in all_codes_data:
            code = item.get('code')
            title = item.get('title')
            if code and title and code not in processed_codes:
                processed_codes.add(code)
                results.append({"code": code, "title": title})
                print(f"[SimplyCodes] ✅ AJOUTÉ: {code} -> {title[:50]}...")
        
        # Fermer le nouvel onglet
        try:
            new_page.close()
        except:
            pass
        
    except Exception as e:
        print(f"[SimplyCodes] Erreur: {str(e)}")
    
    return results


def main():
    # URL de test - Autodesk sur SimplyCodes
    test_url = "https://simplycodes.com/store/autodesk.com"
    
    print("=" * 60)
    print("TEST SIMPLYCODES US - SINGLE URL")
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
        
        results = scrape_simplycodes_test(page, context, test_url)
        
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
        
        print(f"Total: {len(results)} codes")
        
        browser.close()
        print("\n✅ Test terminé !")


if __name__ == "__main__":
    main()
