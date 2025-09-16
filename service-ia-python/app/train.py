# Fichier: service-ia-python/app/train.py (Version finale avec Comet)

import pandas as pd
import numpy as np
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor
from sklearn.metrics import mean_absolute_error
import comet_ml  # Remplacement de mlflow
import os
import argparse
from config import MODELS_CONFIG

def train_model(unique_id: str):
    """
    Entraîne le modèle, l'évalue, et le sauvegarde sur Comet.
    """
    print(f"--- Début de l'entraînement pour {unique_id} ---")
    
    if unique_id not in MODELS_CONFIG:
        raise ValueError(f"ID '{unique_id}' non trouvé dans la configuration.")
    
    config = MODELS_CONFIG[unique_id]

    # Initialisation de l'expérience Comet
    # Comet lit automatiquement les secrets (API Key, Workspace) depuis les variables d'environnement
    experiment = comet_ml.Experiment(
        project_name=os.environ.get("COMET_PROJECT_NAME")
    )
    experiment.set_name(f"Training_TFT_{unique_id}")
    
    print("Logging des paramètres de configuration sur Comet...")
    experiment.log_parameters(config)
    
    # 1. Préparation des données (inchangée)
    print("Préparation des données...")
    df_ventes = pd.read_csv(config["data_source"], parse_dates=['timestamp'])
    df_cat = df_ventes[df_ventes['item_id'] == config["category_id_in_file"]].copy()
    donnees_hebdo = df_cat.groupby('item_id').resample('W-MON', on='timestamp', include_groups=False).sum(numeric_only=True).reset_index()
    donnees_hebdo['item_id'] = config["category_id_in_file"]
    
    data = TimeSeriesDataFrame.from_data_frame(
        donnees_hebdo, id_column="item_id", timestamp_column="timestamp")

    if config.get("data_filter_start") is not None:
        start_date = data.loc[config["category_id_in_file"]].index[config["data_filter_start"]]
        data = data.query("timestamp >= @start_date")
    
    prediction_length = 12
    cutoff_date = data.index.get_level_values('timestamp').max() - pd.to_timedelta(prediction_length * 7, unit='D')
    train_data = data[data.index.get_level_values('timestamp') <= cutoff_date]
    test_data = data
    
    # 2. Entraînement (inchangé)
    print("Lancement de l'entraînement AutoGluon...")
    tft_params = {
        'context_length': prediction_length * 3, 'hidden_dim': 64,
        'dropout_rate': 0.1, 'max_epochs': 120, 'early_stopping_patience': 20
    }
    experiment.log_parameters(tft_params)
    
    local_model_path = f"AutogluonModels/temp_{unique_id}"
    
    predictor = TimeSeriesPredictor(
        prediction_length=prediction_length, path=local_model_path,
        target=config["original_target_col"], eval_metric="mean_wQuantileLoss",
        quantile_levels=[0.1, 0.5, 0.9]
    )
    predictor.fit(train_data, hyperparameters={'TemporalFusionTransformer': tft_params})

    # 3. Évaluation
    print("Évaluation du modèle...")
    predictions = predictor.predict(train_data)
    y_test = test_data.tail(prediction_length)[config["original_target_col"]]
    y_pred = predictions['0.5']
    mae_score = mean_absolute_error(y_test, y_pred)
    
    print(f"MAE Score: {mae_score}")
    experiment.log_metric("mae", mae_score)
    
    # 4. Sauvegarde du modèle sur Comet
    print("Sauvegarde du modèle sur le registre de Comet...")
    experiment.log_model(
        name=f"sales-forecast-{unique_id}",
        file_or_folder=local_model_path,
    )

    print(f"--- Entraînement pour {unique_id} terminé. ---")
    
    # On s'assure que tout est bien envoyé avant la fin du script
    experiment.end()
    
    return f"✅ Succès ! Retrouvez cette exécution sur Comet."

# --- Point d'entrée pour l'exécution en ligne de commande (inchangé) ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="ID unique de la catégorie à entraîner")
    args = parser.parse_args()
    
    result_message = train_model(args.category)
    print(f"\n{result_message}")