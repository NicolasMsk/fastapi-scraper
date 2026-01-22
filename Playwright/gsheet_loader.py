"""
Module commun pour charger les données de compétiteurs depuis Google Sheets.
Utilise le service account pour s'authentifier.
"""

import gspread
from google.oauth2.service_account import Credentials
import os

# Configuration
SPREADSHEET_ID = "1vibqgrHkrWVBQ3DsgKJHKF_vTORmHuC9aKrObNrRpNA"
SHEET_NAME = "All_countries"

# Chemin des credentials - compatible local et Cloud Run
_local_path = os.path.join(os.path.dirname(__file__), "..", "credentials", "service_account.json")
_cloud_path = "/app/credentials/service_account.json"
CREDENTIALS_PATH = _cloud_path if os.path.exists(_cloud_path) else _local_path

# Scopes nécessaires pour Google Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]


def get_gspread_client():
    """Crée un client gspread authentifié avec le service account."""
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client


def load_competitors_data(country: str = None, competitor_source: str = None):
    """
    Charge les données de compétiteurs depuis Google Sheets.
    
    Args:
        country: Filtrer par pays (AU, DE, ES, FR, IT, UK, US)
        competitor_source: Filtrer par source (cuponation, lifehacker, mydealz, etc.)
    
    Returns:
        Liste de dictionnaires avec les données des marchands
    """
    print(f"📊 Chargement des données depuis Google Sheets...")
    
    client = get_gspread_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(SHEET_NAME)
    
    # Récupérer toutes les données
    records = worksheet.get_all_records()
    print(f"📊 {len(records)} lignes chargées depuis '{SHEET_NAME}'")
    
    # Filtrer par pays si spécifié
    if country:
        records = [r for r in records if r.get("Country", "").upper() == country.upper()]
        print(f"📊 {len(records)} lignes pour le pays {country}")
    
    return records


def get_competitor_urls(country: str, competitor_name: str):
    """
    Récupère les URLs d'un compétiteur spécifique pour un pays.
    
    Args:
        country: Code pays (AU, DE, ES, FR, IT, UK, US)
        competitor_name: Nom du compétiteur (cuponation, lifehacker, mydealz, etc.)
    
    Returns:
        Liste de tuples (merchant_row, url) avec les URLs du compétiteur
    """
    records = load_competitors_data(country=country)
    
    competitor_urls = []
    seen_urls = set()
    
    # Chercher dans les colonnes Competitor_1_URL, Competitor_2_URL, Competitor_3_URL, Competitor_4_URL
    competitor_columns = ["Competitor_1_URL", "Competitor_2_URL", "Competitor_3_URL", "Competitor_4_URL"]
    
    for row in records:
        for col in competitor_columns:
            url = row.get(col, "")
            if url and competitor_name.lower() in url.lower() and url not in seen_urls:
                seen_urls.add(url)
                competitor_urls.append((row, url))
    
    print(f"📍 {competitor_name}: {len(competitor_urls)} URLs uniques trouvées pour {country}")
    
    return competitor_urls


# Mapping des compétiteurs par pays
COMPETITORS_BY_COUNTRY = {
    "AU": ["cuponation", "lifehacker"],
    "DE": ["mydealz", "sparwelt"],
    "ES": ["chollometro", "cuponation"],
    "FR": ["igraal", "ma-reduc"],
    "IT": ["codice-sconto", "cuponation"],
    "UK": ["hotukdeals", "vouchercodes"],
    "US": ["retailmenot", "simplycodes"]
}


if __name__ == "__main__":
    # Test
    print("Test du module gsheet_loader...")
    
    # Test chargement global
    data = load_competitors_data()
    print(f"Total: {len(data)} lignes")
    
    # Test par pays
    for country in ["AU", "DE", "ES", "FR", "IT", "UK", "US"]:
        data = load_competitors_data(country=country)
        print(f"{country}: {len(data)} marchands")
    
    # Test URLs compétiteur
    urls = get_competitor_urls("AU", "cuponation")
    print(f"\nExemple URLs Cuponation AU:")
    for row, url in urls[:3]:
        print(f"  {row.get('Merchant_slug')}: {url}")
