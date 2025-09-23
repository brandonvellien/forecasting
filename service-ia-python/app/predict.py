# Fichier: service-ia-python/app/predict.py (Version finale avec recherche de chemin multiple)

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
import traceback
import argparse

load_dotenv()
comet_api = comet_ml.api.API()

# --- Fonctions de préparation des données (inchangées) ---
def get_data_with_covariates(config, engine):
    print(f"--- 1. Récupération des données pour {config['category_id_in_file']} ---")
    item_id_to_fetch = config["category_id_in_file"]
    known_covariates = config.get("known_covariates", [])
    source_table = config.get("source_table", "sales")
    
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

# --- Fonction de prédiction principale ---

def get_prediction(unique_id: str, future_only: bool = True) -> pd.DataFrame:
    print(f"--- Début de la prédiction pour '{unique_id}' ---")
    if unique_id not in MODELS_CONFIG:
        raise ValueError(f"ID de modèle '{unique_id}' non trouvé.")
    config = MODELS_CONFIG[unique_id]
    
    with tempfile.TemporaryDirectory() as temp_output_folder:
        try:
            # === ÉTAPE 1: CHARGEMENT DU MODÈLE ===
            workspace, model_name = os.environ.get("COMET_WORKSPACE"), f"sales-forecast-{unique_id.replace('_', '-')}"
            print(f"Téléchargement du modèle '{model_name}'...")
            model_registry_item = comet_api.get_model(workspace=workspace, model_name=model_name)
            latest_version_str = model_registry_item.find_versions()[0]
            model_registry_item.download(version=latest_version_str, output_folder=temp_output_folder, expand=True)

            # <<< LOGIQUE DE RECHERCHE DÉFINITIVE AVEC PLUSIEURS STRATÉGIES >>>
            path_to_model_dir = None
            
            # Stratégie 1 : Chemin idéal (sous-dossier 'temp_...')
            potential_path_1 = os.path.join(temp_output_folder, f"temp_{unique_id}")
            if os.path.exists(os.path.join(potential_path_1, "predictor.pkl")):
                path_to_model_dir = potential_path_1
                print(f"Stratégie 1 réussie : Modèle trouvé dans {path_to_model_dir}")

            # Stratégie 2 : Chemin "plat" de Windows (fichier avec '\' à la racine)
            if not path_to_model_dir:
                # Note: On doit construire le chemin avec l'antislash de Windows
                win_style_filename = f"temp_{unique_id}\\predictor.pkl"
                potential_path_2 = os.path.join(temp_output_folder, win_style_filename)
                if os.path.exists(potential_path_2):
                    # On doit charger le dossier qui contient ce fichier
                    path_to_model_dir = os.path.dirname(potential_path_2)
                    print(f"Stratégie 2 réussie : Modèle Windows trouvé dans {path_to_model_dir}")
            
            # Stratégie 3 : Recherche récursive de secours
            if not path_to_model_dir:
                print("Stratégies 1 et 2 échouées. Lancement de la recherche récursive de secours...")
                for root, dirs, files in os.walk(temp_output_folder):
                    if "predictor.pkl" in files:
                        path_to_model_dir = root
                        print(f"Stratégie 3 réussie : Modèle trouvé par scan récursif dans {path_to_model_dir}")
                        break
            
            if not path_to_model_dir:
                raise FileNotFoundError("Impossible de trouver 'predictor.pkl' avec toutes les stratégies de recherche.")
            # <<< FIN DE LA CORRECTION >>>

            predictor = TimeSeriesPredictor.load(path_to_model_dir)
            print("✅ Modèle AutoGluon chargé avec succès.")

        except Exception as e:
            print(f"🛑 ERREUR CRITIQUE lors du chargement du modèle: {e}\n{traceback.format_exc()}")
            raise e

        try:
            # === ÉTAPE 2: PRÉPARATION DES DONNÉES ===
            db_password, db_host, db_user, db_name, db_port = (os.environ.get(k) for k in ["DB_PASSWORD", "DB_HOST", "DB_USER", "DB_NAME", "DB_PORT"])
            connection_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            engine = create_engine(connection_str)
            
            df_daily = get_data_with_covariates(config, engine)
            
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
            if donnees_hebdo.empty: raise ValueError("Données vides après nettoyage (dropna).")
            
            if config.get("transformation") == "log":
                donnees_hebdo[predictor.target] = np.log1p(donnees_hebdo[config["original_target_col"]])

            full_data_ts = TimeSeriesDataFrame.from_data_frame(donnees_hebdo, id_column="item_id", timestamp_column="timestamp")
            print("✅ Données prêtes.")

            # === ÉTAPE 3: PRÉDICTION ===
            print("--- 3. Génération des prévisions ---")
            known_covariates_df = None
            prediction_length = predictor.prediction_length

            if future_only:
                data_history = full_data_ts
                if predictor.known_covariates_names:
                    last_known_covariates = full_data_ts.tail(1)[predictor.known_covariates_names]
                    future_covariates_df = pd.concat([last_known_covariates] * prediction_length, ignore_index=True)
                    last_date = full_data_ts.index.get_level_values('timestamp').max()
                    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=7), periods=prediction_length, freq='W-MON')
                    future_covariates_df['timestamp'] = future_dates
                    future_covariates_df['item_id'] = config["category_id_in_file"]
                    known_covariates_df = TimeSeriesDataFrame(future_covariates_df, id_column="item_id", timestamp_column="timestamp")
            else:
                data_history = full_data_ts.slice_by_timestep(end_index=-prediction_length)
                known_covariates_df = full_data_ts.tail(prediction_length) if predictor.known_covariates_names else None
            
            predictions = predictor.predict(data_history, known_covariates=known_covariates_df)

            # === ÉTAPE 4: RETRANSFORMATION ===
            if config.get("transformation") == "log":
                final_predictions = np.expm1(predictions)
            else:
                final_predictions = predictions
            final_predictions = final_predictions.clip(lower=0)
            
            if not future_only and 'actual_sales' in full_data_ts.columns:
                 y_test = full_data_ts.tail(prediction_length)[config["original_target_col"]]
                 final_predictions['actual_sales'] = y_test.values

            print(f"--- Prédiction pour '{unique_id}' terminée avec succès. ---")
            return final_predictions

        except Exception as e:
            print(f"🛑 ERREUR lors de la préparation des données ou de la prédiction pour {unique_id}:\n   Message: {e}\n   Traceback: {traceback.format_exc()}")
            raise e

# --- Point d'entrée pour les tests en local ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lance une prédiction de ventes.")
    parser.add_argument("--category", required=True, help="ID unique de la catégorie.")
    parser.add_argument("--future", action="store_true", help="Si activé, prédit les 12 prochaines semaines.")
    args = parser.parse_args()

    try:
        predictions_df = get_prediction(args.category, future_only=args.future)
        if predictions_df is not None:
            if args.future:
                print("\n--- Prévisions futures ---")
            else:
                print("\n--- Prévisions vs Réalité ---")
            print(predictions_df.round(2))
            print("\n✅ Script terminé avec succès.")
    except Exception as e:
        print(f"\n❌ Le script a échoué. Raison : {e}")