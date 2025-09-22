# Fichier: service-ia-python/app/train.py (Version finale unifiée et stable)

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os
import argparse
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor
from sklearn.metrics import mean_absolute_error
import comet_ml
from dotenv import load_dotenv
from .config import MODELS_CONFIG

load_dotenv()
engine = None

def init_db_engine():
    """Initialise la connexion à la base de données."""
    global engine
    if engine is None:
        db_password, db_host, db_user, db_name, db_port = (os.environ.get(k) for k in ["DB_PASSWORD", "DB_HOST", "DB_USER", "DB_NAME", "DB_PORT"])
        connection_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(connection_str)

def get_training_data(config):
    """
    Construit et exécute une requête SQL dynamique pour récupérer toutes les données
    nécessaires à l'entraînement (ventes + covariables externes si besoin).
    """
    init_db_engine()
    item_id_to_fetch = config["category_id_in_file"]
    known_covariates = config.get("known_covariates", [])
    source_table = config.get("source_table", "sales")
    print(f"--- 1. Récupération des données d'entraînement pour {item_id_to_fetch} ---")

    base_query = f"SELECT s.item_id, s.\"timestamp\", s.qty_sold"
    joins = ""

    if "temperature_mean" in known_covariates or "rain" in known_covariates:
        base_query += ", w.temperature_mean, w.precipitation AS rain"
        joins += " LEFT JOIN weather w ON DATE(s.\"timestamp\" AT TIME ZONE 'UTC') = w.date AND w.city = 'PARIS'"
    if "ipc" in known_covariates:
        base_query += ", i.ipc_clothing_shoes AS ipc"
        joins += " LEFT JOIN ipc i ON DATE_TRUNC('month', s.\"timestamp\" AT TIME ZONE 'UTC')::DATE = i.time_period"
    if "moral_menages" in known_covariates:
        base_query += ", hc.synthetic_indicator AS moral_menages"
        joins += " LEFT JOIN household_confidence hc ON DATE_TRUNC('month', s.\"timestamp\" AT TIME ZONE 'UTC')::DATE = hc.time_period"

    final_query = f"""
    {base_query}
    FROM {source_table} s
    {joins}
    WHERE s.item_id = '{item_id_to_fetch}'
    ORDER BY s."timestamp";
    """
    
    df = pd.read_sql(final_query, engine, parse_dates=['timestamp'])
    print(f"✅ {len(df)} lignes de données brutes récupérées.")
    return df

def apply_feature_engineering(df, config):
    """Applique le feature engineering si spécifié dans la config."""
    if "feature_engineering" not in config:
        return df
    print("--- Application du Feature Engineering (lags, rolling mean) ---")
    fe_config = config["feature_engineering"]
    target = config["original_target_col"]
    for lag in fe_config.get("lags", []):
        df[f'lag_{lag}'] = df[target].shift(lag)
    for window in fe_config.get("rolling_means", []):
        df[f'rolling_mean_{window}'] = df[target].shift(1).rolling(window=window).mean()
    return df

def train_model(unique_id: str):
    print(f"--- Début de l'entraînement pour {unique_id} ---")
    config = MODELS_CONFIG[unique_id]
    
    experiment = comet_ml.Experiment(project_name=os.environ.get("COMET_PROJECT_NAME"))
    experiment.set_name(f"Training_{unique_id}")
    experiment.log_parameters(config)
    
    # === ÉTAPE 1: PRÉPARATION DES DONNÉES ===
    df_daily = get_training_data(config)
    
    print("--- 2. Agrégation et nettoyage des données ---")
    agg_config = {'qty_sold': 'sum'}
    for cov in config.get("known_covariates", []): agg_config[cov] = 'mean'
    donnees_hebdo = df_daily.set_index('timestamp').resample('W-MON').agg(agg_config).reset_index()
    donnees_hebdo['timestamp'] = pd.to_datetime(donnees_hebdo['timestamp']).dt.tz_localize(None)
    donnees_hebdo['item_id'] = config["category_id_in_file"]

    for col in config.get("known_covariates", []):
        donnees_hebdo[col] = donnees_hebdo[col].interpolate(method='linear').ffill().bfill()

    donnees_hebdo = apply_feature_engineering(donnees_hebdo, config)
    donnees_hebdo.dropna(inplace=True)
    if donnees_hebdo.empty: raise ValueError("Données vides après nettoyage.")

    target_col = config["original_target_col"]
    if config.get("transformation") == "log":
        target_col = f"{target_col}_log"
        donnees_hebdo[target_col] = np.log1p(donnees_hebdo[config["original_target_col"]])

    if config.get("training_start_date"):
        donnees_hebdo = donnees_hebdo[donnees_hebdo['timestamp'] >= config["training_start_date"]]

    data = TimeSeriesDataFrame.from_data_frame(donnees_hebdo, id_column="item_id", timestamp_column="timestamp")
    print("✅ Données prêtes pour l'entraînement.")

    # === ÉTAPE 2: ENTRAÎNEMENT DU MODÈLE ===
    prediction_length = 12
    train_data = data.slice_by_timestep(end_index=-prediction_length)
    test_data = data
    
    print("--- 3. Lancement de l'entraînement AutoGluon ---")
    local_model_path = f"AutogluonModels/temp_{unique_id}"
    
    predictor = TimeSeriesPredictor(
        prediction_length=prediction_length,
        path=local_model_path,
        target=target_col,
        eval_metric="mean_wQuantileLoss",
        known_covariates_names=config.get("known_covariates", [])
    )
    
    predictor.fit(train_data, presets="medium_quality", time_limit=300)

    # === ÉTAPE 3: ÉVALUATION ET SAUVEGARDE ===
    print("--- 4. Évaluation du modèle ---")
    predictions = predictor.predict(train_data, known_covariates=train_data.tail(prediction_length)[config.get("known_covariates", [])])
    
    y_test = test_data.tail(prediction_length)[config["original_target_col"]]
    y_pred = predictions['0.5']
    if config.get("transformation") == "log":
        y_pred = np.expm1(y_pred)
    
    mae_score = mean_absolute_error(y_test, y_pred.clip(0))
    print(f"✅ MAE Score: {mae_score}")
    experiment.log_metric("mae", mae_score)
    
    print("--- 5. Sauvegarde du modèle sur Comet ML ---")
    experiment.log_model(name=f"sales-forecast-{unique_id.replace('_', '-')}", file_or_folder=local_model_path)
    experiment.end()
    return "✅ Succès ! Retrouvez cette exécution sur Comet."

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="ID unique de la catégorie à entraîner")
    args = parser.parse_args()
    result_message = train_model(args.category)
    print(f"\n{result_message}")