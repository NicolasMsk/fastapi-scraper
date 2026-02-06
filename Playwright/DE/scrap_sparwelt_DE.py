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
    Chaque clic ouvre un nouvel onglet → switch → récupérer code → fermer → répéter
    """
    results = []

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Fermer cookie banner si présent
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
        
        if total_count == 0:
            return results
        
        processed_codes = set()
        
        # === ÉTAPE 1: Cliquer sur le premier bouton → ouvre nouvel onglet ===
        first_btn = see_code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        
        pages_before = len(context.pages)
        page.evaluate("(el) => el.click()", first_btn.element_handle())
        page.wait_for_timeout(2000)
        
        # Vérifier si nouvel onglet ouvert
        if len(context.pages) > pages_before:
            work_page = context.pages[-1]
        else:
            work_page = page

        # === ÉTAPE 2: Boucle sur work_page ===
        max_iterations = 50
        
        for iteration in range(max_iterations):
            work_page.wait_for_timeout(2000)
            
            # 1. Récupérer le code dans la popup
            code = None
            try:
                code_elem = work_page.locator("div.p-4 div.border.font-bold span").first
                if code_elem.count() > 0:
                    code = code_elem.inner_text().strip()
                    # Filtrer codes invalides
                    if not code or ' ' in code or len(code) > 30:
                        code = None
            except:
                pass
            
            # 2. Récupérer le titre dans la popup
            current_title = None
            try:
                title_elem = work_page.locator("div.p-4 div.text-xl").first
                if title_elem.count() > 0:
                    current_title = title_elem.inner_text().strip()
            except:
                pass
            
            if current_title is None:
                current_title = f"Offre {iteration + 1}"
            
            # Ajouter si code valide et non dupliqué
            if code and code not in processed_codes:
                processed_codes.add(code)
                results.append({
                    "code": code,
                    "title": current_title
                })
            
            # 3. Fermer la popup avec le X
            try:
                close_btn = work_page.locator("svg.absolute.top-4.right-4, svg.fill-gray-400.absolute").first
                if close_btn.count() > 0:
                    close_btn.click(timeout=3000)
                    work_page.wait_for_timeout(1500)
            except:
                try:
                    work_page.keyboard.press("Escape")
                    work_page.wait_for_timeout(1000)
                except:
                    pass
            
            # Scroll vers le haut
            work_page.evaluate("window.scrollTo(0, 0)")
            work_page.wait_for_timeout(1000)
            
            # 4. Chercher le prochain bouton sur work_page
            next_buttons = work_page.locator(code_selector)
            next_count = next_buttons.count()
            
            next_index = iteration + 1
            
            if next_index >= next_count:
                break
            
            # 5. Cliquer sur le prochain bouton → ouvre nouvel onglet → switch
            next_btn = next_buttons.nth(next_index)
            
            try:
                next_btn.scroll_into_view_if_needed(timeout=5000)
                work_page.wait_for_timeout(500)
            except:
                work_page.evaluate("window.scrollBy(0, 300)")
                work_page.wait_for_timeout(500)
            
            pages_before = len(context.pages)
            
            try:
                work_page.evaluate("(el) => el.click()", next_btn.element_handle())
            except:
                next_btn.click(force=True, timeout=5000)
            
            work_page.wait_for_timeout(2000)
            
            # Switch vers le nouvel onglet
            if len(context.pages) > pages_before:
                work_page = context.pages[-1]
        
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
        page = context.new_page()
        
        for idx, (merchant_row, url) in enumerate(competitor_data, 1):
            merchant_slug = merchant_row.get('Merchant_slug', 'Unknown')
            
            print(f"\n[{idx}/{len(competitor_data)}] 🏪 {merchant_slug}")
            print(f"   URL: {url[:60]}...")
            
            try:
                codes = scrape_sparwelt_all(page, context, url)
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
                        "Title": code_info["title"]
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
