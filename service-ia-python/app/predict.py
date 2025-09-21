# Fichier: service-ia-python/app/predict.py (Version finale avec gestion des requêtes concurrentes)

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor
from .config import MODELS_CONFIG
import comet_ml.api
import os
import shutil
from dotenv import load_dotenv
import tempfile # <-- On importe la librairie pour les dossiers temporaires

# Charger les variables d'environnement
load_dotenv()

comet_api = comet_ml.api.API()

def get_data_from_supabase(config):
    """
    Se connecte à Supabase et récupère les données nécessaires. (Inchangé)
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
    FROM sales s
    {joins}
    WHERE s.item_id = '{item_id_to_fetch}'
    ORDER BY s."timestamp";
    """
    
    df = pd.read_sql(final_query, engine, parse_dates=['timestamp'])
    print(f"{len(df)} lignes de données récupérées pour {item_id_to_fetch}.")
    return df

def get_prediction(unique_id: str, future_only: bool = False) -> pd.DataFrame:
    """
    Génère les prévisions de ventes en utilisant un dossier temporaire unique
    pour chaque requête afin d'éviter les conflits.
    """
    print(f"--- Début de la prédiction pour '{unique_id}' ---")
    
    if unique_id not in MODELS_CONFIG:
        raise ValueError(f"L'ID de modèle '{unique_id}' n'a pas été trouvé dans la configuration.")
        
    config = MODELS_CONFIG[unique_id]
    
    # <<< LA CORRECTION EST ICI >>>
    # On crée un dossier temporaire qui sera automatiquement détruit à la fin
    with tempfile.TemporaryDirectory() as temp_output_folder:
        try:
            # 1. Télécharger et charger le modèle dans le dossier temporaire
            workspace = os.environ.get("COMET_WORKSPACE")
            model_name = f"sales-forecast-{unique_id.replace('_', '-')}"
            
            print(f"Téléchargement du modèle '{model_name}' dans {temp_output_folder}")
            
            model_registry_item = comet_api.get_model(workspace=workspace, model_name=model_name)
            latest_version_str = model_registry_item.find_versions()[0]
            model_registry_item.download(version=latest_version_str, output_folder=temp_output_folder, expand=True)
            
            # <<< LA CORRECTION EST ICI >>>
            # On cherche le dossier du modèle dynamiquement au lieu de deviner son nom
            path_to_model = temp_output_folder
            # Si un sous-dossier 'temp_...' existe, on l'utilise
            potential_subfolder = os.path.join(temp_output_folder, f"temp_{unique_id}")
            if os.path.isdir(potential_subfolder):
                 path_to_model = potential_subfolder
            else:
                # Sinon, on cherche le premier dossier qui contient un 'predictor.pkl'
                found = False
                for root, dirs, files in os.walk(temp_output_folder):
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

        # 2. Préparer les données (inchangé)
        print("Préparation des données...")
        df_daily = get_data_from_supabase(config)
        known_covariates = config.get("known_covariates", [])
        agg_config = {'qty_sold': 'sum'}
        for cov in known_covariates: agg_config[cov] = 'mean'
        agg_config['item_id'] = 'first'
        donnees_hebdo = df_daily.set_index('timestamp').resample('W-MON').agg(agg_config).reset_index()
        donnees_hebdo['item_id'] = donnees_hebdo['item_id'].ffill()
        donnees_hebdo.dropna(subset=['item_id'], inplace=True)
        for col in known_covariates:
            donnees_hebdo[col] = donnees_hebdo[col].interpolate().ffill().bfill()
        donnees_hebdo['timestamp'] = pd.to_datetime(donnees_hebdo['timestamp']).dt.tz_localize(None)
        if config.get("transformation") == "log":
            donnees_hebdo[predictor.target] = np.log1p(donnees_hebdo[config["original_target_col"]])
        if config.get("data_filter_start") is not None:
            temp_ts_df = TimeSeriesDataFrame(donnees_hebdo, id_column="item_id", timestamp_column="timestamp")
            start_date = temp_ts_df.loc[config["category_id_in_file"]].index[config["data_filter_start"]]
            donnees_hebdo = donnees_hebdo.query("timestamp >= @start_date")
        full_data_ts = TimeSeriesDataFrame.from_data_frame(donnees_hebdo, id_column="item_id", timestamp_column="timestamp")
        
        prediction_length = predictor.prediction_length
        future_known_covariates = None

        # 3. Préparer les covariables futures (inchangé)
        if future_only:
            print("--- Mode: Prédiction du futur ---")
            data_history = full_data_ts
            if known_covariates:
                last_date = full_data_ts.index.get_level_values('timestamp').max()
                future_dates = pd.date_range(start=last_date + pd.Timedelta(days=7), periods=prediction_length, freq='W-MON')
                future_df = pd.DataFrame({'timestamp': future_dates, 'item_id': config["category_id_in_file"]})
                for col in known_covariates:
                    future_df[col] = full_data_ts.iloc[-1][col]
                future_known_covariates = TimeSeriesDataFrame(future_df, id_column="item_id", timestamp_column="timestamp")
        else:
            print("--- Mode: Test sur les dernières données connues ---")
            data_history = full_data_ts.slice_by_timestep(end_index=-prediction_length)
            future_known_covariates = full_data_ts.tail(prediction_length) if known_covariates else None

        # 4. Faire la prédiction (inchangé)
        print("Génération des prévisions...")
        predictions = predictor.predict(data_history, known_covariates=future_known_covariates)

        if config.get("transformation") == "log":
            final_predictions = np.expm1(predictions)
        else:
            final_predictions = predictions

        final_predictions = final_predictions.clip(lower=0)
        
        if not future_only and known_covariates:
            y_test = future_known_covariates[config["original_target_col"]]
            final_predictions['actual_sales'] = y_test.values
        
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