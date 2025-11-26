import requests

# Test HotUKDeals avec l'exemple Birmingham Airport Parking
print("🧪 Test de l'API HotUKDeals...")
print("="*80)

response = requests.post(
    "http://localhost:8000/scrape/hotukdeals",
    json={
        "title": "Get 15% off your parking reservation using this Birmingham Airport Parking promo code",
        "url": "https://www.hotukdeals.com/vouchers/birminghamairport.co.uk"
    }
)

print(f"Status Code: {response.status_code}")
print(f"Réponse:\n{response.json()}")
print("="*80)
