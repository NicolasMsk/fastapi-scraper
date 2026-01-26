"""
Script pour analyser et classifier les codes promo avec un LLM.
- Lit les données depuis Google Sheets (Missing_Code)
- Classifie chaque code en 3 catégories de fiabilité
- Réécrit les titres selon les guidelines
- Output en JSON
"""

import gspread
from google.oauth2.service_account import Credentials
import os
import json
from datetime import datetime
from openai import OpenAI

# ===================================================================
# CONFIGURATION
# ===================================================================

# Format du nom du spreadsheet avec la date du jour
SPREADSHEET_NAME_FORMAT = "Missing_Deals_Coupons_{date}"  # {date} sera remplacé par MM_DD_YYYY

# Liste des sheets pays à traiter
COUNTRY_SHEETS = ["UK", "US", "AU", "DE", "ES", "FR", "IT"]

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
# LLM PROMPT
# ===================================================================

ANALYSIS_PROMPT = """You are an expert promo code analyst. Your task is to analyze coupon/promo codes and:
1. CLASSIFY the code reliability into one of 3 categories
2. REWRITE the title following strict guidelines

## INPUT DATA:
- Merchant: {merchant_slug}
- Country: {country}
- Promo Code: {code}
- Original Title: {title}
- Source: {source}

## CLASSIFICATION CATEGORIES:

Analyze the code pattern, title wording, and context to determine reliability:

**CATEGORY A - HIGH RELIABILITY** (Likely Valid):
- Generic discount codes (e.g., SAVE10, WELCOME20, FIRST15)
- Seasonal/event codes (e.g., SUMMER2024, BLACKFRIDAY, XMAS25)
- Clear percentage or dollar amounts in title
- Standard promo patterns (NEW, VIP, MEMBER, STUDENT, SENIOR)
- Codes matching common brand patterns

**CATEGORY B - MEDIUM RELIABILITY** (Possibly Valid):
- Codes with unusual patterns but plausible
- Ambiguous titles that could be real offers
- Older looking codes that might still work
- Codes with mixed signals (some good, some concerning patterns)

**CATEGORY C - LOW RELIABILITY** (Likely Invalid/Spam):
- Competitor affiliate codes (containing names like HONEY, RAKUTEN, RETAILMENOT, etc.)
- Codes that look auto-generated or random
- Titles that are vague, generic, or don't mention a specific offer
- Codes with "exclusive" partner names embedded
- Suspicious patterns (all caps random strings, very long codes)
- Titles in different language than expected for the country

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

## OUTPUT FORMAT:

Respond with ONLY a valid JSON object (no markdown, no explanation):
{{
    "category": "A" | "B" | "C",
    "category_reason": "Brief 1-sentence explanation of classification",
    "rewritten_title": "Your rewritten title here (max 100 chars)",
    "title_approach": "action" | "benefit" | "value"
}}
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
    Ajoute les colonnes LLM_Category et Rewritten_Title après la colonne Title si elles n'existent pas.
    
    Args:
        worksheet: Objet worksheet gspread
    
    Returns:
        tuple: (title_col_index, category_col_index, rewritten_title_col_index)
    """
    header = worksheet.row_values(1)
    
    # Trouver l'index de la colonne Title
    try:
        title_idx = header.index("Title") + 1  # +1 car gspread utilise 1-based indexing
    except ValueError:
        raise ValueError("Colonne 'Title' non trouvée dans le header")
    
    # Vérifier si les colonnes LLM existent déjà
    category_col = title_idx + 1
    rewritten_title_col = title_idx + 2
    
    needs_update = False
    
    if len(header) < category_col or header[category_col - 1] != "LLM_Category":
        needs_update = True
    
    if len(header) < rewritten_title_col or header[rewritten_title_col - 1] != "Rewritten_Title":
        needs_update = True
    
    if needs_update:
        print(f"   📝 Ajout des colonnes LLM après 'Title' (col {title_idx})")
        
        # Insérer 2 colonnes après Title
        worksheet.insert_cols(values=[["LLM_Category"], ["Rewritten_Title"]], col=category_col)
        
        print(f"   ✅ Colonnes ajoutées: LLM_Category (col {category_col}), Rewritten_Title (col {rewritten_title_col})")
    else:
        print(f"   ✅ Colonnes LLM déjà présentes")
    
    return title_idx, category_col, rewritten_title_col


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
    
    # S'assurer que les colonnes LLM existent
    title_idx, category_col, rewritten_title_col = ensure_llm_columns(worksheet)
    
    all_records = worksheet.get_all_records()
    
    # Filtrer uniquement ceux qui n'ont PAS encore été traités (pas de catégorie)
    unprocessed = [r for r in all_records if not r.get("LLM_Category")]
    print(f"   📝 {len(unprocessed)} codes non analysés sur {len(all_records)} au total")
    
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
            record["_category_col"] = category_col
            record["_rewritten_col"] = rewritten_title_col
            batch_with_index.append(record)
        except ValueError:
            continue
    
    print(f"📊 Batch de {len(batch_with_index)} codes à analyser")
    return batch_with_index


def get_missing_codes_OLD(batch_size: int = 100, filter_today: bool = True):
    """
    ANCIENNE VERSION - Récupère les codes depuis la sheet Missing_Code.
    Conservée pour référence uniquement.
    """
    print("⚠️ Utilisation de l'ancienne fonction - deprecated")
    return [], None


def analyze_code_with_llm(record: dict, client: OpenAI) -> dict:
    """
    Analyse un code promo avec le LLM.
    
    Args:
        record: Dictionnaire avec les données du code
        client: Client OpenAI
    
    Returns:
        Dictionnaire avec category et rewritten_title
    """
    prompt = ANALYSIS_PROMPT.format(
        merchant_slug=record.get("Merchant_slug", "Unknown"),
        country=record.get("Country", "Unknown"),
        code=record.get("Code", ""),
        title=record.get("Title", ""),
        source=record.get("Competitor_Source", "Unknown")
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a promo code analyst. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Nettoyer si le LLM ajoute des backticks markdown
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        result = json.loads(result_text)
        return result
        
    except json.JSONDecodeError as e:
        print(f"   ⚠️ JSON parse error: {e}")
        return {
            "category": "B",
            "category_reason": "Failed to parse LLM response",
            "rewritten_title": record.get("Title", "")[:100],
            "title_approach": "value"
        }
    except Exception as e:
        print(f"   ❌ LLM error: {e}")
        return None


def update_sheet_with_results(worksheet, results: list):
    """
    Met à jour le Google Sheet avec les résultats de l'analyse.
    Met à jour UNIQUEMENT les 2 colonnes LLM ajoutées après Title.
    
    Args:
        worksheet: Objet worksheet gspread
        results: Liste des résultats d'analyse
    """
    print("\n📝 Mise à jour du Google Sheet...")
    
    # Batch update pour être plus rapide
    updates = []
    
    for r in results:
        row_index = r["original_data"].get("_row_index")
        category_col = r["original_data"].get("_category_col")
        rewritten_col = r["original_data"].get("_rewritten_col")
        
        if not row_index or not category_col or not rewritten_col:
            continue
        
        analysis = r["analysis"]
        
        # Convertir les indices de colonnes en lettres (A, B, C, etc.)
        from gspread.utils import rowcol_to_a1
        
        category_cell = rowcol_to_a1(row_index, category_col)
        rewritten_cell = rowcol_to_a1(row_index, rewritten_col)
        
        updates.append({
            "range": category_cell,
            "values": [[analysis["category"]]]
        })
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


def analyze_all_codes(records: list, batch_size: int = 10) -> list:
    """
    Analyse tous les codes avec le LLM.
    
    Args:
        records: Liste des codes à analyser
        batch_size: Nombre de codes par batch (pour affichage)
    
    Returns:
        Liste de résultats avec les données originales + analyse
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set!")
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    results = []
    
    print(f"\n🤖 Analyse de {len(records)} codes avec GPT-4o-mini...")
    
    for idx, record in enumerate(records, 1):
        merchant = record.get("Merchant_slug", "Unknown")
        code = record.get("Code", "")
        
        print(f"[{idx}/{len(records)}] {merchant} - {code[:20]}...", end=" ")
        
        analysis = analyze_code_with_llm(record, client)
        
        if analysis:
            result = {
                "original_data": record,
                "analysis": analysis
            }
            results.append(result)
            print(f"→ Cat {analysis['category']}")
        else:
            print("→ ❌ Failed")
        
        # Progress indicator
        if idx % batch_size == 0:
            print(f"   📊 Progress: {idx}/{len(records)} ({idx*100//len(records)}%)")
    
    return results


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
            "category": r["analysis"]["category"],
            "category_reason": r["analysis"]["category_reason"],
            "rewritten_title": r["analysis"]["rewritten_title"],
            "title_approach": r["analysis"]["title_approach"]
        })
    
    output_data = {
        "generated_at": datetime.now().isoformat(),
        "total_codes": len(formatted_results),
        "category_counts": {
            "A": sum(1 for r in formatted_results if r["category"] == "A"),
            "B": sum(1 for r in formatted_results if r["category"] == "B"),
            "C": sum(1 for r in formatted_results if r["category"] == "C")
        },
        "results": formatted_results
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Résultats sauvegardés: {output_path}")
    return output_path


def print_summary(results: list):
    """Affiche un résumé des résultats."""
    categories = {"A": 0, "B": 0, "C": 0}
    
    for r in results:
        cat = r["analysis"]["category"]
        if cat in categories:
            categories[cat] += 1
    
    total = len(results)
    
    print(f"\n{'='*60}")
    print("📊 RÉSUMÉ DE L'ANALYSE")
    print(f"{'='*60}")
    print(f"Total codes analysés: {total}")
    print(f"")
    print(f"🟢 Catégorie A (High Reliability):   {categories['A']:4d} ({categories['A']*100//total if total else 0}%)")
    print(f"🟡 Catégorie B (Medium Reliability): {categories['B']:4d} ({categories['B']*100//total if total else 0}%)")
    print(f"🔴 Catégorie C (Low Reliability):    {categories['C']:4d} ({categories['C']*100//total if total else 0}%)")
    print(f"{'='*60}")


def main(batch_size: int = 100, countries: list = None):
    """
    Fonction principale - traite tous les pays sheet par sheet.
    
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
                print(f"✅ Tous les codes de {country} ont été analysés!")
                break
            
            # 2. Analyser avec le LLM
            results = analyze_all_codes(records)
            
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
