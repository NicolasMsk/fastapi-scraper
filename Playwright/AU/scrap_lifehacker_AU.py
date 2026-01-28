"""
Script Playwright pour scraper TOUS les codes Lifehacker (Australie)
- Plus rapide et stable que Selenium
- Logique identique au script FastAPI scraper_lifehacker.py
- Les codes sont directement dans le HTML (span.btn-peel__secret) - pas besoin de cliquer !
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_lifehacker_all(page, url):
    """
    Scrape TOUS les codes d'une page Lifehacker AU avec Playwright.
    
    Avantage: Les codes sont directement dans le HTML (span.btn-peel__secret)
    donc pas besoin de cliquer sur les boutons !
    
    On exclut les offres expirées (class promotion-discount-card--expired)
    """
    results = []
    
    try:
        print(f"[Lifehacker] Accès à l'URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Fermer cookie banner si présent
        try:
            page.click("button:has-text('Accept'), button:has-text('Agree'), button:has-text('OK'), #onetrust-accept-btn-handler", timeout=3000)
            page.wait_for_timeout(1000)
        except:
            pass
        
        # Trouver tous les boutons "Get Code" qui ne sont PAS dans une carte expirée
        # Les codes expirés ont la classe "promotion-discount-card--expired" sur leur parent div
        # On utilise XPath pour exclure ces cartes expirées
        code_buttons = page.locator("xpath=//div[contains(@class, 'btn-peel')][not(ancestor::div[contains(@class, 'promotion-discount-card--expired')])]")
        count = code_buttons.count()
        
        if count == 0:
            # Fallback: essayer avec le sélecteur CSS standard si XPath ne trouve rien
            code_buttons = page.locator("div.btn-peel")
            count = code_buttons.count()
            # Filtrer manuellement les expirés
            valid_buttons = []
            for i in range(count):
                btn = code_buttons.nth(i)
                try:
                    # Vérifier si le parent a la classe expired
                    parent_classes = btn.locator("xpath=ancestor::div[contains(@class, 'promotion-discount-card')]").first.get_attribute("class") or ""
                    if "expired" not in parent_classes:
                        valid_buttons.append(i)
                except:
                    valid_buttons.append(i)  # En cas d'erreur, inclure
            count = len(valid_buttons)
            print(f"[Lifehacker] {count} boutons 'Get Code' trouvés (fallback, hors expirés)")
        else:
            valid_buttons = list(range(count))
            print(f"[Lifehacker] {count} boutons 'Get Code' trouvés (hors expirés)")
        
        if count == 0:
            print("[Lifehacker] Aucun code disponible sur cette page")
            return results
        
        processed_codes = set()
        processed_titles = set()  # Éviter doublons de titres aussi
        
        # Extraire les codes directement depuis le HTML (pas besoin de cliquer!)
        for idx in valid_buttons:
            try:
                button = code_buttons.nth(idx)
                
                # Le code est dans span.btn-peel__secret
                code_elem = button.locator("span.btn-peel__secret").first
                code = None
                if code_elem.count() > 0:
                    code = code_elem.inner_text().strip()
                
                # Le titre est dans l'attribut data-promotion-title du bouton
                title = button.get_attribute("data-promotion-title")
                # Ne pas mettre de valeur par défaut si titre non trouvé
                
                # N'ajouter que si code ET titre sont trouvés (pas de valeur par défaut)
                if code and title and len(code) >= 3 and code not in processed_codes and title not in processed_titles:
                    processed_codes.add(code)
                    processed_titles.add(title)
                    results.append({
                        "success": True,
                        "code": code,
                        "title": title,
                        "message": "Code extrait avec succès"
                    })
                    print(f"[Lifehacker] ✅ Code: {code} -> {title[:50]}...")
                elif code and not title:
                    print(f"[Lifehacker] ⚠️ Titre non trouvé pour le code: {code}")
                elif code:
                    print(f"[Lifehacker] ⚠️ Code doublon ignoré: {code}")
                else:
                    print(f"[Lifehacker] ⚠️ Code invalide ou vide")
                    
            except Exception as e:
                print(f"[Lifehacker] ⚠️ Erreur extraction: {str(e)[:30]}")
        
        print(f"[Lifehacker] Total: {len(results)} codes récupérés")
        
    except Exception as e:
        print(f"[Lifehacker] ❌ Erreur générale: {str(e)[:50]}")
    
    return results


def main():
    """Scrape Lifehacker AU depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")
    
    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("AU", "lifehacker")
    print(f"📍 Lifehacker: {len(competitor_data)} URLs uniques")
    
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
                codes = scrape_lifehacker_all(page, url)
                print(f"   ✅ {len(codes)} codes trouvés")
                
                for code_info in codes:
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "AU",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "lifehacker",
                        "Competitor_URL": url,
                        "Affiliate_Link": "",
                        "Code": code_info.get("code", ""),
                        "Title": code_info.get("title", "")
                    })
            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:50]}")
            
            print(f"   📝 Total: {len(all_results)} codes")
        
        browser.close()
    
    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="Lifehacker AU")
        
        print(f"\n{'='*60}")
        print(f"✅ LIFEHACKER AU TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")


if __name__ == "__main__":
    main()
