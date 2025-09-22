# Fichier: service-ia-python/app/predict.py (Version finale multi-modèles)

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor
from .config import MODELS_CONFIG
import comet_ml.api
import os
import shutil
from dotenv import load_dotenv
import tempfile

load_dotenv()
comet_api = comet_ml.api.API()

def get_base_data(config, engine):
    """Récupère les données de ventes depuis la table spécifiée."""
    table = config["source_table"]
    item_id = config["category_id_in_file"]
    print(f"--- Récupération des données depuis la table '{table}' pour l'item '{item_id}' ---")
    
    sql_query = f"SELECT item_id, \"timestamp\", qty_sold FROM {table} WHERE item_id = '{item_id}'"
    df = pd.read_sql(sql_query, engine, parse_dates=['timestamp'])
    df['timestamp'] = df['timestamp'].dt.tz_localize(None)
    
    df_hebdo = df.groupby('item_id').resample('W-MON', on='timestamp').sum(numeric_only=True).reset_index()
    df_hebdo['item_id'] = item_id
    return df_hebdo

def apply_feature_engineering(df, config):
    """Applique le feature engineering (lags, rolling means) si spécifié."""
    if "feature_engineering" not in config:
        return df

    print("--- Application du Feature Engineering ---")
    fe_config = config["feature_engineering"]
    target = config["original_target_col"]

    for lag in fe_config.get("lags", []):
        df[f'lag_{lag}'] = df[target].shift(lag)
    
    for window in fe_config.get("rolling_means", []):
        df[f'rolling_mean_{window}'] = df[target].shift(1).rolling(window=window).mean()
        
    return df

def get_prediction(unique_id: str, future_only: bool = False) -> pd.DataFrame:
    print(f"--- Début de la prédiction pour '{unique_id}' ---")
    if unique_id not in MODELS_CONFIG:
        raise ValueError(f"L'ID de modèle '{unique_id}' n'a pas été trouvé dans la configuration.")
    config = MODELS_CONFIG[unique_id]
    
    with tempfile.TemporaryDirectory() as temp_output_folder:
        try:
            # 1. Télécharger et charger le modèle
            workspace, model_name = os.environ.get("COMET_WORKSPACE"), f"sales-forecast-{unique_id.replace('_', '-')}"
            print(f"Téléchargement du modèle '{model_name}' dans {temp_output_folder}")
            model_registry_item = comet_api.get_model(workspace=workspace, model_name=model_name)
            latest_version_str = model_registry_item.find_versions()[0]
            model_registry_item.download(version=latest_version_str, output_folder=temp_output_folder, expand=True)

            path_to_model = temp_output_folder
            potential_subfolder = os.path.join(temp_output_folder, f"temp_{unique_id}")
            if os.path.isdir(potential_subfolder):
                path_to_model = potential_subfolder
            else:
                found = False
                for root, _, files in os.walk(temp_output_folder):
                    if "predictor.pkl" in files:
                        path_to_model = root
                        found = True
                        break
                if not found:
                    raise FileNotFoundError("Impossible de trouver 'predictor.pkl' dans le modèle téléchargé.")
            
            print(f"Chemin du modèle trouvé : {path_to_model}")
            predictor = TimeSeriesPredictor.load(path_to_model)
            print("Modèle AutoGluon chargé avec succès.")

        except Exception as e:
            print(f"🛑 Erreur critique lors du chargement du modèle pour {unique_id}: {e}")
            return None

        # 2. Préparer les données
        db_password, db_host, db_user, db_name, db_port = (os.environ.get(k) for k in ["DB_PASSWORD", "DB_HOST", "DB_USER", "DB_NAME", "DB_PORT"])
        connection_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(connection_str)
        
        donnees_hebdo = get_base_data(config, engine)
        donnees_hebdo = apply_feature_engineering(donnees_hebdo, config)
        
        # Le code pour les covariables externes (ligne 1) reste ici
        known_covariates = config.get("known_covariates", [])
        if known_covariates:
            # ... (logique pour fusionner météo, IPC, etc. si nécessaire)
            pass

        donnees_hebdo.dropna(inplace=True)

        target_col = config["original_target_col"]
        if config.get("transformation") == "log":
            target_col = f"{target_col}_log"
            donnees_hebdo[target_col] = np.log1p(donnees_hebdo[config["original_target_col"]])

        if config.get("training_start_date"):
            donnees_hebdo = donnees_hebdo[donnees_hebdo['timestamp'] >= config["training_start_date"]]

        full_data_ts = TimeSeriesDataFrame.from_data_frame(donnees_hebdo, id_column="item_id", timestamp_column="timestamp")
        
        if config.get("data_filter_start") is not None:
            full_data_ts = full_data_ts.loc[config["category_id_in_file"]].iloc[config["data_filter_start"]:].reset_index()
            full_data_ts = TimeSeriesDataFrame(full_data_ts, id_column="item_id", timestamp_column="timestamp")
        
        # 3. Prédiction
        print("Génération des prévisions...")
        predictions = predictor.predict(full_data_ts)

        if config.get("transformation") == "log":
            final_predictions = np.expm1(predictions)
        else:
            final_predictions = predictions

        final_predictions = final_predictions.clip(lower=0)
        
        print(f"--- Prédiction pour '{unique_id}' terminée. ---")
        return final_predictions


# Le point d'entrée pour les tests en local reste inchangé
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Lance une prédiction de ventes.")
    parser.add_argument("--category", required=True, help="ID unique de la catégorie.")
    parser.add_argument("--future", action="store_true", help="Si activé, prédit les 12 prochaines semaines.")
    args = parser.parse_args()

    try:
        predictions_df = get_prediction(args.category, future_only=args.future)
        if predictions_df is not None:
            if args.future:
                print("\n--- Prévisions futures (12 prochaines semaines) ---")
            else:
                print("\n--- Prévisions vs Réalité (12 dernières semaines) ---")
            print(predictions_df.round(2))
            print("\n✅ Script terminé avec succès.")
        else:
            print("\n❌ Le script n'a pas pu générer de prévisions.")
    except Exception as e:
        print(f"\n❌ Une erreur inattendue est survenue : {e}")