
import pandas as pd
import numpy as np
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor
from sklearn.metrics import mean_absolute_error
import mlflow
from mlflow.pyfunc import PythonModel
import joblib
import os
import argparse

# --- Wrapper PyFunc pour rendre le modèle AutoGluon compatible avec MLflow ---
class AutoGluonPyFuncModel(PythonModel):
    def load_context(self, context):
        """Charge le modèle depuis le chemin sauvegardé."""
        self.predictor = TimeSeriesPredictor.load(context.artifacts["predictor_path"])

    def predict(self, context, model_input):
        """Effectue la prédiction."""
        # On s'assure que l'entrée est au bon format
        if not isinstance(model_input, TimeSeriesDataFrame):
            model_input = TimeSeriesDataFrame(model_input)
        return self.predictor.predict(model_input)

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
    Entraîne le modèle, l'évalue, et le sauvegarde sur MLflow en utilisant un wrapper PyFunc.
    """
    print(f"--- Début de l'entraînement pour {unique_id} ---")
    
    if unique_id not in MODELS_CONFIG:
        raise ValueError(f"ID non valide.")
    
    config = MODELS_CONFIG[unique_id]

    mlflow.set_experiment("Prédictions Ligne Produit 1")
    with mlflow.start_run(run_name=f"Training_TFT_pyfunc_{unique_id}") as run:
        
        mlflow.log_params(config)
        
        # --- 1. Préparation des données ---
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
        
        # --- 2. Entraînement ---
        print("Lancement de l'entraînement AutoGluon...")
        tft_params = {
            'context_length': prediction_length * 3, 'hidden_dim': 64,
            'dropout_rate': 0.1, 'max_epochs': 120, 'early_stopping_patience': 20
        }
        mlflow.log_params(tft_params)
        
        # Le chemin local où le modèle sera temporairement sauvegardé
        local_model_path = f"AutogluonModels/temp_{unique_id}"
        
        predictor = TimeSeriesPredictor(
            prediction_length=prediction_length, path=local_model_path,
            target=config["original_target_col"], eval_metric="mean_wQuantileLoss",
            quantile_levels=[0.1, 0.5, 0.9]
        )
        predictor.fit(train_data, hyperparameters={'TemporalFusionTransformer': tft_params})

        # --- 3. Évaluation ---
        print("Évaluation du modèle...")
        predictions = predictor.predict(train_data)
        y_test = test_data.tail(prediction_length)[config["original_target_col"]]
        y_pred = predictions['0.5']
        mae_score = mean_absolute_error(y_test, y_pred)
        mlflow.log_metric("mae", mae_score)
        
        # --- 4. Sauvegarde avec le wrapper PyFunc ---
        print("Sauvegarde du modèle sur MLflow avec le wrapper PyFunc...")
        mlflow.pyfunc.log_model(
            artifact_path=f"model_{unique_id}",
            python_model=AutoGluonPyFuncModel(),
            # On dit à MLflow d'inclure le dossier du modèle sauvegardé
            artifacts={'predictor_path': local_model_path},
            registered_model_name=f"sales-forecast-{unique_id}"
        )
        print(f"--- Entraînement pour {unique_id} terminé. ---")
        return run.info.run_id

# --- POINT D'ENTRÉE POUR L'EXÉCUTION ---
if __name__ == "__main__":
    mlflow_tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if mlflow_tracking_uri:
        mlflow.set_tracking_uri(mlflow_tracking_uri)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="ID unique de la catégorie à entraîner")
    args = parser.parse_args()
    
    run_id = train_model(args.category)
    print(f"\n✅ Succès ! Retrouvez cette exécution dans MLflow avec l'ID : {run_id}")