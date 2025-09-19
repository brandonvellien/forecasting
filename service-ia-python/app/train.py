# Fichier: service-ia-python/app/train.py (Version finale, logique Workbench 100% répliquée)

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
        db_password = os.environ.get("DB_PASSWORD")
        db_host = os.environ.get("DB_HOST")
        db_user = os.environ.get("DB_USER")
        db_name = os.environ.get("DB_NAME")
        db_port = os.environ.get("DB_PORT")
        connection_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(connection_str)

def get_dynamic_data(config):
    """
    Récupère et prépare les données depuis Supabase en suivant
    strictement la logique du script Workbench.
    """
    print("--- Préparation des données depuis Supabase (Logique Workbench) ---")
    init_db_engine()
    
    item_id_to_fetch = config["category_id_in_file"]
    
    # --- 1. Ventes (Logique Workbench) ---
    sql_query = f"SELECT item_id, \"timestamp\", qty_sold FROM sales WHERE item_id = '{item_id_to_fetch}'"
    sales_df = pd.read_sql(sql_query, engine, parse_dates=['timestamp'])
    sales_df['timestamp'] = sales_df['timestamp'].dt.tz_localize(None)
    df_cat = sales_df[sales_df['item_id'] == item_id_to_fetch].copy()
    donnees_hebdo = df_cat.groupby('item_id').resample('W-MON', on='timestamp').sum(numeric_only=True).reset_index()

    # --- 2. Données externes (traitées séparément AVANT la fusion) ---
    known_covariates = config.get("known_covariates", [])

    if "temperature_mean" in known_covariates or "rain" in known_covariates:
        weather_df = pd.read_sql("SELECT date AS timestamp, temperature_mean, precipitation AS rain FROM weather WHERE city = 'PARIS'", engine, parse_dates=['timestamp'])
        weather_df['timestamp'] = weather_df['timestamp'].dt.tz_localize(None)
        meteo_hebdo = weather_df.set_index('timestamp')[['rain', 'temperature_mean']].resample('W-MON').mean().ffill().reset_index()
        donnees_hebdo = pd.merge(donnees_hebdo, meteo_hebdo, on='timestamp', how='left')

    if "ipc" in known_covariates:
        ipc_df = pd.read_sql("SELECT time_period AS timestamp, ipc_clothing_shoes AS ipc FROM ipc", engine, parse_dates=['timestamp'])
        ipc_df['timestamp'] = ipc_df['timestamp'].dt.tz_localize(None)
        ipc_hebdo = ipc_df.set_index('timestamp').resample('W-MON').mean().ffill().reset_index()
        donnees_hebdo = pd.merge(donnees_hebdo, ipc_hebdo, on='timestamp', how='left')
        
    if "moral_menages" in known_covariates:
        mdm_df = pd.read_sql("SELECT time_period AS timestamp, synthetic_indicator AS moral_menages FROM household_confidence", engine, parse_dates=['timestamp'])
        mdm_df['timestamp'] = mdm_df['timestamp'].dt.tz_localize(None)
        moral_hebdo = mdm_df.set_index('timestamp').resample('W-MON').mean().ffill().reset_index()
        donnees_hebdo = pd.merge(donnees_hebdo, moral_hebdo, on='timestamp', how='left')

    # --- 3. Nettoyage final (après toutes les fusions) ---
    donnees_hebdo = donnees_hebdo.ffill().bfill()
    donnees_hebdo.dropna(inplace=True)
    
    return donnees_hebdo

def train_model(unique_id: str):
    # Le reste de cette fonction et du script est correct et ne change pas.
    print(f"--- Début de l'entraînement pour {unique_id} ---")
    
    config = MODELS_CONFIG[unique_id]
    
    experiment = comet_ml.Experiment(project_name=os.environ.get("COMET_PROJECT_NAME"))
    experiment.set_name(f"Training_TFT_{unique_id}")
    experiment.log_parameters(config)
    
    donnees_hebdo = get_dynamic_data(config)
    
    target_col = config["original_target_col"]
    if config.get("transformation") == "log":
        target_col = f"{config['original_target_col']}_log"
        donnees_hebdo[target_col] = np.log1p(donnees_hebdo[config["original_target_col"]])

    data = TimeSeriesDataFrame.from_data_frame(donnees_hebdo, id_column="item_id", timestamp_column="timestamp")

    if config.get("data_filter_start") is not None:
        start_date = data.loc[config["category_id_in_file"]].index[config["data_filter_start"]]
        data = data.query("timestamp >= @start_date")
        
    prediction_length = 12
    cutoff_date = data.index.get_level_values('timestamp').max() - pd.to_timedelta(prediction_length * 7, unit='D')
    train_data = data[data.index.get_level_values('timestamp') <= cutoff_date]
    test_data = data
    
    print("Lancement de l'entraînement AutoGluon...")
    default_tft_params = {
        'context_length': prediction_length * 3, 'hidden_dim': 64,
        'dropout_rate': 0.1, 'max_epochs': 120, 'early_stopping_patience': 20
    }
    tft_params = config.get("hyperparameters", default_tft_params)
    experiment.log_parameters(tft_params)
    
    local_model_path = f"AutogluonModels/temp_{unique_id}"
    
    predictor = TimeSeriesPredictor(
        prediction_length=prediction_length,
        path=local_model_path,
        target=target_col,
        eval_metric="mean_wQuantileLoss",
        quantile_levels=[0.1, 0.5, 0.9],
        known_covariates_names=config.get("known_covariates", []),
        
    )
    train_data.to_csv("Check")
    predictor.fit(train_data, hyperparameters={'TemporalFusionTransformer': tft_params})

    print("Évaluation du modèle...")
    known_covariates = config.get("known_covariates", [])
    future_known_covariates = test_data.tail(prediction_length)[known_covariates] if known_covariates else None

    predictions = predictor.predict(train_data, known_covariates=future_known_covariates)
    
    y_test = test_data.tail(prediction_length)[config["original_target_col"]]
    
    if config.get("transformation") == "log":
        y_pred = np.expm1(predictions['0.5'])
    else:
        y_pred = predictions['0.5']
    
    mae_score = mean_absolute_error(y_test, y_pred.clip(0))
    
    print(f"MAE Score: {mae_score}")
    experiment.log_metric("mae", mae_score)
    
    experiment.log_model(
        name=f"sales-forecast-{unique_id.replace('_', '-')}",
        file_or_folder=local_model_path,
    )
    experiment.end()
    return "✅ Succès ! Retrouvez cette exécution sur Comet."

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="ID unique de la catégorie à entraîner")
    args = parser.parse_args()
    
    result_message = train_model(args.category)
    print(f"\n{result_message}")