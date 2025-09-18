# Fichier: service-ia-python/verifier_donnees.py

import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

# --- Copiez la fonction get_data_from_supabase de votre train.py ici ---
def get_data_from_supabase(item_id_to_fetch):
    print("--- Connexion à Supabase et récupération des données ---")
    db_password = os.environ.get("DB_PASSWORD")
    db_host = os.environ.get("DB_HOST")
    db_user = os.environ.get("DB_USER")
    db_name = os.environ.get("DB_NAME")
    db_port = os.environ.get("DB_PORT")
    connection_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(connection_str)
    query = f"""
    SELECT item_id, "timestamp", qty_sold
    FROM sales
    WHERE item_id = '{item_id_to_fetch}'
    ORDER BY "timestamp";
    """
    df = pd.read_sql(query, engine, parse_dates=['timestamp'])
    return df

def compare_datasets():
    """
    Compare les données de l'ancien CSV avec celles de Supabase
    après une préparation identique.
    """
    item_id = "category1_01"

    # --- 1. Préparer les données de l'ANCIEN CSV ---
    print("--- Préparation des données depuis le fichier CSV ---")
    try:
        df_csv_raw = pd.read_csv("../data/ventes_paris_ligne1_par_categorie.csv", parse_dates=['timestamp'])
        df_csv_cat = df_csv_raw[df_csv_raw['item_id'] == item_id].copy()
        df_csv_weekly = df_csv_cat.groupby('item_id').resample('W-MON', on='timestamp').sum(numeric_only=True).reset_index()
        df_csv_weekly['item_id'] = item_id # S'assurer que l'id est correct
        print(f"CSV : {len(df_csv_weekly)} lignes hebdomadaires trouvées.")
    except FileNotFoundError:
        print("Erreur : Fichier 'ventes_paris_ligne1_par_categorie.csv' non trouvé.")
        return

    # --- 2. Préparer les données de SUPABASE ---
    print("\n--- Préparation des données depuis Supabase ---")
    df_db_daily = get_data_from_supabase({"category_id_in_file": item_id})
    df_db_weekly = df_db_daily.set_index('timestamp').resample('W-MON').agg(
        {'item_id': 'first', 'qty_sold': 'sum'}
    ).reset_index()
    df_db_weekly['item_id'] = df_db_weekly['item_id'].ffill()
    df_db_weekly.dropna(subset=['item_id'], inplace=True)
    print(f"Supabase : {len(df_db_weekly)} lignes hebdomadaires trouvées.")

    # --- 3. COMPARAISON ---
    print("\n--- COMPARAISON DES DONNÉES ---")
    print(f"Nombre de lignes (CSV vs Supabase): {len(df_csv_weekly)} vs {len(df_db_weekly)}")
    print(f"Somme des ventes (CSV vs Supabase): {df_csv_weekly['qty_sold'].sum()} vs {df_db_weekly['qty_sold'].sum()}")

    print("\nPremières 5 lignes du CSV :")
    print(df_csv_weekly.head())
    
    print("\nPremières 5 lignes de Supabase :")
    print(df_db_weekly.head())

if __name__ == "__main__":
    compare_datasets()