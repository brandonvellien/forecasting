# Fichier: train.py (pour la catégorie category1_01)

import pandas as pd
import numpy as np
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor
from sklearn.metrics import mean_absolute_error
import mlflow
import mlflow.autogluon
import os
import argparse

# --- FONCTIONS UTILITAIRES ---
def smape(y_true, y_pred):
    """Calcule le Symmetric Mean Absolute Percentage Error (sMAPE)."""
    denominator = np.abs(y_true) + np.abs(y_pred)
    denominator[denominator == 0] = np.finfo(float).eps
    return np.mean(2 * np.abs(y_pred - y_true) / denominator) * 100

# ==============================================================================
# --- CONFIGURATION CENTRALE ---
# ==============================================================================
# Ce dictionnaire pourrait être dans un fichier config.py partagé
MODELS_CONFIG = {
    "ligne1_category1_01": {
        "category_id_in_file": "category1_01",
        "data_source": "ventes_paris_ligne1_par_categorie.csv",
        "data_filter_start": 118,
        "transformation": None,
        "target_column": "qty_sold"
    }
}
# ==============================================================================

def train_model(unique_id: str):
    """
    Entraîne le modèle champion pour une catégorie et enregistre les résultats
    de l'expérience avec MLflow.
    """
    print(f"--- Début de l'entraînement pour {unique_id} ---")
    
    if unique_id not in MODELS_CONFIG:
        raise ValueError(f"ID non valide. '{unique_id}' n'est pas dans la configuration.")
    
    config = MODELS_CONFIG[unique_id]

    mlflow.set_experiment("Prédictions Ligne Produit 1")
    with mlflow.start_run(run_name=f"Training_TFT_{unique_id}") as run:
        
        print("Enregistrement des paramètres sur MLflow...")
        mlflow.log_params(config)
        
        # 1. Préparation des données
        print("Préparation des données...")
        df_ventes = pd.read_csv(config["data_source"], parse_dates=['timestamp'])
        df_cat = df_ventes[df_ventes['item_id'] == config["category_id_in_file"]].copy()
        donnees_hebdo = df_cat.groupby('item_id').resample('W-MON', on='timestamp', include_groups=False).sum(numeric_only=True).reset_index()
        donnees_hebdo['item_id'] = config["category_id_in_file"]
        
        data = TimeSeriesDataFrame.from_data_frame(
            donnees_hebdo, id_column="item_id", timestamp_column="timestamp")

        if config["data_filter_start"] is not None:
            start_date = data.loc[config["category_id_in_file"]].index[config["data_filter_start"]]
            data = data.query("timestamp >= @start_date")
        
        prediction_length = 12
        cutoff_date = data.index.get_level_values('timestamp').max() - pd.to_timedelta(prediction_length * 7, unit='D')
        train_data = data[data.index.get_level_values('timestamp') <= cutoff_date]
        test_data = data
        print("✅ Données finales prêtes.")

        # 2. Entraînement
        print("\nLancement de l'entraînement ciblé sur TFT...")
        tft_powerful_params = {
            'context_length': prediction_length * 3, 'hidden_dim': 64,
            'dropout_rate': 0.1, 'max_epochs': 120, 'early_stopping_patience': 20
        }
        mlflow.log_params(tft_powerful_params)
        
        predictor = TimeSeriesPredictor(
            prediction_length=prediction_length,
            path=f"AutogluonModels/ts_TFT_ONLY_{config['category_id_in_file']}",
            target=config["target_column"],
            eval_metric="mean_wQuantileLoss",
            quantile_levels=[0.1, 0.5, 0.9]
        )
        predictor.fit(train_data, hyperparameters={'TemporalFusionTransformer': tft_powerful_params})

        # 3. Évaluation et Logging des résultats
        print("\nÉvaluation du modèle...")
        predictions = predictor.predict(train_data)
        y_test = test_data.tail(prediction_length)[config["target_column"]]
        y_pred = predictions['0.5']
        mae_score = mean_absolute_error(y_test, y_pred)
        
        print(f"MAE obtenue : {mae_score:.2f}")
        mlflow.log_metric("mae", mae_score)
        
        # 4. Sauvegarde du modèle sur MLflow
        print("Sauvegarde du modèle sur MLflow...")
        mlflow.autogluon.log_model(
            predictor,
            artifact_path=f"model_{unique_id}",
            registered_model_name=f"sales-forecast-{unique_id}"
        )
        print(f"--- Entraînement pour {unique_id} terminé. ---")
        return run.info.run_id

# --- POINT D'ENTRÉE POUR L'EXÉCUTION ---
if __name__ == "__main__":
    # Configuration de l'adresse du serveur MLflow depuis une variable d'environnement ou en dur
    IP_EXTERNE_DE_VOTRE_VM = os.environ.get("MLFLOW_TRACKING_URI", "http://VOTRE_IP_EXTERNE_ICI:5000").replace("http://", "").split(":")[0]
    mlflow.set_tracking_uri(f"http://{IP_EXTERNE_DE_VOTRE_VM}:5000")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="ID unique de la catégorie à entraîner (ex: ligne1_category1_01)")
    args = parser.parse_args()
    
    run_id = train_model(args.category)
    print(f"\n✅ Succès ! Retrouvez cette exécution dans l'interface MLflow (http://{IP_EXTERNE_DE_VOTRE_VM}:5000) avec l'ID : {run_id}")