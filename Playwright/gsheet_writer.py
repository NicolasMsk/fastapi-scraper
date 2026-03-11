"""
Module pour écrire les résultats de scraping dans Google Sheets.
Écrit directement dans la sheet Missing_Code.
Applique automatiquement le nettoyage des données (déduplication, filtres).
"""

import gspread
from google.oauth2.service_account import Credentials
import os
import re
from datetime import datetime

# Configuration
MISSING_CODE_SPREADSHEET_ID = "16wrx_aKk0FfCKlLXZMp3WKvfwQp5-d6uaJhynqDhXdc"
MISSING_CODE_SHEET_NAME = "Missing_Code"

# Chemin des credentials - compatible local et Cloud Run
# Local: ../credentials/service_account.json
# Cloud Run: /app/credentials/service_account.json
_local_path = os.path.join(os.path.dirname(__file__), "..", "credentials", "service_account.json")
_cloud_path = "/app/credentials/service_account.json"
CREDENTIALS_PATH = _cloud_path if os.path.exists(_cloud_path) else _local_path

# Scopes nécessaires pour Google Sheets (lecture ET écriture)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ===================================================================
# CONFIGURATION DES FILTRES DE NETTOYAGE
# ===================================================================

# Mots-clés "exclusive" à supprimer (tous langues)
EXCLUSIVE_KEYWORDS = [
    'exclusive', 'exclusivo', 'exclusiva', 'esclusivo', 'esclusiva', 
    'exclusif', 'exklusiv'
]

# Préfixes de codes concurrents/affiliés à supprimer
COMPETITOR_PREFIXES = [
    # France
    'POULPEO', 'IGRAAL', 'REDUC', 'MAREDUC', 'RADINS', 'EBUYCLUB', 'PROGRAM',
    # Espagne
    'CHOLLO', 'CHOLLOMETRO', 'CUPONATION', 'CUP',
    # Italie
    'CODICE', 'SCONTO',
    # UK
    'VOUCHERCODE', 'HOTUK', 'TOPCASHBACK', 'QUIDCO',
    # US
    'RETAILMENOT', 'RMN', 'SIMPLY', 'HONEY', 'RAKUTEN', 'IBOTTA', 'GROUPON',
    # Allemagne
    'MYDEALZ', 'SPARWELT', 'GUTSCHEIN',
    # Australie
    'LIFEHACKER', 'OZBARGAIN', 'SHOPBACK',
    # Génériques affiliés
    'AFFILIATE', 'AFFIL', 'PARTNER', 'CASHBACK', 'CB'
]


def clean_results(results: list) -> list:
    """
    Applique tous les filtrages et nettoyages aux résultats avant écriture.
    
    Étapes:
    1. Suppression des doublons (Country + Merchant_ID + Code)
    2. Suppression des codes avec espaces (plusieurs mots)
    3. Suppression des lignes avec "exclusive" dans le titre
    4. Suppression des codes de concurrents (préfixes affiliés)
    
    Args:
        results: Liste de dictionnaires avec les données scrappées
    
    Returns:
        Liste filtrée et nettoyée
    """
    if not results:
        return []
    
    print(f"\n🧹 Nettoyage de {len(results)} résultats...")
    
    # ÉTAPE 1: Déduplication (Country + Merchant_ID + Code)
    seen = set()
    deduped = []
    for r in results:
        key = (r.get("Country", ""), str(r.get("Merchant_ID", "")), r.get("Code", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    
    removed_dupes = len(results) - len(deduped)
    if removed_dupes > 0:
        print(f"   ✅ {removed_dupes} doublons supprimés")
    results = deduped
    
    # ÉTAPE 2: Supprimer les codes avec espaces
    before = len(results)
    results = [r for r in results if ' ' not in str(r.get("Code", ""))]
    removed_spaces = before - len(results)
    if removed_spaces > 0:
        print(f"   ✅ {removed_spaces} codes avec espaces supprimés")
    
    # ÉTAPE 3: Supprimer les lignes avec "exclusive" dans le titre
    before = len(results)
    pattern = '|'.join(EXCLUSIVE_KEYWORDS)
    results = [r for r in results if not re.search(pattern, str(r.get("Title", "")), re.IGNORECASE)]
    removed_exclusive = before - len(results)
    if removed_exclusive > 0:
        print(f"   ✅ {removed_exclusive} codes 'exclusive' supprimés")
    
    # ÉTAPE 4: Supprimer les codes concurrents (préfixes affiliés)
    before = len(results)
    prefix_pattern = '^(' + '|'.join(COMPETITOR_PREFIXES) + ')'
    results = [r for r in results if not re.match(prefix_pattern, str(r.get("Code", "")).upper())]
    removed_competitors = before - len(results)
    if removed_competitors > 0:
        print(f"   ✅ {removed_competitors} codes concurrents supprimés")
    
    total_removed = removed_dupes + removed_spaces + removed_exclusive + removed_competitors
    print(f"   📊 {len(results)} résultats après nettoyage ({total_removed} supprimés)")
    
    return results


def get_gspread_client():
    """Crée un client gspread authentifié avec le service account."""
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client


def append_to_gsheet(results: list, source_name: str = None, skip_cleaning: bool = False):
    """
    Ajoute les résultats de scraping dans la Google Sheet Missing_Code.
    Applique automatiquement le nettoyage sauf si skip_cleaning=True.

    Sheet columns (13): Date | Country | Merchant_ID | Merchant_slug | GPN_URL |
    Competitor_Source | Competitor_URL | Code | Title | Terms | Expiry Date |
    Actioned by | Comments

    Args:
        results: Liste de dictionnaires avec les données scrappées.
                 Chaque dict doit avoir: Date, Country, Merchant_ID, Merchant_slug,
                 GPN_URL, Competitor_Source, Competitor_URL, Code, Title
        source_name: Nom de la source pour le logging (optionnel)
        skip_cleaning: Si True, n'applique pas le nettoyage (défaut: False)

    Returns:
        int: Nombre de lignes ajoutées
    """
    if not results:
        print(f"⚠️ Aucun résultat à écrire dans Google Sheets")
        return 0

    # Appliquer le nettoyage
    if not skip_cleaning:
        results = clean_results(results)

    if not results:
        print(f"⚠️ Aucun résultat après nettoyage")
        return 0

    print(f"\n📤 Écriture de {len(results)} résultats dans Google Sheets...")

    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(MISSING_CODE_SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(MISSING_CODE_SHEET_NAME)

        # Préparer les lignes à ajouter (13 colonnes matching sheet headers)
        rows_to_add = []
        for result in results:
            row = [
                result.get("Date", datetime.now().strftime("%Y-%m-%d")),
                result.get("Country", ""),
                result.get("Merchant_ID", ""),
                result.get("Merchant_slug", ""),
                result.get("GPN_URL", ""),
                result.get("Competitor_Source", ""),
                result.get("Competitor_URL", ""),
                result.get("Code", ""),
                result.get("Title", ""),
                result.get("Terms", result.get("terms", "")),
                result.get("Expiry Date", result.get("expiration_date", "")),
                "",  # Actioned by
                ""   # Comments
            ]
            rows_to_add.append(row)
        
        # Ajouter toutes les lignes d'un coup (plus efficace)
        worksheet.append_rows(rows_to_add, value_input_option="USER_ENTERED")
        
        source_info = f" ({source_name})" if source_name else ""
        print(f"✅ {len(rows_to_add)} lignes ajoutées à Google Sheets{source_info}")
        
        return len(rows_to_add)
        
    except Exception as e:
        print(f"❌ Erreur lors de l'écriture dans Google Sheets: {e}")
        raise


def clear_sheet_data():
    """
    Efface toutes les données de la sheet (garde les en-têtes).
    À utiliser avec précaution !
    """
    print("⚠️ Effacement des données de la sheet Missing_Code...")
    
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MISSING_CODE_SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(MISSING_CODE_SHEET_NAME)
    
    # Garder la première ligne (en-têtes) et effacer le reste
    worksheet.delete_rows(2, worksheet.row_count)
    
    print("✅ Données effacées (en-têtes conservés)")


def get_existing_codes(country: str = None, date: str = None):
    """
    Récupère les codes déjà présents dans la sheet pour éviter les doublons.
    
    Args:
        country: Filtrer par pays (optionnel)
        date: Filtrer par date (optionnel)
    
    Returns:
        set: Ensemble de tuples (Merchant_ID, Code) déjà présents
    """
    client = get_gspread_client()
    spreadsheet = client.open_by_key(MISSING_CODE_SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(MISSING_CODE_SHEET_NAME)
    
    records = worksheet.get_all_records()
    
    existing_codes = set()
    for record in records:
        if country and record.get("Country", "") != country:
            continue
        if date and record.get("Date", "") != date:
            continue
        
        merchant_id = record.get("Merchant_ID", "")
        code = record.get("Code", "")
        if merchant_id and code:
            existing_codes.add((str(merchant_id), str(code)))
    
    return existing_codes


def append_unique_results(results: list, source_name: str = None):
    """
    Ajoute uniquement les résultats qui ne sont pas déjà dans la sheet.
    Vérifie les doublons par (Merchant_ID, Code).
    
    Args:
        results: Liste de dictionnaires avec les données scrappées
        source_name: Nom de la source pour le logging
    
    Returns:
        int: Nombre de lignes ajoutées (après déduplication)
    """
    if not results:
        print(f"⚠️ Aucun résultat à écrire")
        return 0
    
    print(f"\n🔍 Vérification des doublons pour {len(results)} résultats...")
    
    # Récupérer les codes existants
    existing_codes = get_existing_codes()
    print(f"📊 {len(existing_codes)} codes déjà présents dans la sheet")
    
    # Filtrer les nouveaux résultats
    new_results = []
    for result in results:
        merchant_id = str(result.get("Merchant_ID", ""))
        code = str(result.get("Code", ""))
        
        if (merchant_id, code) not in existing_codes:
            new_results.append(result)
    
    duplicates_count = len(results) - len(new_results)
    if duplicates_count > 0:
        print(f"⏭️ {duplicates_count} doublons ignorés")
    
    if new_results:
        return append_to_gsheet(new_results, source_name)
    else:
        print(f"ℹ️ Aucun nouveau code à ajouter")
        return 0
