"""
Script Playwright pour scraper TOUS les codes codice-sconto.net (Italie)
- Plus rapide et stable que Selenium
- Logique identique au script FastAPI scraper_codicescontonet.py
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_codicescontonet_all(page, context, url):
    """
    Scrape TOUS les codes d'une page codice-sconto.net avec Playwright.
    
    Logique FastAPI:
    1. Cliquer sur le premier bouton "Vedi il codice" -> nouvel onglet s'ouvre
    2. Sur le NOUVEL onglet: récupérer le code et fermer la popup
    3. Les boutons suivants sont AUSSI sur ce nouvel onglet
    4. Cliquer sur le bouton suivant -> encore un nouvel onglet
    5. Répéter
    """
    results = []
    
    try:
        print(f"[CodiceSconto] Accès à l'URL: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Accepter cookies
        try:
            page.click("button:has-text('Accetta'), button:has-text('Accept'), button:has-text('OK')", timeout=3000)
            page.wait_for_timeout(1000)
        except:
            pass
        
        # Trouver les boutons "Vedi il codice" (liens avec classe _code_btn)
        see_code_buttons = page.locator("a._code_btn")
        total_count = see_code_buttons.count()
        
        if total_count == 0:
            see_code_buttons = page.locator("xpath=//a[.//p[contains(text(), 'Vedi il codice')]]")
            total_count = see_code_buttons.count()
        
        if total_count == 0:
            print("[CodiceSconto] Aucun code disponible sur cette page")
            return results
        
        print(f"[CodiceSconto] {total_count} boutons 'Vedi il codice' trouvés au total")
        
        # === FILTRE: Exclure les offres expirées (Offerte scadute) ===
        # On utilise JavaScript pour compter combien de boutons sont AVANT la section "Offerte scadute"
        valid_buttons_count = page.evaluate("""() => {
            // Chercher le h3 "Offerte scadute"
            const expiredHeaders = document.querySelectorAll('h3');
            let expiredSection = null;
            for (const h of expiredHeaders) {
                if (h.textContent.includes('Offerte scadute')) {
                    expiredSection = h;
                    break;
                }
            }
            
            // Si pas de section expirée, tous les boutons sont valides
            if (!expiredSection) {
                return document.querySelectorAll('a._code_btn').length;
            }
            
            // Sinon, compter les boutons qui apparaissent AVANT la section
            const allButtons = document.querySelectorAll('a._code_btn');
            let count = 0;
            for (const btn of allButtons) {
                // compareDocumentPosition: 4 = btn est AVANT expiredSection
                if (expiredSection.compareDocumentPosition(btn) & Node.DOCUMENT_POSITION_PRECEDING) {
                    count++;
                }
            }
            return count;
        }""")
        
        if valid_buttons_count < total_count:
            print(f"[CodiceSconto] ⚠️ Section 'Offerte scadute' détectée - {total_count - valid_buttons_count} offres expirées ignorées")
            total_count = valid_buttons_count
        
        if total_count == 0:
            print("[CodiceSconto] Aucun code valide (non expiré) disponible sur cette page")
            return results
        
        print(f"[CodiceSconto] {total_count} codes valides (non expirés) à scraper")
        
        processed_codes = set()
        processed_titles = set()
        
        # === ÉTAPE 1: Cliquer sur le premier bouton pour ouvrir le nouvel onglet ===
        first_btn = see_code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        
        # Récupérer le titre du premier code
        first_title = None
        try:
            container = first_btn.locator("xpath=ancestor::div[contains(@class, 'codice-scontonet_MYUVPJ')]")
            first_title = container.locator("div.hidden_3").first.inner_text().strip()
        except:
            pass  # Ne pas mettre de valeur par défaut
        
        if first_title:
            print(f"[CodiceSconto] Clic sur le premier code: {first_title[:50]}...")
        else:
            print(f"[CodiceSconto] Clic sur le premier code (titre non trouvé)")
        
        # Cliquer avec JavaScript (comme FastAPI)
        pages_before = len(context.pages)
        page.evaluate("(el) => el.click()", first_btn.element_handle())
        page.wait_for_timeout(2000)
        
        # Vérifier si un nouvel onglet s'est ouvert
        if len(context.pages) <= pages_before:
            print("[CodiceSconto] Aucun nouvel onglet ouvert")
            return results
        
        # Switcher vers le nouvel onglet
        new_page = context.pages[-1]
        print("[CodiceSconto] Switché vers le nouvel onglet")
        new_page.wait_for_timeout(2000)
        
        # === ÉTAPE 2: Boucle sur le nouvel onglet ===
        max_iterations = 30
        clicked_count = 0
        
        for iteration in range(max_iterations):
            print(f"[CodiceSconto] --- Itération {iteration + 1} ---")
            
            new_page.wait_for_timeout(2000)
            
            # 1. Récupérer le code affiché dans la popup
            code = None
            try:
                code_elems = new_page.locator("div.undefined.codicescontonet")
                for i in range(code_elems.count()):
                    text = code_elems.nth(i).inner_text().strip()
                    if text and 3 <= len(text) <= 25 and ' ' not in text:
                        code = text
                        print(f"[CodiceSconto] Code trouvé: {code}")
                        break
            except:
                pass
            
            if not code:
                try:
                    code_elems = new_page.locator("span.undefined.codicescontonet")
                    for i in range(code_elems.count()):
                        text = code_elems.nth(i).inner_text().strip()
                        if text and 3 <= len(text) <= 25:
                            code = text
                            print(f"[CodiceSconto] Code trouvé via span: {code}")
                            break
                except:
                    pass
            
            # 2. Récupérer le titre de l'offre depuis la popup
            current_title = None
            try:
                title_elem = new_page.locator("p.codice-scontonet_X1fs7j").first
                if title_elem.count() > 0:
                    current_title = title_elem.inner_text().strip()
                    print(f"[CodiceSconto] Titre trouvé: {current_title[:50]}...")
            except:
                pass
            
            # N'ajouter que si code ET titre sont trouvés (pas de valeur par défaut)
            if code and current_title and code not in processed_codes and current_title not in processed_titles:
                processed_codes.add(code)
                processed_titles.add(current_title)
                results.append({
                    "success": True,
                    "code": code,
                    "title": current_title,
                    "message": "Code extrait avec succès"
                })
                print(f"[CodiceSconto] ✅ Code: {code} -> {current_title[:40]}...")
            else:
                print(f"[CodiceSconto] ⚠️ Code ou titre non trouvé, ou doublon")
            
            # 3. Fermer la popup en cliquant sur cd_close
            try:
                close_icon = new_page.locator("div.cd_close").first
                if close_icon.count() > 0:
                    close_icon.click(timeout=3000)
                    print("[CodiceSconto] Popup fermée via cd_close")
                    new_page.wait_for_timeout(1000)
            except:
                try:
                    close_btn = new_page.locator("xpath=//img[@alt='close icon']/ancestor::div[1]").first
                    if close_btn.count() > 0:
                        close_btn.click(timeout=3000)
                        print("[CodiceSconto] Popup fermée via close icon")
                        new_page.wait_for_timeout(1000)
                except:
                    pass
            
            # 4. Chercher le prochain bouton "Vedi il codice" SUR CE NOUVEL ONGLET
            new_page.wait_for_timeout(500)
            
            next_buttons = new_page.locator("a._code_btn")
            next_count = next_buttons.count()
            
            if next_count == 0:
                next_buttons = new_page.locator("xpath=//a[.//p[contains(text(), 'Vedi il codice')]]")
                next_count = next_buttons.count()
            
            clicked_count += 1
            
            # Vérifier si on a atteint la limite des codes valides (non expirés)
            if clicked_count >= total_count:
                print(f"[CodiceSconto] ✅ Tous les {total_count} codes valides ont été traités")
                break
            
            if clicked_count >= next_count:
                print("[CodiceSconto] Plus de boutons 'Vedi il codice' disponibles")
                break
            
            # 5. Cliquer sur le bouton suivant (index = clicked_count)
            next_btn = next_buttons.nth(clicked_count)
            try:
                next_btn.scroll_into_view_if_needed()
                new_page.wait_for_timeout(300)
                
                # Cliquer avec JavaScript pour ouvrir un nouvel onglet
                pages_before = len(context.pages)
                new_page.evaluate("(el) => el.click()", next_btn.element_handle())
                new_page.wait_for_timeout(2000)
                
                # Si un nouvel onglet s'est ouvert, switcher
                if len(context.pages) > pages_before:
                    old_page = new_page
                    new_page = context.pages[-1]
                    print(f"[CodiceSconto] Switché vers nouvel onglet pour code {clicked_count + 1}")
                    new_page.wait_for_timeout(1000)
                else:
                    print("[CodiceSconto] Pas de nouvel onglet détecté")
                
            except Exception as e:
                print(f"[CodiceSconto] Erreur clic suivant: {str(e)[:30]}")
                break
        
        # Fermer les onglets ouverts
        for p in context.pages[1:]:
            try:
                p.close()
            except:
                pass
        
        print(f"[CodiceSconto] Total: {len(results)} codes récupérés")
        
    except Exception as e:
        print(f"[CodiceSconto] ❌ Erreur générale: {str(e)[:50]}")
    
    return results


def main():
    """Scrape Codice-Sconto.net IT depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")
    
    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("IT", "codice-sconto")
    print(f"📍 Codicescontonet: {len(competitor_data)} URLs uniques")
    
    all_results = []
    
    # Configuration pour éviter les crashes mémoire
    PAGE_REFRESH_INTERVAL = 30  # Recréer la page tous les N merchants
    
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
            
            # Recréer la page périodiquement pour éviter les memory leaks
            if idx > 1 and (idx - 1) % PAGE_REFRESH_INTERVAL == 0:
                print(f"   🔄 Rafraîchissement de la page (prévention crash mémoire)...")
                try:
                    page.close()
                except:
                    pass
                page = context.new_page()
            
            print(f"\n[{idx}/{len(competitor_data)}] 🏪 {merchant_slug}")
            print(f"   URL: {url[:60]}...")
            
            # Tentative avec retry en cas de crash
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    codes = scrape_codicescontonet_all(page, context, url)
                    print(f"   ✅ {len(codes)} codes trouvés")
                    
                    for code_info in codes:
                        all_results.append({
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                            "Country": "IT",
                            "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                            "Merchant_slug": merchant_slug,
                            "GPN_URL": merchant_row.get("GPN_URL", ""),
                            "Competitor_Source": "codice-sconto.net",
                            "Competitor_URL": url,
                            "Code": code_info.get("code", ""),
                            "Title": code_info.get("title", "")
                        })
                    break  # Succès, sortir de la boucle retry
                    
                except Exception as e:
                    error_msg = str(e)
                    if "Page crashed" in error_msg or "Target closed" in error_msg:
                        print(f"   ⚠️ Page crash détecté, tentative {attempt + 1}/{max_retries}...")
                        try:
                            page.close()
                        except:
                            pass
                        page = context.new_page()
                        if attempt == max_retries - 1:
                            print(f"   ❌ Échec après {max_retries} tentatives")
                    else:
                        print(f"   ❌ Erreur: {error_msg[:50]}")
                        break  # Erreur non-crash, pas de retry
            
            print(f"   📝 Total: {len(all_results)} codes")
        
        browser.close()
    
    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="Codicescontonet IT")
        
        print(f"\n{'='*60}")
        print(f"✅ CODICESCONTONET IT TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")


if __name__ == "__main__":
    main()
