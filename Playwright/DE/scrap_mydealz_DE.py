"""
Script Playwright pour scraper TOUS les codes MyDealz (DE)
- Basé sur la logique HotUKDeals/Chollometro
- Chaque clic sur "Code anzeigen" ouvre un NOUVEL ONGLET avec popup
- On récupère code + titre dans la popup
- On ferme la popup, puis on clique sur le bouton suivant (nouvel onglet)
- EXCLUT les codes expirés (dans div.jkau50)
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_mydealz_all(page, context, url):
    """
    Scrape TOUS les codes d'une page MyDealz avec Playwright.
    Approche rapide: ouvre un onglet, puis itère via JS clicks sur work_page.
    """
    results = []

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_selector("div[data-testid='active-vouchers-widget']", timeout=5000)
        except:
            page.wait_for_timeout(1000)

        # Fermer cookie banner si présent
        try:
            page.click("button:has-text('Akzeptieren'), button:has-text('Accept'), #onetrust-accept-btn-handler", timeout=1500)
            page.wait_for_timeout(300)
        except:
            pass

        code_selector = "div[data-testid='active-vouchers-widget'] div[title='Code anzeigen']"

        total_count = page.locator(code_selector).count()
        if total_count == 0:
            return results

        # 1. Pré-extraire expiry dates
        title_to_expiry = {}
        title_expiry_data = page.evaluate("""() => {
            const cards = document.querySelectorAll("div[data-testid='vouchers-ui-voucher-card']");
            const pairs = [];
            cards.forEach(card => {
                const h3 = card.querySelector("h3");
                const title = h3 ? h3.textContent.trim() : '';
                let expiry = '';
                card.querySelectorAll("span").forEach(span => {
                    const txt = span.textContent.trim();
                    if (txt.match(/Gültig bis/)) {
                        expiry = txt.replace(/^Gültig bis:\\s*/, '').trim();
                    }
                });
                if (title) pairs.push([title, expiry]);
            });
            return pairs;
        }""")
        for pair in title_expiry_data:
            if pair[0]:
                title_to_expiry[pair[0]] = pair[1]
        if title_to_expiry:
            print(f"[MyDealz] {len(title_to_expiry)} dates d'expiration pré-extraites")

        # 2. Cliquer sur tous les boutons "Details" pour révéler les terms
        title_to_terms = {}
        details_buttons = page.locator("div[data-testid='active-vouchers-widget'] button._1nymodn1")
        details_count = details_buttons.count()
        for i in range(details_count):
            try:
                details_buttons.nth(i).scroll_into_view_if_needed(timeout=1000)
                details_buttons.nth(i).click(timeout=1000)
                page.wait_for_timeout(50)
            except:
                pass
        page.wait_for_timeout(200)

        # 3. Extraire les terms
        title_terms_data = page.evaluate("""() => {
            const cards = document.querySelectorAll("div[data-testid='vouchers-ui-voucher-card']");
            const pairs = [];
            cards.forEach(card => {
                const h3 = card.querySelector("h3");
                const title = h3 ? h3.textContent.trim() : '';
                let terms = '';
                const richText = card.querySelector('div[data-testid="rich-text-root"]');
                if (richText) terms = richText.textContent.trim();
                if (title) pairs.push([title, terms]);
            });
            return pairs;
        }""")
        for pair in title_terms_data:
            if pair[0] and pair[1]:
                title_to_terms[pair[0]] = pair[1]

        processed_codes = set()

        # === Ouvrir le premier bouton via JS click → nouvel onglet ===
        pages_before = len(context.pages)
        page.evaluate("""() => {
            var btn = document.querySelector("div[data-testid='active-vouchers-widget'] div[title='Code anzeigen']");
            if (btn) { btn.scrollIntoView({block: 'center'}); btn.click(); }
        }""")
        try:
            context.wait_for_event("page", timeout=5000)
        except:
            page.wait_for_timeout(500)

        if len(context.pages) <= pages_before:
            return results
        work_page = context.pages[-1]
        work_page.wait_for_load_state("domcontentloaded", timeout=5000)

        # === Boucle: extraire code du popup, fermer, cliquer suivant via JS ===
        for iteration in range(total_count):
            # Attendre la popup
            try:
                work_page.wait_for_selector("[data-testid='voucherPopup-codeHolder-voucherType-code'] h4", timeout=2000)
            except:
                pass

            # Récupérer le code
            code = None
            try:
                code_el = work_page.locator("[data-testid='voucherPopup-codeHolder-voucherType-code'] h4")
                if code_el.count() > 0:
                    code = code_el.first.inner_text().strip()
                    if code == "Siehe Details" or ' ' in code or not code:
                        code = None
            except:
                pass

            # Récupérer le titre
            current_title = None
            try:
                title_el = work_page.locator("[data-testid='voucherPopup-header-popupTitleWrapper'] h4")
                if title_el.count() > 0:
                    current_title = title_el.first.inner_text().strip()
            except:
                pass

            if current_title is None:
                current_title = f"Offre {iteration + 1}"

            # Ajouter si code valide
            if code and code not in processed_codes:
                processed_codes.add(code)
                results.append({
                    "code": code,
                    "title": current_title,
                    "terms": title_to_terms.get(current_title, ""),
                    "expiration_date": title_to_expiry.get(current_title, "")
                })

            # Fermer la popup
            try:
                work_page.locator("[data-testid='CloseIcon']").first.click(timeout=1000)
                work_page.wait_for_timeout(300)
            except:
                pass

            # Cliquer sur le prochain bouton via JS (évite element_handle qui bloque)
            next_idx = iteration + 1
            if next_idx >= total_count:
                break

            clicked = work_page.evaluate(f"""() => {{
                var btns = document.querySelectorAll("div[data-testid='active-vouchers-widget'] div[title='Code anzeigen']");
                if (btns[{next_idx}]) {{
                    btns[{next_idx}].scrollIntoView({{block: 'center'}});
                    btns[{next_idx}].click();
                    return true;
                }}
                return false;
            }}""")

            if not clicked:
                break

            # Check si nouvel onglet
            try:
                context.wait_for_event("page", timeout=2000)
                if len(context.pages) > 2:
                    work_page = context.pages[-1]
            except:
                work_page.wait_for_timeout(300)

    except PlaywrightTimeout:
        pass
    except Exception as e:
        print(f"[MyDealz] Erreur: {str(e)[:50]}")

    return results


def main():
    """Scrape MyDealz DE depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")
    
    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("DE", "mydealz")
    print(f"📍 MyDealz: {len(competitor_data)} URLs uniques")
    
    if len(competitor_data) == 0:
        print("❌ Aucune URL MyDealz trouvée")
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
                codes = scrape_mydealz_all(page, context, url)

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
                        "Competitor_Source": "mydealz",
                        "Competitor_URL": url,
                        "Code": code_info["code"],
                        "Title": code_info["title"],
                        "terms": code_info.get("terms", ""),
                        "expiration_date": code_info.get("expiration_date", "")
                    })

            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:50]}")

            print(f"   📝 Total: {len(all_results)} codes")

            # Fermer les onglets popup éventuels (garder la page principale)
            while len(context.pages) > 1:
                context.pages[-1].close()
        
        browser.close()
    
    # Sauvegarder les résultats
    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="MyDealz DE")
        
        print(f"\n{'='*60}")
        print(f"✅ MYDEALZ DE TERMINÉ!")
        print(f"{'='*60}")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
    else:
        print("\n❌ Aucun code trouvé")


if __name__ == "__main__":
    main()
