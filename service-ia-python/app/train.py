# Fichier: service-ia-python/app/train.py (Version finale, avec filtre corrigé)

import pandas as pd
from sqlalchemy import create_engine
import os
import argparse
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor
from sklearn.metrics import mean_absolute_error
import comet_ml
from dotenv import load_dotenv
from config import MODELS_CONFIG

# Charger les variables d'environnement
load_dotenv()

def get_data_from_supabase(config):
    """
    Se connecte à Supabase et récupère les données nécessaires
    en fonction de la configuration du modèle.
    """
    print("--- Connexion à Supabase et récupération des données ---")
    
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
        # Cas simple : on ne prend que les ventes
        query = f"""
        SELECT item_id, "timestamp", qty_sold
        FROM sales
        WHERE item_id = '{item_id_to_fetch}'
        ORDER BY "timestamp";
        """
        print("Requête simple (ventes uniquement)...")
    else:
        # Cas complexe : on joint les données externes
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
        print("Requête complexe (avec jointures)...")

    df = pd.read_sql(query, engine, parse_dates=['timestamp'])
    print(f"{len(df)} lignes de données récupérées.")
    return df

def train_model(unique_id: str):
    """
    Entraîne le modèle en utilisant les données de Supabase et le sauvegarde sur Comet.
    """
    print(f"--- Début de l'entraînement pour {unique_id} ---")
    
    if unique_id not in MODELS_CONFIG:
        raise ValueError(f"ID '{unique_id}' non trouvé dans la configuration.")
    
    config = MODELS_CONFIG[unique_id]
    known_covariates = config.get("known_covariates", [])

    experiment = comet_ml.Experiment(project_name=os.environ.get("COMET_PROJECT_NAME"))
    experiment.set_name(f"Training_TFT_{unique_id}")
    experiment.log_parameters(config)
    
    # 1. Préparation des données depuis Supabase
    df_daily = get_data_from_supabase(config)
    
    # Agréger les données à la semaine
    agg_config = {'item_id': 'first', 'qty_sold': 'sum'}
    for cov in known_covariates:
        agg_config[cov] = 'mean'
    donnees_hebdo = df_daily.set_index('timestamp').resample('W-MON').agg(agg_config).reset_index()
    
    donnees_hebdo['item_id'] = donnees_hebdo['item_id'].ffill()
    donnees_hebdo.dropna(subset=['item_id'], inplace=True)

    for col in known_covariates:
        donnees_hebdo[col] = donnees_hebdo[col].interpolate()
    
    donnees_hebdo['timestamp'] = pd.to_datetime(donnees_hebdo['timestamp']).dt.tz_localize(None)
    data = TimeSeriesDataFrame.from_data_frame(donnees_hebdo, id_column="item_id", timestamp_column="timestamp")

    # <<< CORRECTION FINALE ICI : Le bloc manquant est réintégré >>>
    if config.get("data_filter_start") is not None:
        filter_start_index = config.get("data_filter_start")
        print(f"Filtrage des données : conservation des données après l'indice {filter_start_index}.")
        start_date = data.loc[config["category_id_in_file"]].index[filter_start_index]
        data = data.query("timestamp >= @start_date")
        print(f"Nombre de lignes après filtrage : {len(data)}")

    prediction_length = 12
    cutoff_date = data.index.get_level_values('timestamp').max() - pd.to_timedelta(prediction_length * 7, unit='D')
    train_data = data[data.index.get_level_values('timestamp') <= cutoff_date]
    test_data = data
    
    # 2. Entraînement
    print("Lancement de l'entraînement AutoGluon...")
    tft_params = {
        'context_length': prediction_length * 3, 'hidden_dim': 64,
        'dropout_rate': 0.1, 'max_epochs': 120, 'early_stopping_patience': 20
    }
    experiment.log_parameters(tft_params)
    
    local_model_path = f"AutogluonModels/temp_{unique_id}"
    
    predictor = TimeSeriesPredictor(
        prediction_length=prediction_length,
        path=local_model_path,
        target=config["original_target_col"],
        eval_metric="mean_wQuantileLoss",
        quantile_levels=[0.1, 0.5, 0.9],
        known_covariates_names=known_covariates
    )
    predictor.fit(train_data, hyperparameters={'TemporalFusionTransformer': tft_params})

    # 3. Évaluation
    print("Évaluation du modèle...")
    future_known_covariates = test_data.tail(prediction_length)[known_covariates] if known_covariates else None
    predictions = predictor.predict(train_data, known_covariates=future_known_covariates)
    y_test = test_data.tail(prediction_length)[config["original_target_col"]]
    y_pred = predictions['0.5']
    mae_score = mean_absolute_error(y_test, y_pred)
    
    print(f"MAE Score: {mae_score}")
    experiment.log_metric("mae", mae_score)
    
    # 4. Sauvegarde
    print("Sauvegarde du modèle sur le registre de Comet...")
    experiment.log_model(
        name=f"sales-forecast-{unique_id.replace('_', '-')}",
        file_or_folder=local_model_path,
    )

    print(f"--- Entraînement pour {unique_id} terminé. ---")
    experiment.end()
    return "✅ Succès ! Retrouvez cette exécution sur Comet."

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="ID unique de la catégorie à entraîner")
    args = parser.parse_args()
    
    result_message = train_model(args.category)
    print(f"\n{result_message}")