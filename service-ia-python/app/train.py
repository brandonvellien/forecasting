# Fichier: service-ia-python/app/train.py (Version finale multi-modèles)

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
    global engine
    if engine is None:
        db_password, db_host, db_user, db_name, db_port = (os.environ.get(k) for k in ["DB_PASSWORD", "DB_HOST", "DB_USER", "DB_NAME", "DB_PORT"])
        connection_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(connection_str)

def get_base_data(config):
    """Récupère les données de ventes depuis la table spécifiée."""
    init_db_engine()
    table = config["source_table"]
    item_id = config["category_id_in_file"]
    print(f"--- Récupération des données depuis la table '{table}' pour l'item '{item_id}' ---")
    
    sql_query = f"SELECT item_id, \"timestamp\", qty_sold FROM {table} WHERE item_id = '{item_id}'"
    df = pd.read_sql(sql_query, engine, parse_dates=['timestamp'])
    df['timestamp'] = df['timestamp'].dt.tz_localize(None)
    
    # Agrégation à la semaine
    df_hebdo = df.groupby('item_id').resample('W-MON', on='timestamp').sum(numeric_only=True).reset_index()
    df_hebdo['item_id'] = item_id # S'assurer que l'item_id est correct après resample
    return df_hebdo

def apply_feature_engineering(df, config):
    """Applique le feature engineering (lags, rolling means) si spécifié."""
    if "feature_engineering" not in config:
        return df

    print("--- Application du Feature Engineering ---")
    fe_config = config["feature_engineering"]
    target = config["original_target_col"]

    # Création des lags
    for lag in fe_config.get("lags", []):
        df[f'lag_{lag}'] = df[target].shift(lag)
    
    # Création des moyennes mobiles
    for window in fe_config.get("rolling_means", []):
        df[f'rolling_mean_{window}'] = df[target].shift(1).rolling(window=window).mean()
        
    return df

def train_model(unique_id: str):
    print(f"--- Début de l'entraînement pour {unique_id} ---")
    config = MODELS_CONFIG[unique_id]
    
    # Initialisation de Comet ML
    experiment = comet_ml.Experiment(project_name=os.environ.get("COMET_PROJECT_NAME"))
    experiment.set_name(f"Training_{unique_id}")
    experiment.log_parameters(config)
    
    # Pipeline de préparation des données
    donnees_hebdo = get_base_data(config)
    donnees_hebdo = apply_feature_engineering(donnees_hebdo, config)
    
    # Gestion des covariables externes (pour les anciens modèles)
    known_covariates = config.get("known_covariates", [])
    if known_covariates:
        # Le code pour fusionner les données météo, IPC, etc. reste ici si nécessaire
        pass

    donnees_hebdo.dropna(inplace=True)

    # Transformation de la cible (log)
    target_col = config["original_target_col"]
    if config.get("transformation") == "log":
        target_col = f"{target_col}_log"
        donnees_hebdo[target_col] = np.log1p(donnees_hebdo[config["original_target_col"]])

    # Filtres de date
    if config.get("training_start_date"):
        donnees_hebdo = donnees_hebdo[donnees_hebdo['timestamp'] >= config["training_start_date"]]

    data = TimeSeriesDataFrame.from_data_frame(donnees_hebdo, id_column="item_id", timestamp_column="timestamp")

    if config.get("data_filter_start") is not None:
        start_date = data.loc[config["category_id_in_file"]].index[config["data_filter_start"]]
        data = data.query("timestamp >= @start_date")
        
    prediction_length = 12
    train_data = data.slice_by_timestep(end_index=-prediction_length)
    test_data = data
    
    print("Lancement de l'entraînement AutoGluon...")
    local_model_path = f"AutogluonModels/temp_{unique_id}"
    
    predictor = TimeSeriesPredictor(
        prediction_length=prediction_length,
        path=local_model_path,
        target=target_col,
        eval_metric="mean_wQuantileLoss",
        quantile_levels=[0.1, 0.5, 0.9],
        known_covariates_names=known_covariates
    )
    
    # Entraînement
    fit_hyperparameters = config.get("hyperparameters", {})
    model_to_train = fit_hyperparameters.pop("model", None)
    
    if model_to_train:
        print(f"Entraînement d'un modèle unique : {model_to_train}")
        predictor.fit(train_data, hyperparameters={model_to_train: fit_hyperparameters})
    else:
        presets = config.get("presets", "medium_quality")
        time_limit = config.get("time_limit")
        print(f"Entraînement avec presets='{presets}' et time_limit={time_limit}s")
        predictor.fit(train_data, presets=presets, time_limit=time_limit)

    # Évaluation
    print("Évaluation du modèle...")
    predictions = predictor.predict(train_data)
    
    y_test = test_data.tail(prediction_length)[config["original_target_col"]]
    y_pred = predictions['0.5']
    if config.get("transformation") == "log":
        y_pred = np.expm1(y_pred)
    
    mae_score = mean_absolute_error(y_test, y_pred.clip(0))
    print(f"MAE Score: {mae_score}")
    experiment.log_metric("mae", mae_score)
    
    # Sauvegarde sur Comet ML
    experiment.log_model(name=f"sales-forecast-{unique_id.replace('_', '-')}", file_or_folder=local_model_path)
    experiment.end()
    return "✅ Succès ! Retrouvez cette exécution sur Comet."

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="ID unique de la catégorie à entraîner")
    args = parser.parse_args()
    result_message = train_model(args.category)
    print(f"\n{result_message}")