# Fichier: service-ia-python/etl.py (Version corrigée)

import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

def run_sales_etl():
    """
    Extrait les données de ventes brutes, applique la logique de prétraitement,
    et charge les données propres dans la table de production 'sales'.
    """
    # ... (partie connexion à la base de données inchangée)
    db_password = os.environ.get("DB_PASSWORD")
    db_host = os.environ.get("DB_HOST")
    db_user = os.environ.get("DB_USER")
    db_name = os.environ.get("DB_NAME")
    db_port = os.environ.get("DB_PORT")

    connection_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(connection_str)

    print("--- DÉBUT DU PROCESSUS ETL POUR LES VENTES ---")
    print("Extraction des données depuis 'sales_staging'...")
    try:
        df_raw = pd.read_sql("SELECT * FROM sales_staging", engine)
    except Exception as e:
        print(f"Erreur lors de la lecture de la table 'sales_staging' : {e}")
        return

    if df_raw.empty:
        print("Aucune nouvelle donnée de vente à traiter.")
        return

    print(f"Transformation de {len(df_raw)} lignes brutes...")
    
    # <<< CORRECTION ICI >>>
    # On commente le filtre, mais on crée immédiatement la copie pour pouvoir travailler dessus.
    # df_filtered = df_raw[(df_raw['city'] == 'PARIS') & (df_raw['product_line'] == '1')].copy()
    df_filtered = df_raw.copy()

    # Le reste du script peut maintenant utiliser df_filtered sans erreur
    df_filtered['sale_date'] = pd.to_datetime(df_filtered['sale_date'], format='%Y%m%d', errors='coerce')
    df_filtered['qty_sold'] = pd.to_numeric(df_filtered['qty_sold'], errors='coerce').fillna(0).astype(int)

    df_agg = df_filtered.groupby(['sale_date', 'category1'])['qty_sold'].sum().reset_index()
    df_agg['qty_sold'] = df_agg['qty_sold'].clip(lower=0)
    df_agg['item_id'] = 'category1_' + df_agg['category1'].astype(str)
    df_final = df_agg.rename(columns={'sale_date': 'timestamp'})
    df_sorted = df_final[['item_id', 'timestamp', 'qty_sold']].sort_values(by=['item_id', 'timestamp'])
    
    df_to_load = df_sorted.dropna()
    print(f"{len(df_to_load)} lignes propres prêtes à être chargées.")

    # ... (Le reste du script de chargement est identique)
    if not df_to_load.empty:
        print("Chargement des données dans la table 'sales'...")
        try:
            df_to_load.to_sql(name='sales_temp', con=engine, if_exists='replace', index=False)
            
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO sales (item_id, "timestamp", qty_sold)
                    SELECT item_id, "timestamp", qty_sold FROM sales_temp
                    ON CONFLICT (item_id, "timestamp") 
                    DO UPDATE SET qty_sold = sales.qty_sold + EXCLUDED.qty_sold;
                """))
                conn.execute(text("DROP TABLE sales_temp;"))
                conn.commit()
            
            print("✅ Chargement réussi.")
            
            with engine.connect() as conn:
                conn.execute(text("TRUNCATE TABLE sales_staging;"))
                conn.commit()
            print("Table de staging vidée.")

        except Exception as e:
            print(f"🛑 Erreur lors du chargement des données : {e}")

    print("--- FIN DU PROCESSUS ETL POUR LES VENTES ---")

if __name__ == "__main__":
    run_sales_etl()