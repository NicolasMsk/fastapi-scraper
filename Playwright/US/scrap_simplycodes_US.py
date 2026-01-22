"""
Script Playwright pour scraper TOUS les codes SimplyCodes (US)
- Basé sur la logique FastAPI/scraper_simplycodes.py
- Clique sur le premier bouton pour auth, puis récupère tous les codes visibles
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_simplycodes_all(page, context, url):
    """Scrape tous les codes d'une page SimplyCodes - VERSION OPTIMISÉE"""
    results = []
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        
        # Vérifier s'il y a des boutons "Show Code"
        has_codes = page.locator("[data-testid='promotion-copy-code-button']").count()
        
        if has_codes == 0:
            return results
        
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
        
        # D'ABORD: récupérer le code de la popup (premier code)
        try:
            popup_code = new_page.evaluate("""() => {
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
        except:
            pass
        
        # FERMER LA POPUP avec le bouton X ou clic extérieur
        try:
            close_btn = new_page.locator("button:has(span.i-ph\\:x), button:has(span[class*='i-ph'][class*='x'])").first
            if close_btn.count() > 0:
                close_btn.click()
                new_page.wait_for_timeout(500)
            else:
                new_page.mouse.click(10, 10)
                new_page.wait_for_timeout(500)
        except:
            pass
        
        # Cliquer sur "Show more" 2 fois pour afficher plus de codes
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
                else:
                    break
            except:
                break
        
        # EXTRACTION COMPLÈTE VIA JAVASCRIPT - INSTANTANÉ
        all_codes = new_page.evaluate("""() => {
            const results = [];
            document.querySelectorAll("[data-testid='promotion-copy-code-button']").forEach(btn => {
                const parent = btn.closest('div');
                if (!parent) return;
                
                const codeSpan = parent.querySelector('span.font-bold, span.uppercase, span[class*="truncate"]');
                const code = codeSpan ? codeSpan.textContent.trim() : null;
                
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
        
        # Dédupliquer
        seen = {r["code"] for r in results}
        for item in all_codes:
            code = item.get('code')
            title = item.get('title')
            if code and title and code not in seen:
                seen.add(code)
                results.append({"code": code, "title": title})
        
        # Fermer le nouvel onglet
        if new_page != page:
            try:
                new_page.close()
            except:
                pass
        
    except Exception as e:
        print(f"      ❌ Erreur: {str(e)[:50]}")
    
    return results


def main():
    """Scrape SimplyCodes US depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")
    
    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("US", "simplycodes")
    print(f"📍 SimplyCodes: {len(competitor_data)} URLs uniques")
    
    all_results = []
    
    print(f"\n🚀 Lancement de Playwright...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        for idx, (merchant_row, url) in enumerate(competitor_data, 1):
            merchant_slug = merchant_row.get('Merchant_slug', 'Unknown')
            
            print(f"\n[{idx}/{len(competitor_data)}] 🏪 {merchant_slug}")
            print(f"   URL: {url[:60]}...")
            
            try:
                codes = scrape_simplycodes_all(page, context, url)
                print(f"   ✅ {len(codes)} codes trouvés")
                
                for code_info in codes:
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "US",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "simplycodes",
                        "Competitor_URL": url,
                        "Code": code_info["code"],
                        "Title": code_info["title"]
                    })
            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:50]}")
            
            print(f"   📝 Total: {len(all_results)} codes")
        
        browser.close()
    
    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="SimplyCodes US")
        
        print(f"\n{'='*60}")
        print(f"✅ SIMPLYCODES US TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")


if __name__ == "__main__":
    main()
