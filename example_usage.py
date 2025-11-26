"""
Script exemple pour utiliser les 3 endpoints de l'API de scraping
"""
import requests
import time


# URL de l'API (change cette URL si tu déploies sur Google Cloud)
API_BASE_URL = "http://localhost:8000"


def scrape_hotukdeals(title, url):
    """
    Scrape un code depuis HotUKDeals
    
    Args:
        title: Titre exact de l'offre
        url: URL de la page HotUKDeals
    
    Returns:
        Dict avec le résultat du scraping
    """
    endpoint = f"{API_BASE_URL}/scrape/hotukdeals"
    
    payload = {
        "title": title,
        "url": url
    }
    
    try:
        print(f"🔍 Scraping HotUKDeals: {title[:50]}...")
        response = requests.post(endpoint, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Code trouvé: {result['code']}")
            print(f"   ⏱️ Temps d'exécution: {result['execution_time_seconds']}s")
            return result
        else:
            print(f"   ❌ Erreur {response.status_code}: {response.json()['detail']}")
            return None
            
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None


def scrape_vouchercodes(title, url):
    """
    Scrape un code depuis VoucherCodes
    
    Args:
        title: Titre exact de l'offre
        url: URL de la page VoucherCodes
    
    Returns:
        Dict avec le résultat du scraping
    """
    endpoint = f"{API_BASE_URL}/scrape/vouchercodes"
    
    payload = {
        "title": title,
        "url": url
    }
    
    try:
        print(f"🔍 Scraping VoucherCodes: {title[:50]}...")
        response = requests.post(endpoint, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Code trouvé: {result['code']}")
            print(f"   ⏱️ Temps d'exécution: {result['execution_time_seconds']}s")
            return result
        else:
            print(f"   ❌ Erreur {response.status_code}: {response.json()['detail']}")
            return None
            
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None


def scrape_retailmenot(title, url):
    """
    Scrape un code depuis RetailMeNot
    
    Args:
        title: Titre exact de l'offre
        url: URL de la page RetailMeNot
    
    Returns:
        Dict avec le résultat du scraping
    """
    endpoint = f"{API_BASE_URL}/scrape/retailmenot"
    
    payload = {
        "title": title,
        "url": url
    }
    
    try:
        print(f"🔍 Scraping RetailMeNot: {title[:50]}...")
        response = requests.post(endpoint, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Code trouvé: {result['code']}")
            print(f"   ⏱️ Temps d'exécution: {result['execution_time_seconds']}s")
            return result
        else:
            print(f"   ❌ Erreur {response.status_code}: {response.json()['detail']}")
            return None
            
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None


def scrape_multiple_offers(offers):
    """
    Scrape plusieurs offres de différents sites
    
    Args:
        offers: Liste de dict avec {site, title, url}
    
    Returns:
        Liste des résultats
    """
    results = []
    
    for i, offer in enumerate(offers, 1):
        print(f"\n[{i}/{len(offers)}] 🛍️ {offer['site']}")
        
        if offer['site'] == 'hotukdeals':
            result = scrape_hotukdeals(offer['title'], offer['url'])
        elif offer['site'] == 'vouchercodes':
            result = scrape_vouchercodes(offer['title'], offer['url'])
        elif offer['site'] == 'retailmenot':
            result = scrape_retailmenot(offer['title'], offer['url'])
        else:
            print(f"   ⚠️ Site non supporté: {offer['site']}")
            result = None
        
        results.append({
            'site': offer['site'],
            'title': offer['title'],
            'url': offer['url'],
            'result': result
        })
        
        # Pause entre chaque scraping
        time.sleep(1)
    
    return results


if __name__ == "__main__":
    print("="*80)
    print("🚀 Démarrage du scraping de codes promo")
    print("="*80)
    
    # Exemple 1: Scraper une seule offre HotUKDeals
    print("\n📋 EXEMPLE 1: Scraper une offre HotUKDeals")
    print("-"*80)
    result = scrape_hotukdeals(
        title="Get 15% off your parking reservation using this Birmingham Airport Parking promo code",
        url="https://www.hotukdeals.com/vouchers/birminghamairport.co.uk"
    )
    
    # Exemple 2: Scraper une seule offre VoucherCodes
    print("\n📋 EXEMPLE 2: Scraper une offre VoucherCodes")
    print("-"*80)
    result = scrape_vouchercodes(
        title="5% off First Orders at Acer",
        url="https://www.vouchercodes.co.uk/uk-store.acer.com?oi=8792020"
    )
    
    # Exemple 3: Scraper une seule offre RetailMeNot
    print("\n📋 EXEMPLE 3: Scraper une offre RetailMeNot")
    print("-"*80)
    result = scrape_retailmenot(
        title="10% Off Stays",
        url="https://www.retailmenot.com/view/dusit.com"
    )
    
    # Exemple 4: Scraper plusieurs offres de différents sites
    print("\n📋 EXEMPLE 4: Scraper plusieurs offres")
    print("-"*80)
    offers = [
        {
            'site': 'hotukdeals',
            'title': 'Get 15% off your parking reservation using this Birmingham Airport Parking promo code',
            'url': 'https://www.hotukdeals.com/vouchers/birminghamairport.co.uk'
        },
        {
            'site': 'vouchercodes',
            'title': '5% off First Orders at Acer',
            'url': 'https://www.vouchercodes.co.uk/uk-store.acer.com?oi=8792020'
        },
        {
            'site': 'retailmenot',
            'title': '10% Off Stays',
            'url': 'https://www.retailmenot.com/view/dusit.com'
        }
    ]
    
    results = scrape_multiple_offers(offers)
    
    # Afficher le résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ DES RÉSULTATS")
    print("="*80)
    
    for i, item in enumerate(results, 1):
        print(f"\n[{i}] {item['site'].upper()}")
        print(f"    Titre: {item['title'][:60]}...")
        if item['result']:
            print(f"    ✅ Code: {item['result']['code']}")
            print(f"    ⏱️ Temps: {item['result']['execution_time_seconds']}s")
        else:
            print(f"    ❌ Échec du scraping")
    
    print("\n" + "="*80)
    print("✅ Scraping terminé!")
    print("="*80)
