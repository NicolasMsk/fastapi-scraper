"""
Script Playwright pour scraper TOUS les codes iGraal (FR)
- Basé sur la logique RetailMeNot/Ma-Reduc
- Clique sur le premier code pour révéler tous les autres
- Récupère tous les codes et titres de la page via JavaScript
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_igraal_all(page, context, url):
    """
    Scrape TOUS les codes d'une page iGraal avec Playwright.
    Logique RetailMeNot : Cliquer sur un code pour révéler tous les autres,
    puis récupérer via JavaScript.
    """
    results = []

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Fermer cookie banner si présent
        try:
            page.click("button:has-text('Accepter'), button:has-text('Accept'), #onetrust-accept-btn-handler", timeout=2000)
            page.wait_for_timeout(500)
        except:
            pass
        
        # Trouver tous les boutons "Afficher le code"
        code_buttons = page.locator("button:has-text('Afficher le code')")
        count = code_buttons.count()

        if count == 0:
            return results

        # Pré-extraire terms + expiry AVANT de cliquer sur les codes
        # 1. Cliquer sur tous les boutons "Conditions" pour révéler les terms
        cond_buttons = page.locator("div.horizontalbasecard.stt-vld:not(.stt-exp) button.gpew711")
        cond_count = cond_buttons.count()
        for i in range(cond_count):
            try:
                btn = cond_buttons.nth(i)
                btn.scroll_into_view_if_needed()
                btn.click()
                page.wait_for_timeout(200)
            except:
                pass
        page.wait_for_timeout(500)

        # 2. Extraire le mapping titre -> {terms, expiry} via JS
        title_extras = page.evaluate("""() => {
            var mapping = {};
            var cards = document.querySelectorAll('div.horizontalbasecard.stt-vld:not(.stt-exp)');
            cards.forEach(function(card) {
                var titleH3 = card.querySelector('h3._1t96igp3, h3#offerbasecard-title');
                var title = titleH3 ? titleH3.textContent.trim() : '';
                if (!title) return;

                // Expiry: span contenant SVG alarm-clock
                var expiry = '';
                var spans = card.querySelectorAll('span._1fehs7y0');
                spans.forEach(function(span) {
                    if (span.querySelector('svg[aria-label="alarm-clock icon"]')) {
                        expiry = span.textContent.trim();
                    }
                });

                // Terms: div.gpew715 (révélé après clic sur Conditions)
                var terms = '';
                var termsDiv = card.querySelector('div.gpew715');
                if (termsDiv) {
                    terms = termsDiv.textContent.trim();
                }

                mapping[title] = {terms: terms, expiration_date: expiry};
            });
            return mapping;
        }""")
        if title_extras:
            print(f"      {len(title_extras)} terms/expiry pré-extraits")

        # Cliquer sur le premier bouton pour révéler les codes
        first_btn = code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        
        # Gérer le nouvel onglet potentiel
        with context.expect_page() as new_page_info:
            first_btn.click()
        
        try:
            new_page = new_page_info.value
            new_page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)

            # Vérifier si c'est une page igraal
            if "igraal" in new_page.url:
                work_page = new_page
            else:
                new_page.close()
                work_page = page
        except:
            work_page = page
        
        page.wait_for_timeout(2000)
        
        # Fermer la popup si présente
        try:
            work_page.keyboard.press("Escape")
            work_page.wait_for_timeout(1500)
        except:
            pass
        
        # Scroll de la page pour charger tous les codes
        last_height = work_page.evaluate("document.body.scrollHeight")
        while True:
            work_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            work_page.wait_for_timeout(1000)
            new_height = work_page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        work_page.evaluate("window.scrollTo(0, 0)")
        work_page.wait_for_timeout(1000)
        
        # Récupérer tous les codes via JavaScript (même logique que RetailMeNot)
        # IMPORTANT: Exclure les codes expirés (stt-vld = valide, stt-exp = expiré)
        codes_data = work_page.evaluate("""
            () => {
                var results = [];
                // Sélectionner les cartes de codes VALIDES uniquement
                // EXCLURE les expirés (stt-exp)
                var cards = document.querySelectorAll('div.horizontalbasecard.stt-vld:not(.stt-exp)');
                
                cards.forEach(function(card) {
                    // Le code est dans le bouton (après révélation)
                    var codeBtn = card.querySelector('button._1aujn430');
                    var code = null;
                    
                    if (codeBtn) {
                        var btnText = codeBtn.textContent.trim();
                        // Si le texte n'est pas "Afficher le code", c'est le code
                        if (btnText && btnText !== 'Afficher le code' && btnText !== 'Copier' && btnText.length >= 3) {
                            code = btnText;
                        }
                    }
                    
                    // Le titre est dans h3._1t96igp3
                    var titleH3 = card.querySelector('h3._1t96igp3, h3#offerbasecard-title');
                    var title = titleH3 ? titleH3.textContent.trim() : null;
                    
                    if (code && title) {
                        results.push({code: code, title: title});
                    }

                });
                
                return results;
            }
        """)
        
        # Filtrer les doublons (uniquement sur le code)
        processed_codes = set()
        
        # Fonction pour vérifier si c'est un vrai code promo (alphanumerique sans espaces)
        def is_real_code(code):
            if not code:
                return False
            # Un vrai code n'a pas d'espaces et est alphanumérique (lettres/chiffres)
            # Exclure les textes comme "Activer le cashback", "En profiter", "Acheter un bon"
            if ' ' in code:
                return False
            # Vérifier que c'est principalement alphanumérique
            return code.replace('-', '').replace('_', '').isalnum()
        
        for item in codes_data:
            code = item['code']
            title = item['title']

            # Vérifier si c'est un vrai code promo
            if not is_real_code(code):
                continue

            # Vérifier uniquement si le code est un doublon
            if code in processed_codes:
                continue

            # N'ajouter que si code ET titre sont présents
            if code and title:
                processed_codes.add(code)
                extras = title_extras.get(title, {})
                results.append({
                    "code": code,
                    "title": title,
                    "terms": extras.get("terms", ""),
                    "expiration_date": extras.get("expiration_date", "")
                })
        
        # Fermer le nouvel onglet si on en a ouvert un
        if work_page != page:
            try:
                work_page.close()
            except:
                pass
        
    except Exception as e:
        print(f"      ❌ Erreur: {str(e)[:50]}")
    
    return results


def main():
    """Scrape iGraal FR depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")
    
    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("FR", "igraal")
    print(f"📍 iGraal: {len(competitor_data)} URLs uniques")
    
    all_results = []
    
    # Configuration pour éviter les "Page crashed"
    PAGE_REFRESH_INTERVAL = 25
    
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
            
            # Recréer la page périodiquement
            if idx > 1 and (idx - 1) % PAGE_REFRESH_INTERVAL == 0:
                print(f"\n🔄 Refresh de la page (prévention memory leak)...")
                try:
                    page.close()
                except:
                    pass
                for p_tab in context.pages:
                    try:
                        p_tab.close()
                    except:
                        pass
                page = context.new_page()
            
            print(f"\n[{idx}/{len(competitor_data)}] 🏪 {merchant_slug}")
            print(f"   URL: {url[:60]}...")
            
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    codes = scrape_igraal_all(page, context, url)
                    print(f"   ✅ {len(codes)} codes trouvés")

                    for code_info in codes:
                        all_results.append({
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Country": "FR",
                            "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                            "Merchant_slug": merchant_slug,
                            "GPN_URL": merchant_row.get("GPN_URL", ""),
                            "Competitor_Source": "igraal",
                            "Competitor_URL": url,
                            "Code": code_info["code"],
                            "Title": code_info["title"],
                            "terms": code_info.get("terms", ""),
                            "expiration_date": code_info.get("expiration_date", "")
                        })
                    break
                    
                except Exception as e:
                    error_msg = str(e)
                    if "Page crashed" in error_msg or "Target closed" in error_msg:
                        print(f"   ⚠️ Page crashed (attempt {attempt + 1}/{max_retries}), recréation...")
                        try:
                            page.close()
                        except:
                            pass
                        for p_tab in context.pages:
                            try:
                                p_tab.close()
                            except:
                                pass
                        page = context.new_page()
                        if attempt == max_retries - 1:
                            print(f"   ❌ Échec après {max_retries} tentatives")
                    else:
                        print(f"   ❌ Erreur: {error_msg[:50]}")
                        break
            
            print(f"   📝 Total: {len(all_results)} codes")
        
        browser.close()
    
    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="iGraal FR")
        
        print(f"\n{'='*60}")
        print(f"✅ IGRAAL FR TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")


if __name__ == "__main__":
    main()
