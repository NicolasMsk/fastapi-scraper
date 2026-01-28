"""
Script Playwright pour scraper TOUS les codes VoucherCodes (UK)
- Plus rapide et stable que Selenium
- Extrait les URLs uniques VoucherCodes du CSV
- Récupère TOUS les codes de chaque page
"""

import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import du module gsheet_loader (dossier parent)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gsheet_loader import get_competitor_urls, load_competitors_data
from gsheet_writer import append_to_gsheet


def scrape_vouchercodes_all(page, context, url):
    """Scrape tous les codes d'une page VoucherCodes avec Playwright + lien affilié"""
    results = []
    affiliate_link = None

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        # Fermer cookie banner
        try:
            page.click("#onetrust-accept-btn-handler", timeout=3000)
            page.wait_for_timeout(500)
        except:
            pass

        # Trouver TOUS les boutons "Get Code" (on vérifiera l'exclusivité après clic)
        get_code_buttons = page.locator("button[data-qa='el:offerPrimaryButton']:has-text('Get Code')")
        count = get_code_buttons.count()

        if count == 0:
            get_code_buttons = page.locator("button:has-text('Get Code')")
            count = get_code_buttons.count()

        print(f"[VoucherCodes] {count} boutons 'Get Code' trouvés")

        if count == 0:
            return results, affiliate_link

        processed_codes = set()
        processed_titles = set()

        # Cliquer sur le premier bouton pour ouvrir le nouvel onglet
        first_btn = get_code_buttons.first
        first_btn.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        with context.expect_page() as new_page_info:
            first_btn.click()

        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded")
        new_page.wait_for_timeout(2000)

        # === CAPTURE DU LIEN AFFILIÉ ===
        # La page originale se redirige vers le site marchand
        try:
            for _ in range(10):  # Max 5 secondes
                current_url = page.url
                if "vouchercodes.co.uk" not in current_url:
                    affiliate_link = current_url
                    break
                page.wait_for_timeout(500)
        except:
            pass

        # Itérer sur tous les codes (on en a détecté 'count' au départ)
        # Pattern d'indexation: 0, 0, 1, 2, 3, ..., N-2
        for iteration in range(count):
            try:
                new_page.wait_for_timeout(1500)

                # Chercher le code dans la popup
                code = None
                title = None

                # Sélecteur principal pour VoucherCodes
                try:
                    code_elem = new_page.locator("p[data-qa='el:code']").first
                    if code_elem.count() > 0:
                        code = code_elem.inner_text().strip()
                except:
                    pass

                if not code:
                    # Fallback: chercher p.font-bold
                    try:
                        elems = new_page.locator("p.font-bold")
                        for i in range(elems.count()):
                            text = elems.nth(i).inner_text().strip()
                            if text and 3 <= len(text) <= 30:
                                code = text
                                break
                    except:
                        pass

                # Chercher le titre dans la popup
                try:
                    title_elem = new_page.locator("div[data-qa='el:offerTitle']").first
                    if title_elem.count() > 0:
                        title = title_elem.inner_text().strip()
                except:
                    pass

                # Vérifier si c'est une offre Exclusive (à ignorer)
                # On cherche le tag UNIQUEMENT dans le conteneur PARENT DIRECT du titre trouvé
                is_exclusive = False
                try:
                    if title_elem and title_elem.count() > 0:
                        # Remonter au parent du titre et chercher le tag exclusive dedans
                        parent_container = title_elem.locator("xpath=..")
                        exclusive_tag = parent_container.locator("span[data-qa='el:exclusiveTag']")
                        if exclusive_tag.count() > 0:
                            is_exclusive = True
                except:
                    pass

                # N'ajouter que si code ET titre sont trouvés ET pas Exclusive
                if code and title and not is_exclusive and code not in processed_codes and title not in processed_titles:
                    processed_codes.add(code)
                    processed_titles.add(title)
                    results.append({"code": code, "title": title, "affiliate_link": affiliate_link})
                    print(f"[VoucherCodes] ✅ Code: {code} | {title[:50]}...")
                else:
                    # Logger pourquoi le code n'est pas ajouté
                    if not code:
                        print(f"[VoucherCodes] ⚠️ Code non trouvé | Titre: {title[:50] if title else 'N/A'}...")
                    elif not title:
                        print(f"[VoucherCodes] ⚠️ Titre non trouvé (code: {code})")
                    elif is_exclusive:
                        print(f"[VoucherCodes] ⚠️ EXCLUSIVE ignorée: {code} | {title[:50]}...")
                    elif code in processed_codes:
                        print(f"[VoucherCodes] ⚠️ Code doublon: {code}")
                    elif title in processed_titles:
                        print(f"[VoucherCodes] ⚠️ Titre doublon: {title[:50]}...")

                # Fermer la popup - plusieurs sélecteurs possibles
                popup_closed = False
                close_selectors = [
                    "button.rounded-full.bg-white.absolute",
                    "button.absolute.right-0.top-0",
                    "button:has(svg[aria-label='close icon'])",
                    "button.rounded-full.bg-white:has(svg[data-qa='el:closeIcon'])",
                    "button:has(svg[data-qa='el:closeIcon'])",
                    "button.rounded-full:has(svg)",
                ]

                for selector in close_selectors:
                    try:
                        close_btn = new_page.locator(selector).first
                        if close_btn.count() > 0 and close_btn.is_visible():
                            close_btn.click()
                            new_page.wait_for_timeout(500)
                            popup_closed = True
                            break
                    except:
                        continue

                if not popup_closed:
                    try:
                        new_page.keyboard.press("Escape")
                        new_page.wait_for_timeout(500)
                    except:
                        pass

                # Si c'est la dernière itération, pas besoin de cliquer sur le prochain bouton
                if iteration == count - 1:
                    break

                # Cliquer sur le prochain bouton "Get Code"
                next_buttons = new_page.locator("button[data-qa='el:offerPrimaryButton']:has-text('Get Code')")
                if next_buttons.count() == 0:
                    next_buttons = new_page.locator("button:has-text('Get Code')")

                # S'il n'y a plus de boutons, on a terminé
                if next_buttons.count() == 0:
                    break

                # Calculer l'index: après iteration 0 → index 0, après iteration 1 → index 1, etc.
                next_index = iteration
                next_btn = next_buttons.nth(next_index)
                next_btn.scroll_into_view_if_needed()
                new_page.wait_for_timeout(300)

                # Ouvrir dans un nouvel onglet
                with context.expect_page() as next_page_info:
                    next_btn.click()

                next_new_page = next_page_info.value
                next_new_page.wait_for_load_state("domcontentloaded")

                # Fermer l'ancien onglet et utiliser le nouveau
                new_page.close()
                new_page = next_new_page

            except Exception as e:
                break

        # Fermer le dernier onglet
        try:
            new_page.close()
        except:
            pass

    except Exception as e:
        print(f"      ❌ Erreur: {str(e)[:50]}")

    return results, affiliate_link


def main():
    """Scrape VoucherCodes UK depuis Google Sheets"""
    print(f"📖 Chargement depuis Google Sheets...")
    
    # Charger les URLs depuis Google Sheets
    competitor_data = get_competitor_urls("UK", "vouchercodes")
    print(f"📍 VoucherCodes: {len(competitor_data)} URLs uniques")
    
    all_results = []
    
    print(f"\n🚀 Lancement de Playwright...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized"
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            screen={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            java_script_enabled=True,
            bypass_csp=True,
            ignore_https_errors=True,
            locale="en-GB",
            timezone_id="Europe/London"
        )

        # Script stealth pour masquer le mode headless
        context.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Override navigator.plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Override navigator.languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-GB', 'en-US', 'en']
            });

            // Override chrome runtime
            window.chrome = {
                runtime: {}
            };

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Override WebGL vendor
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter.apply(this, arguments);
            };
        """)

        page = context.new_page()
        
        for idx, (merchant_row, url) in enumerate(competitor_data, 1):
            merchant_slug = merchant_row.get('Merchant_slug', 'Unknown')
            
            print(f"\n[{idx}/{len(competitor_data)}] 🏪 {merchant_slug}")
            print(f"   URL: {url[:60]}...")
            
            # Créer une nouvelle page pour chaque marchand (la page originale se redirige)
            page = context.new_page()
            
            try:
                codes, affiliate_link = scrape_vouchercodes_all(page, context, url)
                print(f"   ✅ {len(codes)} codes trouvés")
                if affiliate_link:
                    print(f"   🔗 Affiliate: {affiliate_link[:50]}...")
                
                for code_info in codes:
                    all_results.append({
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Country": "UK",
                        "Merchant_ID": merchant_row.get("Merchant_ID", ""),
                        "Merchant_slug": merchant_slug,
                        "GPN_URL": merchant_row.get("GPN_URL", ""),
                        "Competitor_Source": "vouchercodes",
                        "Competitor_URL": url,
                        "Code": code_info["code"],
                        "Title": code_info["title"],
                        "Affiliate_Link": code_info.get("affiliate_link", "")
                    })
            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:50]}")
            
            # Fermer la page après chaque marchand
            try:
                page.close()
            except:
                pass
            
            # Fermer tous les onglets ouverts sauf le contexte
            for p in context.pages:
                try:
                    p.close()
                except:
                    pass
            
            print(f"   📝 Total: {len(all_results)} codes")
        
        browser.close()
    
    if all_results:
        # Écriture directe dans Google Sheets
        append_to_gsheet(all_results, source_name="VoucherCodes UK")
        
        print(f"\n{'='*60}")
        print(f"✅ VOUCHERCODES UK TERMINÉ!")
        print(f"📊 {len(all_results)} codes récupérés et envoyés à Google Sheets")
        print(f"{'='*60}")
    else:
        print(f"\n⚠️ Aucun code trouvé")


if __name__ == "__main__":
    main()
