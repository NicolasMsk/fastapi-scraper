"""
Script Playwright pour scraper TOUS les codes Sparwelt (DE)
- Même logique que MyDealz
- Chaque clic sur "Gutschein anzeigen" ouvre un NOUVEL ONGLET avec popup
- On récupère code + titre dans la popup
- On ferme la popup, puis on clique sur le bouton suivant (nouvel onglet)
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_sparwelt_all(page, context, url):
    """
    Scrape TOUS les codes d'une page Sparwelt avec Playwright.
    Approche rapide: JS clicks, suppression du cookie banner.
    """
    results = []

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_selector("div[data-voucher-id]", timeout=3000)
        except:
            page.wait_for_timeout(500)

        # Supprimer le cookie banner (cmpwrapper bloque les clics)
        page.evaluate('() => { var el = document.getElementById("cmpwrapper"); if(el) el.remove(); }')
        page.wait_for_timeout(200)

        code_selector = "div[data-voucher-id]:not(.grayscale) button:has-text('Gutschein anzeigen')"

        total_count = page.locator(code_selector).count()
        if total_count == 0:
            return results

        processed_codes = set()

        # === Ouvrir le premier bouton via JS click → nouvel onglet ===
        pages_before = len(context.pages)
        page.evaluate("""() => {
            var btns = document.querySelectorAll('div[data-voucher-id]:not(.grayscale) button');
            for (var b of btns) {
                if (b.textContent.includes('Gutschein anzeigen')) { b.click(); break; }
            }
        }""")
        try:
            context.wait_for_event("page", timeout=5000)
        except:
            page.wait_for_timeout(500)

        if len(context.pages) <= pages_before:
            return results
        work_page = context.pages[-1]
        work_page.wait_for_load_state("domcontentloaded", timeout=5000)

        # === Boucle: extraire code, fermer popup, cliquer suivant via JS ===
        for iteration in range(total_count):
            work_page.wait_for_timeout(400)

            # 1. Récupérer le code
            code = None
            try:
                code_elem = work_page.locator("div.p-4 div.border.font-bold span").first
                if code_elem.count() > 0:
                    code = code_elem.inner_text().strip()
                    if not code or ' ' in code or len(code) > 30:
                        code = None
            except:
                pass

            # 2. Récupérer le titre
            current_title = None
            try:
                title_elem = work_page.locator("div.p-4 div.text-xl").first
                if title_elem.count() > 0:
                    current_title = title_elem.inner_text().strip()
            except:
                pass

            if current_title is None:
                current_title = f"Offre {iteration + 1}"

            # 2b. Extraire terms + expiry depuis le <dl>
            terms = ""
            expiration_date = ""
            try:
                dl_data = work_page.evaluate("""() => {
                    var dl = document.querySelector('dl');
                    if (!dl) return {terms: '', expiry: ''};
                    var expiry = '';
                    var parts = [];
                    var dts = dl.querySelectorAll('dt');
                    dts.forEach(function(dt) {
                        var dd = dt.nextElementSibling;
                        if (!dd) return;
                        var label = dt.textContent.trim();
                        var value = dd.textContent.trim();
                        if (label.match(/Gültig bis/)) expiry = value;
                        parts.push(label + ' ' + value);
                    });
                    return {terms: parts.join(' | '), expiry: expiry};
                }""")
                terms = dl_data.get("terms", "")
                expiration_date = dl_data.get("expiry", "")
            except:
                pass

            # Ajouter si code valide
            if code and code not in processed_codes:
                processed_codes.add(code)
                results.append({
                    "code": code,
                    "title": current_title,
                    "terms": terms,
                    "expiration_date": expiration_date
                })

            # 3. Fermer la popup
            try:
                close_btn = work_page.locator("svg.absolute.top-4.right-4, svg.fill-gray-400.absolute").first
                if close_btn.count() > 0:
                    close_btn.click(timeout=1000)
                    work_page.wait_for_timeout(200)
            except:
                try:
                    work_page.keyboard.press("Escape")
                    work_page.wait_for_timeout(200)
                except:
                    pass

            # 4. Cliquer suivant via JS (évite element_handle qui bloque)
            next_idx = iteration + 1
            if next_idx >= total_count:
                break

            clicked = work_page.evaluate(f"""() => {{
                var btns = document.querySelectorAll('div[data-voucher-id]:not(.grayscale) button');
                var gutscheinBtns = [];
                btns.forEach(b => {{ if (b.textContent.includes('Gutschein anzeigen')) gutscheinBtns.push(b); }});
                if (gutscheinBtns[{next_idx}]) {{
                    gutscheinBtns[{next_idx}].scrollIntoView({{block: 'center'}});
                    gutscheinBtns[{next_idx}].click();
                    return true;
                }}
                return false;
            }}""")

            if not clicked:
                break

            try:
                context.wait_for_event("page", timeout=2000)
                if len(context.pages) > 2:
                    work_page = context.pages[-1]
            except:
                work_page.wait_for_timeout(300)

    except PlaywrightTimeout:
        pass
    except Exception as e:
        print(f"[Sparwelt] Erreur: {str(e)[:50]}")
    
    return results


def main():
    """Scrape Sparwelt DE depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")
    
    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("DE", "sparwelt")
    print(f"📍 Sparwelt: {len(competitor_data)} URLs uniques")
    
    if len(competitor_data) == 0:
        print("❌ Aucune URL Sparwelt trouvée")
        return
    
    all_results = []
    
    print(f"\n🚀 Lancement de Playwright...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        context.set_default_timeout(15000)  # 15s max per operation to prevent hangs
        page = context.new_page()
        
        for idx, (merchant_row, url) in enumerate(competitor_data, 1):
            merchant_slug = merchant_row.get('Merchant_slug', 'Unknown')
            
            print(f"\n[{idx}/{len(competitor_data)}] 🏪 {merchant_slug}")
            print(f"   URL: {url[:60]}...")
            
            try:
                codes = scrape_sparwelt_all(page, context, url)

                # Fermer tous les onglets sauf le premier pour éviter ERR_INSUFFICIENT_RESOURCES
                while len(context.pages) > 1:
                    context.pages[-1].close()

                print(f"   ✅ {len(codes)} codes trouvés")

                for code_info in codes:
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "DE",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "sparwelt",
                        "Competitor_URL": url,
                        "Code": code_info["code"],
                        "Title": code_info["title"],
                        "terms": code_info.get("terms", ""),
                        "expiration_date": code_info.get("expiration_date", "")
                    })

            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:50]}")

            # Fermer les onglets popup éventuels (garder la page principale)
            while len(context.pages) > 1:
                context.pages[-1].close()
        
        browser.close()
    
    # Sauvegarder les résultats
    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="Sparwelt DE")
        
        print(f"\n{'='*60}")
        print(f"✅ SPARWELT DE TERMINÉ!")
        print(f"{'='*60}")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
    else:
        print("\n❌ Aucun code trouvé")


if __name__ == "__main__":
    main()
