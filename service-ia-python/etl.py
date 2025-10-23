# Fichier: service-ia-python/etl.py 

import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import argparse # On importe argparse pour gérer les arguments en ligne de commande

load_dotenv()

def run_etl_for_product_line(product_line_id: str, target_table: str):
    """
    Extrait, transforme et charge les données pour une ligne de produit spécifique.

    Args:
        product_line_id (str): L'identifiant de la ligne de produit à traiter (ex: '01').
        target_table (str): Le nom de la table de destination dans Supabase (ex: 'sales').
    """
    # Connexion à la base de données (inchangée)
    db_password = os.environ.get("DB_PASSWORD")
    db_host = os.environ.get("DB_HOST")
    db_user = os.environ.get("DB_USER")
    db_name = os.environ.get("DB_NAME")
    db_port = os.environ.get("DB_PORT")
    connection_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(connection_str)

    print(f"--- DÉBUT DU PROCESSUS ETL POUR LA LIGNE PRODUIT '{product_line_id}' ---")
    
    # 1. Extraction des données brutes
    print("Extraction des données depuis 'sales_staging'...")
    try:
        df_raw = pd.read_sql("SELECT * FROM sales_staging", engine)
    except Exception as e:
        print(f"Erreur lors de la lecture de la table 'sales_staging' : {e}")
        return

    if df_raw.empty:
        print("Aucune nouvelle donnée de vente à traiter.")
        return

    # 2. Transformation
    print(f"Transformation de {len(df_raw)} lignes brutes...")
    
    # On filtre sur la ville de PARIS et la ligne de produit demandée
    df_filtered = df_raw[
        (df_raw['city'] == 'PARIS') & 
        (df_raw['product_line'] == product_line_id)
    ].copy()

    if df_filtered.empty:
        print(f"Aucune nouvelle donnée trouvée pour la ligne produit '{product_line_id}'.")
        return

    # Le reste de la transformation est identique
    df_filtered['sale_date'] = pd.to_datetime(df_filtered['sale_date'], format='%Y%m%d', errors='coerce')
    df_filtered['qty_sold'] = pd.to_numeric(df_filtered['qty_sold'], errors='coerce').fillna(0).astype(int)

    df_agg = df_filtered.groupby(['sale_date', 'category1'])['qty_sold'].sum().reset_index()
    df_agg['qty_sold'] = df_agg['qty_sold'].clip(lower=0)
    
    # L'item_id est construit de la même manière pour les deux lignes
    df_agg['item_id'] = 'category1_' + df_agg['category1'].astype(str)
    
    df_final = df_agg.rename(columns={'sale_date': 'timestamp'})
    df_sorted = df_final[['item_id', 'timestamp', 'qty_sold']].sort_values(by=['item_id', 'timestamp'])
    
    df_to_load = df_sorted.dropna()
    print(f"{len(df_to_load)} lignes propres prêtes à être chargées dans la table '{target_table}'.")

    # 3. Chargement
    if not df_to_load.empty:
        print(f"Chargement des données dans la table '{target_table}'...")
        try:
            # On utilise une table temporaire pour éviter les conflits
            df_to_load.to_sql(name='sales_temp', con=engine, if_exists='replace', index=False)
            
            with engine.connect() as conn:
                # La requête d'insertion est maintenant dynamique pour utiliser la bonne table cible
                insert_query = f"""
                    INSERT INTO {target_table} (item_id, "timestamp", qty_sold)
                    SELECT item_id, "timestamp", qty_sold FROM sales_temp
                    ON CONFLICT (item_id, "timestamp") 
                    DO UPDATE SET qty_sold = {target_table}.qty_sold + EXCLUDED.qty_sold;
                """
                conn.execute(text(insert_query))
                conn.execute(text("DROP TABLE sales_temp;"))
                conn.commit()
            
            print("✅ Chargement réussi.")
            
            # Optionnel : vider la table de staging après traitement
            # À décommenter avec prudence en production
            # with engine.connect() as conn:
            #     conn.execute(text("TRUNCATE TABLE sales_staging;"))
            #     conn.commit()
            # print("Table de staging vidée.")

        except Exception as e:
            print(f"🛑 Erreur lors du chargement des données : {e}")

    print(f"--- FIN DU PROCESSUS ETL POUR LA LIGNE PRODUIT '{product_line_id}' ---")


if __name__ == "__main__":
    # On met en place un système pour passer des arguments au script
    parser = argparse.ArgumentParser(description="ETL pour traiter les données de ventes.")
    parser.add_argument("--product_line", required=True, help="ID de la ligne produit à traiter (ex: '01' ou '02').")
    args = parser.parse_args()
    
    # On définit ici la correspondance entre l'ID et le nom de la table
    config = {
        "01": "sales",
        "02": "sales_product_line_2"
    }
    
    if args.product_line in config:
        target_table_name = config[args.product_line]
        run_etl_for_product_line(args.product_line, target_table_name)
    else:
        print(f"Erreur : Ligne produit '{args.product_line}' non reconnue. "
              f"Valeurs possibles : {list(config.keys())}")