"""
Script pour analyser les codes promo avec un LLM.
- Lit les données depuis Google Sheets (Missing_Deals_Coupons)
- Réécrit les titres selon les guidelines
- Output en JSON
"""

import gspread
from google.oauth2.service_account import Credentials
import os
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# ===================================================================
# CONFIGURATION
# ===================================================================

# Format du nom du spreadsheet avec la date du jour
SPREADSHEET_NAME_FORMAT = "Missing_Deals_Coupons_{date}"  # {date} sera remplacé par MM_DD_YYYY

# Liste des sheets pays à traiter (US exclu)
COUNTRY_SHEETS = ["UK", "AU", "DE", "ES", "FR", "IT"]

# Chemin des credentials Google Sheets
_local_path = os.path.join(os.path.dirname(__file__), "..", "credentials", "service_account.json")
_cloud_path = "/app/credentials/service_account.json"
CREDENTIALS_PATH = _cloud_path if os.path.exists(_cloud_path) else _local_path

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# OpenAI API Key (from environment variable)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# ===================================================================
# TITLE REWRITING RULES
# ===================================================================

REWRITE_RULES = """
## TITLE REWRITING RULES:

**🚫 NEVER DO:**
- Never include the merchant/brand name in the rewritten title
- Never just rephrase with similar words - create something genuinely different
- Never exceed 100 characters

**✅ ALWAYS DO:**
- Front-load the value: Put the discount/offer at the beginning
- Be specific: Include exact amounts, percentages, or product categories
- Use Title Case: Capitalize major words
- Make it scannable: Value should be instantly clear in 2-3 seconds

**REWRITING APPROACH** - Choose the best fit:
1. Action-Oriented: Create urgency with powerful verbs
2. Benefit-Driven: Focus on what the customer gets
3. Value-First: Lead with the concrete offer

**EXAMPLES:**
- ❌ "Temu - Shop Now and Save Big" → ✅ "90% Off Top Categories Today"
- ❌ "Check Out Our Latest Deals" → ✅ "20% Off New Arrivals This Week"
- ❌ "Home Depot Savings Event" → ✅ "Save $100 on Major Appliances"

If the original title already contains good value info, extract and front-load it.
If the title is vague, infer the likely offer from the code pattern and create a compelling title.
"""


# ===================================================================
# FUNCTIONS
# ===================================================================

def get_gspread_client():
    """Crée un client gspread authentifié."""
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def find_todays_spreadsheet(client):
    """
    Trouve le spreadsheet du jour dans Google Drive.
    
    Args:
        client: Client gspread authentifié
    
    Returns:
        Objet Spreadsheet ou None si non trouvé
    """
    today = datetime.now().strftime("%m_%d_%Y")  # Format: MM_DD_YYYY
    spreadsheet_name = SPREADSHEET_NAME_FORMAT.format(date=today)
    
    print(f"🔍 Recherche du spreadsheet: {spreadsheet_name}")
    
    try:
        spreadsheet = client.open(spreadsheet_name)
        print(f"   ✅ Spreadsheet trouvé: {spreadsheet.title}")
        return spreadsheet
    except gspread.SpreadsheetNotFound:
        print(f"   ❌ Spreadsheet non trouvé: {spreadsheet_name}")
        return None


def ensure_llm_columns(worksheet):
    """
    Ajoute la colonne Rewritten_Title (après Title) si elle n'existe pas.

    Args:
        worksheet: Objet worksheet gspread

    Returns:
        tuple: (title_col_index, rewritten_title_col_index)
    """
    header = worksheet.row_values(1)

    # Trouver l'index de la colonne Title
    try:
        title_idx = header.index("Title") + 1  # +1 car gspread utilise 1-based indexing
    except ValueError:
        raise ValueError("Colonne 'Title' non trouvée dans le header")

    # Vérifier et ajouter Rewritten_Title (après Title)
    rewritten_title_col = title_idx + 1
    if len(header) < rewritten_title_col or header[rewritten_title_col - 1] != "Rewritten_Title":
        print(f"   📝 Ajout de la colonne Rewritten_Title (col {rewritten_title_col})")
        worksheet.insert_cols(values=[["Rewritten_Title"]], col=rewritten_title_col)
        print(f"   ✅ Colonne ajoutée: Rewritten_Title")
    else:
        print(f"   ✅ Colonne Rewritten_Title déjà présente")

    # Re-lire le header pour être sûr d'avoir le bon indice
    header = worksheet.row_values(1)
    rewritten_title_col = header.index("Rewritten_Title") + 1

    return title_idx, rewritten_title_col


def get_missing_codes(worksheet, batch_size: int = 100):
    """
    Récupère les codes depuis une worksheet spécifique.

    Args:
        worksheet: Objet worksheet gspread
        batch_size: Nombre de lignes à récupérer par batch (défaut: 100)

    Returns:
        Liste de dictionnaires avec les données + row_index + col_indices
    """
    print(f"📥 Récupération des données de la sheet '{worksheet.title}'...")

    # S'assurer que la colonne Rewritten_Title existe
    title_idx, rewritten_title_col = ensure_llm_columns(worksheet)

    all_records = worksheet.get_all_records()

    # Filtrer uniquement ceux qui n'ont PAS encore été traités (pas de Rewritten_Title)
    unprocessed = [r for r in all_records if not r.get("Rewritten_Title")]
    print(f"   📝 {len(unprocessed)} codes non traités sur {len(all_records)} au total")

    # Prendre seulement le batch_size demandé
    batch = unprocessed[:batch_size]

    # Ajouter l'index de ligne pour pouvoir updater plus tard
    # (row_index = position dans la sheet, +2 car header + index 1-based)
    batch_with_index = []
    for record in batch:
        # Trouver l'index réel dans all_records
        try:
            original_index = all_records.index(record)
            record["_row_index"] = original_index + 2  # +2 pour header et 1-based
            record["_rewritten_col"] = rewritten_title_col
            batch_with_index.append(record)
        except ValueError:
            continue

    print(f"📊 Batch de {len(batch_with_index)} codes à traiter")
    return batch_with_index


def analyze_batch_with_llm(records: list, client: OpenAI, country: str) -> list:
    """
    Réécrit les titres d'un batch en une seule requête LLM.

    Args:
        records: Liste de dictionnaires avec les données des codes
        client: Client OpenAI
        country: Code pays (UK, US, AU, DE, ES, FR, IT) pour la langue

    Returns:
        Liste de dictionnaires avec id et rewritten_title pour chaque code

    Raises:
        Exception: Si l'API échoue (pas de fallback)
    """
    # Mapper les pays aux langues
    COUNTRY_LANGUAGES = {
        "UK": "English",
        "US": "English",
        "AU": "English",
        "DE": "German",
        "ES": "Spanish",
        "FR": "French",
        "IT": "Italian"
    }
    language = COUNTRY_LANGUAGES.get(country, "English")

    # Construire le prompt avec les données essentielles
    codes_data = []
    for idx, record in enumerate(records, 1):
        codes_data.append({
            "id": idx,
            "code": record.get("Code", ""),
            "title": record.get("Title", "")
        })

    batch_prompt = f"""Process {len(codes_data)} promo codes. For each one:

REWRITE THE TITLE in {language} following these rules:
{REWRITE_RULES}

IMPORTANT: All rewritten titles MUST be in {language}.

DATA TO PROCESS:
{json.dumps(codes_data)}

RESPOND WITH JSON ARRAY ONLY:
[{{"id":1,"rewritten_title":"...in {language}..."}},...]
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"Rewrite promo code titles in {language}. JSON array only."},
            {"role": "user", "content": batch_prompt}
        ],
        temperature=0.3,
        max_tokens=min(len(records) * 40, 16000)  # ~40 tokens par entrée, max 16000
    )

    result_text = response.choices[0].message.content.strip()

    # Nettoyer si le LLM ajoute des backticks markdown
    if result_text.startswith("```"):
        result_text = result_text.split("```")[1]
        if result_text.startswith("json"):
            result_text = result_text[4:]
    result_text = result_text.strip()

    results = json.loads(result_text)

    # Vérifier que le nombre de résultats correspond
    if len(results) != len(records):
        raise ValueError(f"Expected {len(records)} results, got {len(results)}")

    return results


def analyze_all_codes(records: list, country: str) -> list:
    """
    Réécrit les titres du batch en UNE SEULE requête LLM.

    Args:
        records: Liste des codes à traiter
        country: Code pays pour la langue (UK, DE, ES, FR, IT, etc.)

    Returns:
        Liste de résultats avec les données originales + titre réécrit
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set!")

    client = OpenAI(api_key=OPENAI_API_KEY)

    print(f"\n🤖 Traitement de {len(records)} codes avec GPT-4o-mini...")

    # Traiter tout le batch en une seule fois
    analyses = analyze_batch_with_llm(records, client, country)

    # Associer les résultats aux records originaux
    results = []
    for idx, record in enumerate(records):
        # Trouver l'analyse correspondante par ID
        analysis = next((a for a in analyses if a.get("id") == idx + 1), None)

        if analysis:
            result = {
                "original_data": record,
                "analysis": analysis
            }
            results.append(result)
            print(f"   [{idx+1}/{len(records)}] {record.get('Title', '')[:35]} → {analysis['rewritten_title'][:35]}")
        else:
            print(f"   [{idx+1}/{len(records)}] ❌ No result for code {idx+1}")

    print(f"   ✅ Batch de {len(results)} codes traités")
    return results


def update_sheet_with_results(worksheet, results: list):
    """
    Met à jour le Google Sheet avec les titres réécrits.
    Met à jour la colonne Rewritten_Title.

    Args:
        worksheet: Objet worksheet gspread
        results: Liste des résultats
    """
    print("\n📝 Mise à jour du Google Sheet...")

    # Batch update pour être plus rapide
    updates = []

    for r in results:
        row_index = r["original_data"].get("_row_index")
        rewritten_col = r["original_data"].get("_rewritten_col")

        if not row_index or not rewritten_col:
            continue

        analysis = r["analysis"]

        # Convertir les indices de colonnes en lettres (A, B, C, etc.)
        from gspread.utils import rowcol_to_a1

        # Rewritten_Title
        rewritten_cell = rowcol_to_a1(row_index, rewritten_col)
        updates.append({
            "range": rewritten_cell,
            "values": [[analysis["rewritten_title"]]]
        })

    # Faire le batch update
    if updates:
        worksheet.batch_update(updates)
        print(f"   ✅ {len(results)} lignes mises à jour dans la sheet '{worksheet.title}'")
    else:
        print("   ⚠️ Aucune ligne à mettre à jour")


def save_results_json(results: list, output_path: str = None):
    """
    Sauvegarde les résultats en JSON.

    Args:
        results: Liste des résultats d'analyse
        output_path: Chemin du fichier JSON (optionnel)

    Returns:
        Chemin du fichier créé
    """
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            os.path.dirname(__file__),
            "Output",
            f"code_analysis_{timestamp}.json"
        )

    # Créer le dossier si nécessaire
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Formater les résultats pour le JSON final
    formatted_results = []
    for r in results:
        formatted_results.append({
            "merchant_slug": r["original_data"].get("Merchant_slug"),
            "country": r["original_data"].get("Country"),
            "code": r["original_data"].get("Code"),
            "original_title": r["original_data"].get("Title"),
            "rewritten_title": r["analysis"]["rewritten_title"]
        })

    output_data = {
        "generated_at": datetime.now().isoformat(),
        "total_codes": len(formatted_results),
        "results": formatted_results
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Résultats sauvegardés: {output_path}")
    return output_path


def print_summary(results: list):
    """Affiche un résumé des résultats."""
    total = len(results)
    
    print(f"\n{'='*60}")
    print("📊 RÉSUMÉ")
    print(f"{'='*60}")
    print(f"Total titres réécrits: {total}")
    print(f"{'='*60}")


def main(batch_size: int = 100, countries: list = None):
    """
    Fonction principale - traite les codes par pays (sheet par sheet).
    
    Args:
        batch_size: Nombre de codes par batch (défaut: 100)
        countries: Liste des pays à traiter (défaut: tous les pays configurés)
    """
    print("🚀 Démarrage de l'analyse des codes promo...")
    print(f"   📦 Taille des batches: {batch_size}")
    print("")
    
    # Récupérer le client et le spreadsheet du jour
    client = get_gspread_client()
    spreadsheet = find_todays_spreadsheet(client)
    
    if not spreadsheet:
        print("❌ Impossible de trouver le spreadsheet du jour!")
        return []
    
    # Liste des pays à traiter
    target_countries = countries if countries else COUNTRY_SHEETS
    print(f"📍 Pays à traiter: {', '.join(target_countries)}\n")
    
    all_results = []
    
    # Traiter chaque pays (sheet)
    for country in target_countries:
        print(f"\n{'='*60}")
        print(f"🌍 TRAITEMENT DU PAYS: {country}")
        print(f"{'='*60}")
        
        try:
            worksheet = spreadsheet.worksheet(country)
        except gspread.WorksheetNotFound:
            print(f"   ⚠️ Sheet '{country}' non trouvée - skip")
            continue
        
        batch_num = 1
        country_results = []
        
        # Boucler sur les batches jusqu'à ce qu'il n'y ait plus de codes
        while True:
            print(f"\n📦 BATCH #{batch_num} - {country}")
            
            # 1. Récupérer le prochain batch
            records = get_missing_codes(worksheet, batch_size=batch_size)
            
            if not records:
                if batch_num == 1:
                    print(f"✅ {country} déjà complètement traité - skip")
                else:
                    print(f"✅ Tous les codes de {country} ont été traités!")
                break
            
            # 2. Réécrire les titres avec le LLM (dans la bonne langue)
            results = analyze_all_codes(records, country)
            
            # 3. Mettre à jour le sheet immédiatement
            update_sheet_with_results(worksheet, results)
            
            # 4. Ajouter aux résultats
            country_results.extend(results)
            all_results.extend(results)
            
            # 5. Afficher le résumé du batch
            print(f"\n📊 Résumé du batch #{batch_num} ({country}):")
            print(f"   ✅ {len(results)} codes analysés et mis à jour")
            
            batch_num += 1
        
        # Résumé pour ce pays
        if country_results:
            print(f"\n✅ {country}: {len(country_results)} codes traités au total")
    
    # Afficher le résumé global
    if all_results:
        print(f"\n{'='*60}")
        print(f"📊 RÉSUMÉ GLOBAL - {len(all_results)} codes traités")
        print(f"{'='*60}")
        print_summary(all_results)
        
        # Sauvegarder en JSON (backup)
        output_path = save_results_json(all_results)
        print(f"\n✅ Analyse terminée!")
        print(f"📁 Backup JSON: {output_path}")
    
    return all_results


if __name__ == "__main__":
    import sys
    
    # Arguments: python code_analyzer.py [batch_size] [countries]
    # Exemple: python code_analyzer.py 100 UK,US,FR
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    countries = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    
    main(batch_size=batch_size, countries=countries)
