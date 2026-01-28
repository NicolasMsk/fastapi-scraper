"""
Test script pour codice-sconto.net (Italie) - Test sur une seule URL
"""

from playwright.sync_api import sync_playwright
import time

# URL de test
TEST_URL = "https://asos.codice-sconto.net/"

def test_codicescontonet_single():
    start_time = time.time()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        print(f"[TEST] Navigation vers {TEST_URL}")
        page.goto(TEST_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        print("[TEST] Page chargée")
        
        # Accepter cookies (plusieurs sélecteurs possibles)
        try:
            # Essayer click direct comme dans le ALL
            page.click("button:has-text('Accetta'), button:has-text('Accept'), button:has-text('OK'), button:has-text('Accetto'), #onetrust-accept-btn-handler, .fc-cta-consent", timeout=3000)
            page.wait_for_timeout(500)
            print("[TEST] Cookies acceptés")
        except:
            print("[TEST] Pas de bannière cookies ou déjà acceptée")
        
        # Trouver les boutons "Vedi il codice"
        see_code_buttons = page.locator("a._code_btn")
        total_count = see_code_buttons.count()
        print(f"[TEST] Boutons 'Vedi il codice' trouvés: {total_count}")
        
        if total_count == 0:
            see_code_buttons = page.locator("xpath=//a[.//p[contains(text(), 'Vedi il codice')]]")
            total_count = see_code_buttons.count()
            print(f"[TEST] Fallback XPath: {total_count}")
        
        if total_count == 0:
            print("[TEST] ❌ Aucun bouton trouvé!")
            browser.close()
            return []
        
        # Filtrer les offres expirées
        valid_buttons_count = page.evaluate("""() => {
            const expiredHeaders = document.querySelectorAll('h3');
            let expiredSection = null;
            for (const h of expiredHeaders) {
                if (h.textContent.includes('Offerte scadute')) {
                    expiredSection = h;
                    break;
                }
            }
            if (!expiredSection) {
                return document.querySelectorAll('a._code_btn').length;
            }
            const allButtons = document.querySelectorAll('a._code_btn');
            let count = 0;
            for (const btn of allButtons) {
                if (expiredSection.compareDocumentPosition(btn) & Node.DOCUMENT_POSITION_PRECEDING) {
                    count++;
                }
            }
            return count;
        }""")
        
        if valid_buttons_count < total_count:
            print(f"[TEST] ⚠️ {total_count - valid_buttons_count} offres expirées ignorées")
            total_count = valid_buttons_count
        
        print(f"[TEST] {total_count} codes valides à scraper")

        results = []
        affiliate_link = None
        processed_codes = set()
        processed_titles = set()
        max_codes = 5
        
        # Premier clic
        first_btn = see_code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        
        pages_before = len(context.pages)
        page.evaluate("(el) => el.click()", first_btn.element_handle())
        page.wait_for_timeout(1500)
        
        if len(context.pages) <= pages_before:
            print("[TEST] ❌ Aucun nouvel onglet ouvert")
            browser.close()
            return []
        
        new_page = context.pages[-1]
        print("[TEST] Nouvel onglet ouvert")
        new_page.wait_for_timeout(1500)

        # CAPTURE DU LIEN AFFILIÉ - La page ORIGINALE se redirige vers le marchand
        try:
            for _ in range(10):
                current_url = page.url
                if "codice-sconto" not in current_url.lower():
                    affiliate_link = current_url
                    print(f"[TEST] Lien affilié capturé: {affiliate_link[:60]}...")
                    break
                page.wait_for_timeout(500)
        except Exception as e:
            print(f"[TEST] ⚠️ Erreur capture affiliate: {str(e)[:40]}")

        # Boucle d'extraction
        for iteration in range(min(max_codes, total_count)):
            print(f"\n[TEST] ========== ITERATION {iteration + 1} ==========")
            
            new_page.wait_for_timeout(1500)
            
            # 1. Récupérer le code
            code = None
            try:
                code_elems = new_page.locator("div.undefined.codicescontonet")
                for i in range(code_elems.count()):
                    text = code_elems.nth(i).inner_text().strip()
                    if text and 3 <= len(text) <= 25 and ' ' not in text:
                        code = text
                        print(f"[TEST] Code trouvé: {code}")
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
                            print(f"[TEST] Code via span: {code}")
                            break
                except:
                    pass
            
            # 2. Récupérer le titre
            current_title = None
            try:
                title_elem = new_page.locator("p.codice-scontonet_X1fs7j").first
                if title_elem.count() > 0:
                    current_title = title_elem.inner_text().strip()
                    print(f"[TEST] Titre: {current_title[:50]}...")
            except:
                pass
            
            # Valider et ajouter
            if code and current_title and code not in processed_codes and current_title not in processed_titles:
                processed_codes.add(code)
                processed_titles.add(current_title)
                results.append({"code": code, "title": current_title, "affiliate_link": affiliate_link})
                print(f"[TEST] ✅ AJOUTÉ: {code}")
            else:
                print(f"[TEST] ⚠️ NON AJOUTÉ")
            
            # 3. Fermer la popup
            try:
                close_icon = new_page.locator("div.cd_close").first
                if close_icon.count() > 0:
                    close_icon.click(timeout=3000)
                    print("[TEST] Popup fermée")
                    new_page.wait_for_timeout(500)
            except:
                pass
            
            # 4. Chercher le bouton suivant (limiter aux non-expirés)
            new_page.wait_for_timeout(300)
            
            next_buttons = new_page.locator("a._code_btn")
            next_count = next_buttons.count()
            
            current_index = iteration + 1
            print(f"[TEST] Index suivant: {current_index}, total: {min(next_count, total_count)}")
            
            if current_index >= min(next_count, total_count):
                print("[TEST] Plus de boutons disponibles, FIN")
                break
            
            # 5. Cliquer sur le bouton suivant
            next_btn = next_buttons.nth(current_index)
            try:
                next_btn.scroll_into_view_if_needed()
                new_page.wait_for_timeout(200)
                
                pages_before = len(context.pages)
                new_page.evaluate("(el) => el.click()", next_btn.element_handle())
                new_page.wait_for_timeout(1500)
                
                if len(context.pages) > pages_before:
                    new_page = context.pages[-1]
                    print(f"[TEST] Switch vers nouvel onglet")
                    new_page.wait_for_timeout(800)
                    
            except Exception as e:
                print(f"[TEST] ❌ Erreur: {str(e)[:50]}")
                break
        
        # Fermer les onglets
        for p in context.pages[1:]:
            try:
                p.close()
            except:
                pass
        
        browser.close()
        
        elapsed = time.time() - start_time
        print(f"\n[TEST] ✅ Terminé en {elapsed:.1f}s - {len(results)} codes extraits")
        
        return results


if __name__ == "__main__":
    codes = test_codicescontonet_single()
    print("\n--- RÉSULTATS ---")
    if codes:
        print(f"Affiliate Link: {codes[0].get('affiliate_link', 'N/A')}\n")
    for i, c in enumerate(codes, 1):
        print(f"{i}. {c['code']} | {c['title'][:60]}...")
