# API de Scraping de Codes Promo

Cette API FastAPI permet de scraper des codes promo depuis HotUKDeals et VoucherCodes en fournissant simplement le titre de l'offre et l'URL de la page.

## Installation

1. Installer les dépendances :
```bash
pip install -r requirements.txt
```

2. S'assurer que Chrome et ChromeDriver sont installés et compatibles.

## Lancement de l'API

```bash
python main.py
```

Ou avec uvicorn directement :
```bash
uvicorn main:app --reload
```

L'API sera accessible sur `http://localhost:8000`

## Documentation interactive

Une fois l'API lancée, accédez à la documentation Swagger UI :
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

## Endpoints disponibles

### 1. POST `/scrape/hotukdeals`

Scrape un code promo depuis HotUKDeals.

**Body de la requête** :
```json
{
  "title": "20% Off Sitewide",
  "url": "https://www.hotukdeals.com/merchants/example-merchant"
}
```

**Réponse réussie** :
```json
{
  "success": true,
  "code": "SAVE20",
  "title": "20% Off Sitewide",
  "message": "Code trouvé avec succès",
  "execution_time_seconds": 8.45
}
```

### 2. POST `/scrape/vouchercodes`

Scrape un code promo depuis VoucherCodes.

**Body de la requête** :
```json
{
  "title": "15% Off Your First Order",
  "url": "https://www.vouchercodes.co.uk/example-merchant.html"
}
```

**Réponse réussie** :
```json
{
  "success": true,
  "code": "FIRST15",
  "title": "15% Off Your First Order",
  "message": "Code trouvé avec succès",
  "execution_time_seconds": 7.23
}
```

### 3. POST `/scrape/retailmenot`

Scrape un code promo depuis RetailMeNot (US).

**Body de la requête** :
```json
{
  "title": "20% Off Sitewide",
  "url": "https://www.retailmenot.com/view/example.com"
}
```

**Réponse réussie** :
```json
{
  "success": true,
  "code": "SAVE20",
  "title": "20% Off Sitewide",
  "message": "Code trouvé avec succès",
  "execution_time_seconds": 6.87
}
```

## Exemples d'utilisation

### Avec curl

```bash
# HotUKDeals
curl -X POST "http://localhost:8000/scrape/hotukdeals" \
  -H "Content-Type: application/json" \
  -d '{"title": "20% Off Sitewide", "url": "https://www.hotukdeals.com/merchants/example"}'

# VoucherCodes
curl -X POST "http://localhost:8000/scrape/vouchercodes" \
  -H "Content-Type: application/json" \
  -d '{"title": "15% Off", "url": "https://www.vouchercodes.co.uk/example.html"}'

# RetailMeNot
curl -X POST "http://localhost:8000/scrape/retailmenot" \
  -H "Content-Type: application/json" \
  -d '{"title": "20% Off", "url": "https://www.retailmenot.com/view/example.com"}'
```

### Avec Python (requests)

```python
import requests

# HotUKDeals
response = requests.post(
    "http://localhost:8000/scrape/hotukdeals",
    json={
        "title": "20% Off Sitewide",
        "url": "https://www.hotukdeals.com/merchants/example"
    }
)
print(response.json())

# VoucherCodes
response = requests.post(
    "http://localhost:8000/scrape/vouchercodes",
    json={
        "title": "15% Off Your First Order",
        "url": "https://www.vouchercodes.co.uk/example.html"
    }
)
print(response.json())

# RetailMeNot
response = requests.post(
    "http://localhost:8000/scrape/retailmenot",
    json={
        "title": "20% Off Sitewide",
        "url": "https://www.retailmenot.com/view/example.com"
    }
)
print(response.json())
```

## Codes d'erreur

- **400** : URL invalide ou ne correspond pas au site attendu
- **404** : Titre de l'offre non trouvé sur la page
- **500** : Erreur interne lors du scraping

## Notes

- Le scraping utilise Selenium en mode headless (sans interface graphique)
- Chaque requête lance une nouvelle instance de Chrome pour éviter les conflits
- Le navigateur se ferme automatiquement après le scraping
