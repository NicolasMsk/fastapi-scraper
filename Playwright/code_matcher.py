"""
Code Matcher - Compare les codes scrapés avec BigQuery et crée un Google Spreadsheet
- Charge les données depuis Google Sheets (Teahupoo + Missing_Code)
- Charge les données depuis BigQuery
- Identifie les nouveaux codes (non présents dans la base)
- Crée un Google Spreadsheet avec les résultats par pays

Compatible local et Google Cloud Run.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from google.oauth2.service_account import Credentials
from google.cloud import bigquery
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread

# ============================================================================
# CONFIGURATION
# ============================================================================

# Chemin des credentials - compatible local et Cloud Run
_local_path = os.path.join(os.path.dirname(__file__), "..", "credentials", "service_account.json")
_cloud_path = "/app/credentials/service_account.json"
CREDENTIALS_PATH = _cloud_path if os.path.exists(_cloud_path) else _local_path

# Scopes nécessaires
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/bigquery"
]

# BigQuery
BIGQUERY_PROJECT_ID = "prj-grp-coupons-dev-9996"

# Dossier Google Drive pour les outputs
OUTPUT_FOLDER_ID = "1w04EnXt7AVPOGsrxQGwGE9IfJmRXOerm"

# Pays à traiter
COUNTRIES = ['AU', 'PL', 'US', 'IT', 'UK', 'ES', 'FR', 'DE']


# ============================================================================
# AUTHENTIFICATION
# ============================================================================

def get_credentials():
    """Crée les credentials depuis le service account."""
    return Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)


def get_gspread_client():
    """Crée un client gspread authentifié."""
    creds = get_credentials()
    return gspread.authorize(creds)


def get_bigquery_client():
    """Crée un client BigQuery authentifié."""
    creds = get_credentials()
    return bigquery.Client(project=BIGQUERY_PROJECT_ID, credentials=creds)


# ============================================================================
# CHARGEMENT DES DONNÉES
# ============================================================================

def load_teahupoo_data(gc, date_str: str) -> pd.DataFrame:
    """
    Charge les données depuis le spreadsheet Teahupoo_{date}.

    Args:
        gc: Client gspread
        date_str: Date au format DD_MM_YYYY

    Returns:
        DataFrame avec les données BI_SEO
    """
    spreadsheet_name = f"Teahupoo_{date_str}"
    print(f"\n{'='*60}")
    print(f"📊 CHARGEMENT TEAHUPOO")
    print(f"{'='*60}")
    print(f"🔍 Recherche de: {spreadsheet_name}")

    try:
        spreadsheet = gc.open(spreadsheet_name)
        print(f"✅ Fichier trouvé!")

        dfs = []
        for country in COUNTRIES:
            try:
                sheet_name = f"GRPN_{country}"
                worksheet = spreadsheet.worksheet(sheet_name)
                df_country = pd.DataFrame(worksheet.get_all_records())
                dfs.append(df_country)
                print(f"   - {sheet_name}: {len(df_country)} lignes")
            except gspread.WorksheetNotFound:
                print(f"   - {sheet_name}: ⚠️ Non trouvé")

        if dfs:
            final_df = pd.concat(dfs, ignore_index=True)
            print(f"\n🎉 Total: {len(final_df)} lignes chargées depuis Teahupoo")
            return final_df
        else:
            print("⚠️ Aucune donnée trouvée")
            return pd.DataFrame()

    except gspread.SpreadsheetNotFound:
        print(f"❌ Fichier '{spreadsheet_name}' non trouvé!")
        return pd.DataFrame()


def load_missing_code_data(gc, date_iso: str) -> pd.DataFrame:
    """
    Charge les données depuis DB_Missing_Code, filtrées par date.

    Args:
        gc: Client gspread
        date_iso: Date au format YYYY-MM-DD

    Returns:
        DataFrame avec les codes scrapés du jour
    """
    print(f"\n{'='*60}")
    print(f"📊 CHARGEMENT MISSING_CODE")
    print(f"{'='*60}")

    spreadsheet_name = "DB_Missing_Code"
    print(f"🔍 Ouverture de: {spreadsheet_name}")

    try:
        spreadsheet = gc.open(spreadsheet_name)
        print(f"✅ Fichier trouvé!")

        worksheet = spreadsheet.worksheet("Missing_Code")
        df = pd.DataFrame(worksheet.get_all_records())

        print(f"   - Total lignes: {len(df)}")

        # Filtrer par date
        df_filtered = df[df["Date"] == date_iso]
        print(f"   - Lignes du {date_iso}: {len(df_filtered)}")

        return df_filtered

    except gspread.SpreadsheetNotFound:
        print(f"❌ Fichier '{spreadsheet_name}' non trouvé!")
        return pd.DataFrame()


def load_bigquery_data(client) -> pd.DataFrame:
    """
    Charge les données de coupons depuis BigQuery.

    Args:
        client: Client BigQuery

    Returns:
        DataFrame avec les offres actives
    """
    print(f"\n{'='*60}")
    print(f"📊 CHARGEMENT BIGQUERY")
    print(f"{'='*60}")

    query = """
    WITH fact_offer_metrics AS (
      SELECT
        offer_merchant_domain_key
        ,SUM(fof.clicks) AS clicks
        ,SUM(fof.transactions) AS transactions
        ,SUM(fof.current_transaction_value) AS current_transaction_value
        ,SUM(fof.current_commission) AS current_commission
      FROM `edw.fact_offer` AS fof
      WHERE fof.date_key BETWEEN CAST(FORMAT_DATE("%Y%m%d", DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)) AS INT64) AND CAST(FORMAT_DATE("%Y%m%d", CURRENT_DATE()) AS INT64)
      GROUP BY 1
    )
    SELECT
        dme.cc_merchant_id
        ,ddo.domain
        ,dof.cc_offer_id AS offer_id
        ,dot.offer_title AS offer_title
        ,vcof.offer_code
        ,src_date_added AS offer_date_added
        ,src_last_updated AS offer_date_updated
        ,dof.offer_source AS offer_source
        ,dof.content_source AS offer_content_source
        ,dof.offer_start_date
        ,dof.offer_expiry
        ,ROW_NUMBER() OVER(
            PARTITION BY domd.merchant_domain_key
            ORDER BY src_last_updated DESC
            ) AS offer_last_updated_order
        ,fom.clicks
        ,fom.transactions
        ,fom.current_transaction_value
        ,fom.current_commission
    FROM `edw.dim_offer_merchant_domain` AS domd
    LEFT JOIN `edw.dim_offer` AS dof
        ON dof.offer_key = domd.offer_key
        AND domd.offer_merchant_domain_active = TRUE
    JOIN `stg.vc_offers` AS vcof
        ON vcof.offer_id = dof.cc_offer_id
        AND vcof.status_lookup = 1
    LEFT JOIN `edw.dim_offer_title` AS dot
        ON dot.offer_title_key = dof.offer_title_key
    LEFT JOIN `edw.dim_merchant_domain` AS dmd
      ON dmd.merchant_domain_key = domd.merchant_domain_key
    LEFT JOIN `edw.dim_merchant` AS dme
      ON dme.merchant_key = dmd.merchant_key
    LEFT JOIN `edw.dim_domain` AS ddo
      ON ddo.domain_key = dmd.domain_key
    LEFT JOIN fact_offer_metrics AS fom
      ON fom.offer_merchant_domain_key = domd.offer_merchant_domain_key
    WHERE CAST(dof.offer_start_date AS DATE) <= CURRENT_DATE()
        AND (CAST(dof.offer_expiry AS DATE) >= CURRENT_DATE() OR dof.offer_expiry IS NULL)
        AND domd.offer_merchant_domain_active = True
    """

    print("⏳ Exécution de la requête BigQuery...")

    try:
        query_job = client.query(query)

        # Récupérer avec pagination
        rows = []
        page_size = 50000

        for i, page in enumerate(query_job.result(page_size=page_size).pages):
            batch = [dict(row) for row in page]
            rows.extend(batch)
            print(f"   📦 Batch {i+1}: {len(batch)} lignes → Total: {len(rows)}")

        df = pd.DataFrame(rows)
        print(f"\n✅ Chargement terminé: {len(df)} lignes")

        return df

    except Exception as e:
        print(f"❌ Erreur BigQuery: {str(e)}")
        return pd.DataFrame()


# ============================================================================
# MATCHING DES CODES
# ============================================================================

def match_codes(df_missing: pd.DataFrame, df_content: pd.DataFrame, df_teahupoo: pd.DataFrame) -> pd.DataFrame:
    """
    Compare les codes scrapés avec BigQuery et enrichit avec les données Teahupoo.

    Args:
        df_missing: Codes scrapés
        df_content: Données BigQuery
        df_teahupoo: Données BI_SEO (tiers, grades)

    Returns:
        DataFrame des nouveaux codes (non présents dans la base)
    """
    print(f"\n{'='*60}")
    print(f"🔧 MATCHING DES CODES")
    print(f"{'='*60}")

    if df_missing.empty:
        print("⚠️ Aucun code scrapé à traiter")
        return pd.DataFrame()

    # Enrichir avec les données Teahupoo
    if not df_teahupoo.empty and 'cc_merchant_id' in df_teahupoo.columns:
        tier_dict = dict(zip(df_teahupoo['cc_merchant_id'], df_teahupoo.get('merchant_tier', '')))
        seo_grade_dict = dict(zip(df_teahupoo['cc_merchant_id'], df_teahupoo.get('SEOGrade', '')))

        df_missing['Merchant_tier'] = df_missing['Merchant_ID'].map(tier_dict)
        df_missing['SEO_grade'] = df_missing['Merchant_ID'].map(seo_grade_dict)
        print(f"✅ Données Teahupoo ajoutées (Tier, SEO Grade)")

    # Filtrer BigQuery pour ne garder que les codes réels
    print(f"\n📊 Données BigQuery:")
    print(f"   - Total lignes: {len(df_content)}")

    if df_content.empty:
        print("⚠️ Pas de données BigQuery - tous les codes sont considérés comme nouveaux")
        return df_missing

    df_content_filtered = df_content[
        (df_content['offer_code'].notna()) &
        (df_content['offer_code'].astype(str).str.strip() != '') &
        (df_content['offer_code'].astype(str).str.strip().str.upper() != 'NONE') &
        (df_content['offer_code'].astype(str).str.strip().str.upper() != 'NAN')
    ].copy()

    print(f"   - Lignes avec codes réels: {len(df_content_filtered)}")

    # Nettoyer pour le matching
    df_missing['Code_clean'] = df_missing['Code'].astype(str).str.strip().str.upper()
    df_missing['Merchant_ID_clean'] = df_missing['Merchant_ID'].astype(str).str.strip()

    df_content_filtered['offer_code_clean'] = df_content_filtered['offer_code'].astype(str).str.strip().str.upper()
    df_content_filtered['cc_merchant_id_clean'] = df_content_filtered['cc_merchant_id'].astype(str).str.strip()

    # Créer les clés de matching
    df_missing['matching_key'] = df_missing['Merchant_ID_clean'] + '|' + df_missing['Code_clean']
    df_content_filtered['matching_key'] = df_content_filtered['cc_merchant_id_clean'] + '|' + df_content_filtered['offer_code_clean']

    # Set des codes existants
    codes_existants = set(df_content_filtered['matching_key'].unique())

    print(f"\n🔍 Matching:")
    print(f"   - Codes uniques BigQuery: {len(codes_existants)}")
    print(f"   - Codes uniques scrapés: {df_missing['matching_key'].nunique()}")

    # Identifier les nouveaux codes
    df_missing['existe_dans_base'] = df_missing['matching_key'].isin(codes_existants)

    df_existants = df_missing[df_missing['existe_dans_base']]
    df_nouveaux = df_missing[~df_missing['existe_dans_base']].copy()

    # Statistiques
    print(f"\n📊 RÉSULTATS:")
    print(f"   📥 Total scrapés: {len(df_missing)}")
    print(f"   ✅ Déjà dans la base: {len(df_existants)} ({len(df_existants)/len(df_missing)*100:.1f}%)")
    print(f"   🆕 Nouveaux codes: {len(df_nouveaux)} ({len(df_nouveaux)/len(df_missing)*100:.1f}%)")

    # Répartition par pays
    print(f"\n📍 Nouveaux codes par pays:")
    for country in sorted(df_nouveaux['Country'].dropna().unique()):
        count = len(df_nouveaux[df_nouveaux['Country'] == country])
        print(f"   - {country}: {count}")

    # Répartition par source
    print(f"\n🔗 Nouveaux codes par source:")
    for source in sorted(df_nouveaux['Competitor_Source'].dropna().unique()):
        count = len(df_nouveaux[df_nouveaux['Competitor_Source'] == source])
        print(f"   - {source}: {count}")

    # Nettoyer les colonnes temporaires
    cols_to_drop = ['Code_clean', 'Merchant_ID_clean', 'matching_key', 'existe_dans_base']
    df_final = df_nouveaux.drop(columns=[c for c in cols_to_drop if c in df_nouveaux.columns])

    return df_final


# ============================================================================
# CRÉATION DU GOOGLE SPREADSHEET
# ============================================================================

def create_output_spreadsheet(gc, df: pd.DataFrame, date_str: str) -> str:
    """
    Crée un Google Spreadsheet avec les résultats par pays.
    Utilise gspread.create() comme Teahupoo.

    Args:
        gc: Client gspread
        df: DataFrame des nouveaux codes
        date_str: Date au format DD_MM_YYYY

    Returns:
        URL du spreadsheet créé
    """
    print(f"\n{'='*60}")
    print(f"📝 CRÉATION DU GOOGLE SPREADSHEET")
    print(f"{'='*60}")

    spreadsheet_name = f"Missing_Deals_Coupons_{date_str}"
    print(f"📄 Nom: {spreadsheet_name}")

    # Créer le spreadsheet dans le dossier partagé (comme Teahupoo)
    spreadsheet = gc.create(spreadsheet_name, folder_id=OUTPUT_FOLDER_ID)
    print(f"✅ Spreadsheet créé")

    # Colonnes à exclure
    cols_to_exclude = ['Affiliate_link', 'Redirections']

    # Colonnes à insérer après Merchant_ID
    insert_after_merchant_id = ['Merchant_tier', 'SEO_grade']

    # Construire l'ordre des colonnes
    base_cols = [c for c in df.columns if c not in insert_after_merchant_id and c not in cols_to_exclude]
    columns = []
    for col in base_cols:
        columns.append(col)
        if col == 'Merchant_ID':
            # Insérer Merchant_tier et SEO_grade juste après Merchant_ID
            for insert_col in insert_after_merchant_id:
                if insert_col in df.columns:
                    columns.append(insert_col)

    # Créer la sheet Feedback (vide avec les colonnes)
    print(f"\n📋 Création des sheets:")
    feedback_sheet = spreadsheet.add_worksheet(title="Feedback", rows=1, cols=len(columns))
    feedback_sheet.append_row(columns)
    print(f"   ✅ Feedback (vide)")

    # Créer une sheet par pays
    countries = df['Country'].dropna().unique()
    total_codes = 0

    for country in sorted(countries):
        df_country = df[df['Country'] == country].copy()

        # Supprimer les doublons: un seul code par marchand (case-insensitive)
        df_country['_code_upper'] = df_country['Code'].astype(str).str.strip().str.upper()
        df_country = df_country.drop_duplicates(subset=['Merchant_slug', '_code_upper'], keep='first')
        df_country = df_country.drop(columns=['_code_upper'])
        df_country = df_country.sort_values('Merchant_slug')

        # Réorganiser les colonnes selon l'ordre défini
        df_country = df_country[[c for c in columns if c in df_country.columns]]

        # Créer la sheet
        sheet_name = str(country)[:31]
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=len(df_country)+1, cols=len(columns))

        # Écrire les données
        data = [columns] + df_country.fillna('').values.tolist()
        worksheet.update(values=data, range_name='A1')

        # Formater la colonne Code avec fond rouge
        if 'Code' in columns:
            code_col_index = columns.index('Code')
            col_letter = chr(ord('A') + code_col_index)
            # Format: fond rouge clair pour toute la colonne Code
            worksheet.format(f"{col_letter}:{col_letter}", {
                "backgroundColor": {"red": 1.0, "green": 0.8, "blue": 0.8}
            })

        total_codes += len(df_country)
        print(f"   ✅ {country}: {len(df_country)} codes")

    # Supprimer la sheet par défaut (Sheet1)
    try:
        spreadsheet.del_worksheet(spreadsheet.sheet1)
    except:
        pass

    spreadsheet_url = spreadsheet.url

    print(f"\n{'='*60}")
    print(f"🎉 RÉSUMÉ FINAL")
    print(f"{'='*60}")
    print(f"📊 Total codes: {total_codes}")
    print(f"📋 Sheets créées: Feedback + {len(countries)} pays")
    print(f"🔗 URL: {spreadsheet_url}")
    print(f"{'='*60}")

    return spreadsheet_url


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def main(manual_date: str = None):
    """
    Fonction principale - exécute le matching et crée le spreadsheet.

    Args:
        manual_date: Date manuelle au format YYYY-MM-DD (optionnel)
    """
    print("=" * 80)
    print("🚀 CODE MATCHER - DÉMARRAGE")
    print("=" * 80)

    # Déterminer les dates
    if manual_date:
        # Format ISO pour filtrage
        date_iso = manual_date  # YYYY-MM-DD
        dt = datetime.strptime(manual_date, "%Y-%m-%d")
        date_teahupoo = dt.strftime("%d_%m_%Y")  # DD_MM_YYYY pour Teahupoo
        date_output = dt.strftime("%m_%d_%Y")    # MM_DD_YYYY pour output (comme code_analyzer)
    else:
        now = datetime.now()
        date_iso = now.strftime("%Y-%m-%d")
        date_teahupoo = now.strftime("%d_%m_%Y")  # DD_MM_YYYY pour Teahupoo
        date_output = now.strftime("%m_%d_%Y")    # MM_DD_YYYY pour output

    print(f"📅 Date ISO (filtrage): {date_iso}")
    print(f"📅 Date Teahupoo: {date_teahupoo}")
    print(f"📅 Date Output: {date_output}")

    # Initialiser les clients
    print(f"\n🔐 Authentification...")
    creds = get_credentials()
    gc = gspread.authorize(creds)
    bq_client = bigquery.Client(project=BIGQUERY_PROJECT_ID, credentials=creds)
    print(f"✅ Clients initialisés")

    # Charger les données
    df_teahupoo = load_teahupoo_data(gc, date_teahupoo)
    df_missing = load_missing_code_data(gc, date_iso)
    df_content = load_bigquery_data(bq_client)

    if df_missing.empty:
        print("\n⚠️ Aucun code scrapé trouvé pour cette date. Arrêt.")
        return None

    # Matcher les codes
    df_nouveaux = match_codes(df_missing, df_content, df_teahupoo)

    if df_nouveaux.empty:
        print("\n⚠️ Aucun nouveau code trouvé. Arrêt.")
        return None

    # Créer le Google Spreadsheet avec les résultats
    url = create_output_spreadsheet(gc, df_nouveaux, date_output)

    return url


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    import sys

    # Permettre de passer une date en argument
    if len(sys.argv) > 1:
        manual_date = sys.argv[1]  # Format attendu: YYYY-MM-DD
        print(f"📌 Date manuelle: {manual_date}")
    else:
        manual_date = None

    main(manual_date)
