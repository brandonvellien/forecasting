# Fichier: service-ia-python/app/historical.py (Corrigé)

import pandas as pd
from sqlalchemy import create_engine
import os
from datetime import date
from dotenv import load_dotenv
# 1. IMPORTER LA CONFIGURATION DES MODÈLES
from .config import MODELS_CONFIG

def get_historical_data(unique_id: str, start_date: date, end_date: date):
    """
    Récupère les données de ventes hebdomadaires N-1 depuis la table appropriée.
    """
    print(f"Demande de données historiques N-1 reçue pour : {unique_id}")

    # --- S'assurer que l'ID existe dans la config ---
    if unique_id not in MODELS_CONFIG:
        raise ValueError(f"L'ID de modèle '{unique_id}' n'a pas été trouvé dans la configuration.")
    
    config = MODELS_CONFIG[unique_id]
    
    # 2. UTILISER LE BON ID ET LA BONNE TABLE DEPUIS LA CONFIG
    item_id_to_fetch = config["category_id_in_file"]
    table_name = config.get("source_table", "sales") # Utilise la table de la config, ou "sales" par défaut
    
    print(f"ID de base de données : {item_id_to_fetch}")
    print(f"Utilisation de la table : {table_name}")

    # --- Connexion à la base de données ---
    db_password, db_host, db_user, db_name, db_port = (os.environ.get(k) for k in ["DB_PASSWORD", "DB_HOST", "DB_USER", "DB_NAME", "DB_PORT"])
    connection_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(connection_str)

    # --- Requête SQL avec les bonnes informations ---
    query = f"""
        SELECT "timestamp", qty_sold
        FROM {table_name}
        WHERE item_id = '{item_id_to_fetch}'
        AND "timestamp" BETWEEN ('{start_date}'::date - INTERVAL '1 year') AND ('{end_date}'::date - INTERVAL '1 year')
        ORDER BY "timestamp";
    """
    
    df_daily = pd.read_sql(query, engine, parse_dates=['timestamp'])

    if df_daily.empty:
        return None

    df_weekly = df_daily.set_index('timestamp').resample('W-MON').agg({'qty_sold': 'sum'}).reset_index()
    df_weekly['timestamp'] = df_weekly['timestamp'] + pd.DateOffset(years=1)

    return df_weekly

# --- BLOC DE TEST MIS À JOUR ---
if __name__ == "__main__":
    load_dotenv()
    
    print("--- Lancement du test pour historical.py ---")
    
    # 3. UTILISER DES DATES DE TEST VALIDES
    # On simule une prédiction en 2022 pour chercher des données en 2021
    test_unique_id = "ligne1_category1_01" 
    test_start_date = date(2022, 3, 14)   # Un lundi en 2022
    test_end_date = date(2022, 6, 6)     # 12 semaines plus tard

    print(f"Test avec ID: {test_unique_id}")
    print(f"Période de prédiction simulée: {test_start_date} à {test_end_date}")
    print(f"Le script va donc chercher des données entre {test_start_date.replace(year=test_start_date.year-1)} et {test_end_date.replace(year=test_end_date.year-1)}")

    try:
        result_df = get_historical_data(test_unique_id, test_start_date, test_end_date)
        
        if result_df is not None:
            print("\n✅ Succès ! Données N-1 récupérées et agrégées :")
            print(result_df)
        else:
            print("\n⚠️ Aucune donnée historique trouvée pour cette période.")
            
    except Exception as e:
        print(f"\n❌ Erreur pendant le test : {e}")