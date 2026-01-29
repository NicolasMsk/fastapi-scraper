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
    Chaque clic ouvre un nouvel onglet → switch → récupérer code → fermer → répéter
    """
    results = []
    affiliate_link = None
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Fermer cookie banner si présent
        try:
            page.click("button:has-text('Akzeptieren'), button:has-text('Accept'), #onetrust-accept-btn-handler", timeout=3000)
            page.wait_for_timeout(1000)
        except:
            pass
        
        # Sélecteur: "Code anzeigen" dans active-vouchers-widget UNIQUEMENT (exclut expirés)
        code_selector = "div[data-testid='active-vouchers-widget'] div[title='Code anzeigen']"
        
        see_code_buttons = page.locator(code_selector)
        total_count = see_code_buttons.count()
        
        if total_count == 0:
            return results, affiliate_link
        
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

        # === CAPTURE DU LIEN AFFILIÉ ===
        # La page ORIGINALE se redirige vers le site marchand
        # Attend jusqu'à 10 secondes et vérifie que l'URL est stable (1.5s)
        try:
            last_url = None
            stable_count = 0
            for _ in range(20):  # Max 10 secondes
                current_url = page.url
                if "mydealz" not in current_url.lower():
                    if current_url == last_url:
                        stable_count += 1
                        if stable_count >= 3:  # URL stable pendant 1.5 secondes
                            affiliate_link = current_url
                            print(f"      🔗 Affiliate captured: {affiliate_link[:60]}...")
                            break
                    else:
                        stable_count = 0
                        last_url = current_url
                page.wait_for_timeout(500)
            if not affiliate_link:
                print(f"      ⚠️ No affiliate link captured (page stayed on mydealz)")
        except Exception as e:
            print(f"      ⚠️ Error capturing affiliate: {str(e)[:30]}")
        
        # === ÉTAPE 2: Boucle sur work_page ===
        max_iterations = 50
        
        for iteration in range(max_iterations):
            work_page.wait_for_timeout(2000)
            
            # 1. Récupérer le code dans la popup
            code = None
            try:
                code_elem = work_page.locator("[data-testid='voucherPopup-codeHolder-voucherType-code'] h4").first
                if code_elem.count() > 0:
                    code = code_elem.inner_text().strip()
                    # Filtrer "Siehe Details" et codes avec espaces (pas de vrais codes)
                    if code == "Siehe Details" or ' ' in code or not code:
                        code = None
            except:
                pass
            
            # 2. Récupérer le titre dans la popup
            current_title = None
            try:
                title_elem = work_page.locator("[data-testid='voucherPopup-header-popupTitleWrapper'] h4").first
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
                    "title": current_title,
                    "affiliate_link": affiliate_link
                })
            
            # 3. Fermer la popup avec CloseIcon
            try:
                close_icon = work_page.locator("[data-testid='CloseIcon']").first
                if close_icon.count() > 0:
                    close_icon.click(timeout=3000)
                    work_page.wait_for_timeout(1500)
            except:
                pass
            
            # 4. Chercher le prochain bouton sur work_page
            next_buttons = work_page.locator(code_selector)
            next_count = next_buttons.count()
            
            # Index = iteration + 1 (on a déjà traité iteration boutons)
            next_index = iteration + 1
            
            if next_index >= next_count:
                break
            
            # 5. Cliquer sur le prochain bouton → ouvre nouvel onglet → switch
            next_btn = next_buttons.nth(next_index)
            next_btn.scroll_into_view_if_needed()
            work_page.wait_for_timeout(500)
            
            pages_before = len(context.pages)
            work_page.evaluate("(el) => el.click()", next_btn.element_handle())
            work_page.wait_for_timeout(2000)
            
            # Switch vers le nouvel onglet
            if len(context.pages) > pages_before:
                work_page = context.pages[-1]
        
    except PlaywrightTimeout:
        pass
    except Exception as e:
        print(f"[MyDealz] Erreur: {str(e)[:50]}")
    
    return results, affiliate_link


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
        page = context.new_page()
        
        for idx, (merchant_row, url) in enumerate(competitor_data, 1):
            merchant_slug = merchant_row.get('Merchant_slug', 'Unknown')
            
            print(f"\n[{idx}/{len(competitor_data)}] 🏪 {merchant_slug}")
            print(f"   URL: {url[:60]}...")
            
            try:
                codes, affiliate_link = scrape_mydealz_all(page, context, url)
                print(f"   ✅ {len(codes)} codes trouvés")
                if affiliate_link:
                    print(f"   🔗 Affiliate: {affiliate_link[:50]}...")

                for code_info in codes:
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "DE",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "mydealz",
                        "Competitor_URL": url,
                        "Affiliate_Link": code_info.get("affiliate_link", ""),
                        "Code": code_info["code"],
                        "Title": code_info["title"]
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
