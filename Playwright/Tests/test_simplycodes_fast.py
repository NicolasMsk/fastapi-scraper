"""
Test script pour SimplyCodes US - ULTRA OPTIMISÉ
Récupère tout via JavaScript en une seule fois, sans scroll
"""

from playwright.sync_api import sync_playwright
import time


def scrape_simplycodes_fast(page, context, url):
    """Scraping ultra-rapide via JavaScript - pas de scroll, pas de boucle"""
    results = []
    start_time = time.time()
    
    try:
        print(f"[SimplyCodes] Accès à l'URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        
        # Vérifier s'il y a des boutons "Show Code"
        has_codes = page.locator("[data-testid='promotion-copy-code-button']").count()
        
        if has_codes == 0:
            print("[SimplyCodes] Aucun code trouvé")
            return results
        
        print(f"[SimplyCodes] {has_codes} boutons détectés")
        
        # Recompter après Show more
        has_codes = page.locator("[data-testid='promotion-copy-code-button']").count()
        print(f"[SimplyCodes] {has_codes} boutons total, clic pour auth...")
        
        # UN SEUL clic pour déclencher l'authentification
        first_btn = page.locator("[data-testid='promotion-copy-code-button']").first
        
        try:
            with context.expect_page(timeout=8000) as new_page_info:
                first_btn.click()
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded")
            new_page.wait_for_timeout(1000)
        except:
            new_page = page
            new_page.wait_for_timeout(1000)
        
        print(f"[SimplyCodes] Auth OK - extraction JavaScript...")
        
        # D'ABORD: récupérer le code de la popup (premier code)
        try:
            popup_code = new_page.evaluate("""() => {
                // Chercher le code dans la popup (input readonly ou span)
                const input = document.querySelector('input[readonly]');
                if (input && input.value && input.value.length >= 3) return input.value.trim();
                
                const span = document.querySelector('span.font-bold.uppercase.truncate');
                if (span && span.textContent.trim().length >= 3) return span.textContent.trim();
                
                return null;
            }""")
            
            popup_title = new_page.evaluate("""() => {
                const el = document.querySelector("[data-testid='promotion-subtitle']");
                return el ? el.textContent.trim() : null;
            }""")
            
            if popup_code and popup_title and popup_code not in ['Show Code', 'Copy', 'Copied!']:
                results.append({"code": popup_code, "title": popup_title})
                print(f"[SimplyCodes] ✅ (popup) {popup_code} -> {popup_title[:50]}...")
        except:
            pass
        
        # FERMER LA POPUP avec le bouton X
        try:
            close_btn = new_page.locator("button:has(span.i-ph\\:x), button:has(span[class*='i-ph'][class*='x'])").first
            if close_btn.count() > 0:
                close_btn.click()
                new_page.wait_for_timeout(500)
                print(f"[SimplyCodes] ✅ Popup fermée")
            else:
                # Sinon clic en dehors de la popup
                new_page.mouse.click(10, 10)
                new_page.wait_for_timeout(500)
                print(f"[SimplyCodes] ✅ Popup fermée (clic extérieur)")
        except:
            pass
        
        # Cliquer sur "Show more" sur le nouvel onglet (2 fois max)
        for i in range(2):
            try:
                show_more = new_page.locator("button:text-is('Show more')").first
                if show_more.count() == 0:
                    show_more = new_page.locator("button:has-text('Show more')").first
                
                if show_more.count() > 0:
                    show_more.scroll_into_view_if_needed()
                    new_page.wait_for_timeout(200)
                    show_more.click(force=True)
                    new_page.wait_for_timeout(1000)
                    new_count = new_page.locator("[data-testid='promotion-copy-code-button']").count()
                    print(f"[SimplyCodes] ✅ Show more #{i+1} -> {new_count} boutons")
                else:
                    break
            except:
                break
        
        # ENSUITE: Extraction de tous les codes via JavaScript
        all_codes = new_page.evaluate("""() => {
            const results = [];
            
            // Chercher tous les boutons avec codes visibles
            document.querySelectorAll("[data-testid='promotion-copy-code-button']").forEach(btn => {
                const parent = btn.closest('div');
                if (!parent) return;
                
                // Code: dans un span font-bold à côté du bouton
                const codeSpan = parent.querySelector('span.font-bold, span.uppercase, span[class*="truncate"]');
                const code = codeSpan ? codeSpan.textContent.trim() : null;
                
                // Titre: remonter pour trouver promotion-subtitle
                let card = btn;
                for (let i = 0; i < 10; i++) {
                    card = card.parentElement;
                    if (!card) break;
                    const titleEl = card.querySelector("[data-testid='promotion-subtitle']");
                    if (titleEl) {
                        const title = titleEl.textContent.trim();
                        if (code && code.length >= 3 && !['Show Code', 'Copy', 'Copied!', 'Show code'].includes(code)) {
                            results.push({code, title});
                        }
                        break;
                    }
                }
            });
            
            return results;
        }""")
        
        # Dédupliquer (en excluant ceux déjà récupérés de la popup)
        seen = {r["code"] for r in results}
        for item in all_codes:
            code = item.get('code')
            title = item.get('title')
            if code and title and code not in seen:
                seen.add(code)
                results.append({"code": code, "title": title})
                print(f"[SimplyCodes] ✅ {code} -> {title[:50]}...")
        
        # Fermer le nouvel onglet
        if new_page != page:
            try:
                new_page.close()
            except:
                pass
        
        elapsed = time.time() - start_time
        print(f"[SimplyCodes] ⚡ Extraction terminée en {elapsed:.1f}s")
        
    except Exception as e:
        print(f"[SimplyCodes] Erreur: {str(e)}")
    
    return results


def main():
    test_url = "https://simplycodes.com/store/autodesk.com"
    
    print("=" * 60)
    print("TEST SIMPLYCODES - ULTRA RAPIDE")
    print("=" * 60)
    print(f"URL: {test_url}")
    print("=" * 60)
    
    start = time.time()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # headless=True pour max vitesse
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        results = scrape_simplycodes_fast(page, context, test_url)
        
        print("\n" + "=" * 60)
        print("RÉSULTATS")
        print("=" * 60)
        
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['code']} -> {r['title'][:60]}")
        
        print(f"\nTotal: {len(results)} codes")
        
        browser.close()
    
    total_time = time.time() - start
    print(f"\n⏱️ Temps total: {total_time:.1f}s")
    print("✅ Terminé !")


if __name__ == "__main__":
    main()
