# Fichier: service-ia-python/app/predict.py (Version finale avec le bon chemin de chargement)

import pandas as pd
import numpy as np
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor
from .config import MODELS_CONFIG
import comet_ml.api
import os
import shutil

comet_api = comet_ml.api.API()

def get_prediction(unique_id: str) -> pd.DataFrame:
    """
    Génère les prévisions de ventes en téléchargeant et utilisant
    le dernier modèle depuis le registre de Comet.
    """
    print(f"--- Début de la prédiction pour '{unique_id}' ---")
    
    config = MODELS_CONFIG[unique_id]
    path_to_data = config["data_source"]
    
    output_folder = "downloaded_model"
    path_to_model = ""

    try:
        workspace = os.environ.get("COMET_WORKSPACE")
        model_name = f"sales-forecast-{unique_id}"
        
        print(f"Téléchargement du modèle '{model_name}' depuis Comet (Workspace: {workspace})...")
        
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)

        model_registry_item = comet_api.get_model(workspace=workspace, model_name=model_name)
        
        latest_version_str = model_registry_item.find_versions()[0]
        print(f"Dernière version trouvée : {latest_version_str}")

        model_registry_item.download(
            version=latest_version_str, 
            output_folder=output_folder, 
            expand=True
        )
        
        # <<< CORRECTION FINALE ICI >>>
        # Le modèle AutoGluon est dans un sous-dossier. Nous devons le trouver.
        # Le nom du dossier correspond au `local_model_path` dans train.py
        model_subfolder = f"temp_{unique_id}"
        path_to_model = os.path.join(output_folder, model_subfolder)
        
        print(f"Modèle téléchargé. Chemin du prédicteur : {path_to_model}")

    except Exception as e:
        print(f"🛑 Erreur lors du téléchargement du modèle depuis Comet : {e}")
        print("Tentative de chargement du modèle local comme solution de secours...")
        path_to_model = config.get("model_path")
        if not path_to_model or not os.path.exists(path_to_model):
            print(f"🛑 Aucun modèle local de secours trouvé.")
            return None

    # --- 3. Charger le modèle ---
    try:
        predictor = TimeSeriesPredictor.load(path_to_model)
        print("Modèle AutoGluon chargé avec succès.")
    except Exception as e:
        print(f"🛑 Erreur lors du chargement du modèle AutoGluon depuis '{path_to_model}': {e}")
        return None

    # --- 4. Préparer les données d'historique (inchangé) ---
    print("Préparation des données d'historique...")
    df_ventes = pd.read_csv(path_to_data, parse_dates=['timestamp'])
    df_cat = df_ventes[df_ventes['item_id'] == config["category_id_in_file"]].copy()
    donnees_hebdo = df_cat.groupby('item_id').resample('W-MON', on='timestamp', include_groups=False).sum(numeric_only=True).reset_index()
    donnees_hebdo['item_id'] = config["category_id_in_file"]
    
    if "data_filter_start" in config and config["data_filter_start"] is not None:
        temp_df = TimeSeriesDataFrame(donnees_hebdo, id_column="item_id", timestamp_column="timestamp")
        start_date = temp_df.loc[config["category_id_in_file"]].index[config["data_filter_start"]]
        donnees_hebdo = donnees_hebdo.query("timestamp >= @start_date")

    if config.get("transformation") == "log":
        donnees_hebdo[predictor.target] = np.log1p(donnees_hebdo[config["original_target_col"]])
    elif config.get("transformation") == "sqrt":
        donnees_hebdo[predictor.target] = np.sqrt(donnees_hebdo[config["original_target_col"]])
    
    donnees_hebdo.dropna(inplace=True)
    
    data_history = TimeSeriesDataFrame.from_data_frame(
        donnees_hebdo, id_column="item_id", timestamp_column="timestamp")

    # --- 5. Faire la prédiction et retourner le résultat ---
    print("Génération des prévisions...")
    predictions = predictor.predict(data_history)

    if config.get("transformation") == "log":
        final_predictions = np.expm1(predictions)
    elif config.get("transformation") == "sqrt":
        final_predictions = predictions ** 2
    else:
        final_predictions = predictions

    print(f"--- Prédiction pour '{unique_id}' terminée. ---")
    return final_predictions.clip(lower=0)