"""
Script Playwright pour scraper TOUS les codes SimplyCodes (US)
- Basé sur la logique FastAPI/scraper_simplycodes.py
- Clique sur le premier bouton pour auth, puis récupère tous les codes visibles
"""

import os
import sys
import random
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_simplycodes_all(page, context, url):
    """
    Scrape tous les codes d'une page SimplyCodes.
    Les codes sont visibles dans le DOM sans cliquer (dans les code verifications).
    On extrait directement via JS, sans ouvrir de nouvel onglet (Cloudflare bloque).
    """
    results = []

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(random.randint(1500, 3000))

        # Si Cloudflare bloque, recréer le contexte
        if page.evaluate('() => document.body.innerText.includes("been blocked")'):
            return results

        has_codes = page.locator("[data-testid='promotion-copy-code-button']").count()
        if has_codes == 0:
            return results

        # Extraction directe via .coupon-card-container (pas de "Show more" qui casse la page)
        # Les codes sont dans des spans avec classe "uppercase underline" (code verifications)
        all_codes = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('.coupon-card-container').forEach(card => {
                const titleEl = card.querySelector("[data-testid='promotion-subtitle']");
                const codeSpan = card.querySelector('span.uppercase.underline');
                const hasShowCode = card.querySelector("[data-testid='promotion-copy-code-button']");
                if (titleEl && codeSpan && hasShowCode) {
                    const code = codeSpan.textContent.trim();
                    if (code.length >= 3 && code.length <= 30) {
                        results.push({code: code, title: titleEl.textContent.trim()});
                    }
                }
            });
            return results;
        }""")

        seen = set()
        for item in all_codes:
            code = item.get('code')
            title = item.get('title')
            if code and title and code not in seen:
                seen.add(code)
                results.append({"code": code, "title": title, "terms": "", "expiration_date": ""})

        for r in results:
            print(f"[SimplyCodes] ✅ Code: {r['code']} | {r['title'][:50]}...")

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
        # headless=False pour bypass Cloudflare (xvfb-run sur GCP)
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                "--disable-gpu",
                "--no-sandbox",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}};
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(parameters)
            );
        """)
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
                        "Title": code_info["title"],
                        "terms": code_info.get("terms", ""),
                        "expiration_date": code_info.get("expiration_date", "")
                    })
            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:50]}")

            print(f"   📝 Total: {len(all_results)} codes")

            # Délai aléatoire entre les pages pour éviter le rate limiting Cloudflare
            page.wait_for_timeout(random.randint(500, 1500))

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
