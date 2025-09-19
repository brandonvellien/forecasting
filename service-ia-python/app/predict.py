# Fichier: service-ia-python/app/predict.py (Version finale gérant les covariables et transformations)

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor
from .config import MODELS_CONFIG
import comet_ml.api
import os
import shutil
from dotenv import load_dotenv

# Charger les variables d'environnement (pour les tests en local)
load_dotenv()

comet_api = comet_ml.api.API()

def get_data_from_supabase(config):
    """
    Se connecte à Supabase et récupère les données nécessaires
    en fonction de la configuration du modèle.
    """
    print("--- Connexion à Supabase et récupération des données d'historique ---")
    
    db_password = os.environ.get("DB_PASSWORD")
    db_host = os.environ.get("DB_HOST")
    db_user = os.environ.get("DB_USER")
    db_name = os.environ.get("DB_NAME")
    db_port = os.environ.get("DB_PORT")

    connection_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(connection_str)

    item_id_to_fetch = config["category_id_in_file"]
    known_covariates = config.get("known_covariates", [])

    # On construit la requête SQL dynamiquement
    if not known_covariates:
        query = f"""
        SELECT item_id, "timestamp", qty_sold
        FROM sales
        WHERE item_id = '{item_id_to_fetch}'
        ORDER BY "timestamp";
        """
    else:
        select_clauses = "s.item_id, s.\"timestamp\", s.qty_sold"
        joins = ""
        if "temperature_mean" in known_covariates or "precipitation" in known_covariates:
            select_clauses += ", w.temperature_mean, w.precipitation"
            joins += " LEFT JOIN weather w ON DATE(s.\"timestamp\") = w.date"
        if "ipc_clothing_shoes" in known_covariates:
            select_clauses += ", i.ipc_clothing_shoes"
            joins += " LEFT JOIN ipc i ON DATE_TRUNC('month', s.\"timestamp\")::DATE = i.time_period"
        if "household_confidence" in known_covariates:
            select_clauses += ", hc.synthetic_indicator AS household_confidence"
            joins += " LEFT JOIN household_confidence hc ON DATE_TRUNC('month', s.\"timestamp\")::DATE = hc.time_period"
        
        query = f"""
        SELECT {select_clauses}
        FROM sales s
        {joins}
        WHERE s.item_id = '{item_id_to_fetch}'
        ORDER BY s."timestamp";
        """

    df = pd.read_sql(query, engine, parse_dates=['timestamp'])
    print(f"{len(df)} lignes de données récupérées.")
    return df

def get_prediction(unique_id: str) -> pd.DataFrame:
    """
    Génère les prévisions de ventes en téléchargeant le modèle depuis Comet
    et en récupérant les données d'historique depuis Supabase.
    """
    print(f"--- Début de la prédiction pour '{unique_id}' ---")
    
    config = MODELS_CONFIG[unique_id]
    output_folder = "downloaded_model"
    path_to_model = ""

    # 1. Télécharger le modèle depuis Comet
    try:
        workspace = os.environ.get("COMET_WORKSPACE")
        model_name = f"sales-forecast-{unique_id.replace('_', '-')}"
        
        print(f"Téléchargement du modèle '{model_name}' depuis Comet...")
        
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)

        model_registry_item = comet_api.get_model(workspace=workspace, model_name=model_name)
        latest_version_str = model_registry_item.find_versions()[0]
        print(f"Dernière version trouvée : {latest_version_str}")

        model_registry_item.download(version=latest_version_str, output_folder=output_folder, expand=True)
        
        model_subfolder = f"temp_{unique_id}"
        path_to_model = os.path.join(output_folder, model_subfolder)
        
        print(f"Modèle téléchargé. Chemin du prédicteur : {path_to_model}")

    except Exception as e:
        print(f"🛑 Erreur lors du téléchargement depuis Comet : {e}")
        return None

    # 2. Charger le modèle
    try:
        predictor = TimeSeriesPredictor.load(path_to_model)
        print("Modèle AutoGluon chargé avec succès.")
    except Exception as e:
        print(f"🛑 Erreur lors du chargement du modèle AutoGluon : {e}")
        return None

    # 3. Préparer les données d'historique et les covariables futures
    print("Préparation des données d'historique et des covariables futures...")
    df_daily = get_data_from_supabase(config)
    
    known_covariates = config.get("known_covariates", [])
    
    # Agréger les données à la semaine
    agg_config = {'item_id': 'first', 'qty_sold': 'sum'}
    for cov in known_covariates:
        agg_config[cov] = 'mean'
    donnees_hebdo = df_daily.set_index('timestamp').resample('W-MON').agg(agg_config).reset_index()
    
    donnees_hebdo['item_id'] = donnees_hebdo['item_id'].ffill()
    donnees_hebdo.dropna(subset=['item_id'], inplace=True)

    for col in known_covariates:
        donnees_hebdo[col] = donnees_hebdo[col].interpolate().bfill()
    
    donnees_hebdo['timestamp'] = pd.to_datetime(donnees_hebdo['timestamp']).dt.tz_localize(None)

    # Appliquer la transformation si nécessaire
    if config.get("transformation") == "log":
        print(f"Application de la transformation logarithmique sur '{predictor.target}'.")
        donnees_hebdo[predictor.target] = np.log1p(donnees_hebdo[config["original_target_col"]])

    # Appliquer le filtre de date
    if config.get("data_filter_start") is not None:
        temp_ts_df = TimeSeriesDataFrame(donnees_hebdo, id_column="item_id", timestamp_column="timestamp")
        start_date = temp_ts_df.loc[config["category_id_in_file"]].index[config["data_filter_start"]]
        donnees_hebdo = donnees_hebdo.query("timestamp >= @start_date")
        
    full_data_ts = TimeSeriesDataFrame.from_data_frame(
        donnees_hebdo, id_column="item_id", timestamp_column="timestamp")
        
    # Extraire les covariables futures si le modèle en a besoin
    future_known_covariates = None
    if known_covariates:
        print("Extraction des covariables futures pour la prédiction...")
        future_known_covariates = full_data_ts.tail(predictor.prediction_length)[known_covariates]
        
    # Les données d'historique sont toutes les données disponibles
    data_history = full_data_ts

    # 4. Faire la prédiction
    print("Génération des prévisions...")
    predictions = predictor.predict(
        data_history, 
        known_covariates=future_known_covariates
    )

    # Gérer la retransformation si nécessaire
    if config.get("transformation") == "log":
        print("Application de la retransformation exponentielle.")
        final_predictions = np.expm1(predictions)
    else:
        final_predictions = predictions

    final_predictions = final_predictions.clip(lower=0)
    
    print(f"--- Prédiction pour '{unique_id}' terminée. ---")
    return final_predictions


# --- Point d'entrée pour les tests en local ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--category", 
        default="ligne1_category1_01",
        help="ID unique de la catégorie pour laquelle générer une prédiction"
    )
    args = parser.parse_args()

    print(f"Lancement de la prédiction pour la catégorie : {args.category}")
    predictions_df = get_prediction(args.category)
    
    if predictions_df is not None:
        print("\n--- Prévisions générées ---")
        print(predictions_df)
        print("\n✅ Script terminé avec succès.")
    else:
        print("\n❌ Le script n'a pas pu générer de prévisions.")