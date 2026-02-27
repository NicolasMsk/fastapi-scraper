"""
Utilitaires pour capturer les liens affiliés avec toutes les redirections.
Module partagé par tous les scrapers Playwright.
"""

from urllib.parse import urlparse


def get_domain(url):
    """Extrait le domaine d'une URL (sans www.)"""
    domain = urlparse(url).netloc.lower()
    return domain[4:] if domain.startswith("www.") else domain


def capture_affiliate_link(page, source_domain, max_wait=20, redirections_list=None):
    """
    Capture le lien affilié en attendant que l'URL soit stable et différente du site source.
    Enregistre aussi toutes les redirections intermédiaires.

    Returns: URL finale ou None
    """
    last_url = None
    stable_count = 0
    if redirections_list is None:
        redirections_list = []

    for _ in range(max_wait):
        try:
            current_url = page.url
            current_domain = get_domain(current_url)

            if current_url not in redirections_list:
                redirections_list.append(current_url)
                print(f"   [REDIRECT] {current_url[:80]}...")

            if source_domain not in current_domain:
                if current_url == last_url:
                    stable_count += 1
                    if stable_count >= 3:
                        return current_url
                else:
                    stable_count = 0
                    last_url = current_url

            page.wait_for_timeout(500)
        except:
            break

    return None


def capture_with_redirections(page, source_url, wait_after_action=3000):
    """
    Capture le lien affilié ET toutes les redirections intermédiaires.
    Attache un listener pour capturer les navigations.

    Args:
        page: Page Playwright (celle qui se redirige)
        source_url: URL de départ pour identifier le domaine source
        wait_after_action: Temps d'attente après l'action (ms)

    Returns:
        dict avec 'final_url' et 'redirections' (liste) ou None
    """
    source_domain = get_domain(source_url)
    all_redirections = []

    def handle_request(request):
        if request.resource_type == "document":
            req_url = request.url
            if req_url not in all_redirections:
                all_redirections.append(req_url)
                print(f"   [NAV] {req_url[:80]}...")

    try:
        page.on("request", handle_request)
        page.wait_for_timeout(wait_after_action)

        affiliate_link = capture_affiliate_link(page, source_domain, redirections_list=all_redirections)

        if affiliate_link:
            print(f"   [INFO] {len(all_redirections)} redirections capturées")
            return {
                'final_url': affiliate_link,
                'redirections': all_redirections
            }
        return None

    except Exception as e:
        print(f"   [FAIL] Erreur capture: {str(e)[:50]}")
        return None
    finally:
        try:
            page.remove_listener("request", handle_request)
        except:
            pass


def format_redirections(redirections_list):
    """Formate la liste des redirections en string pour le spreadsheet."""
    if not redirections_list:
        return ""
    return " -> ".join(redirections_list)
