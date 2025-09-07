# Fichier: service-ia-python/app/predict.py

import pandas as pd
import numpy as np
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor
from .config import MODELS_CONFIG # <-- LA CORRECTION EST ICI

def get_prediction(unique_id: str) -> pd.DataFrame:
    """
    Génère les prévisions de ventes pour une catégorie de produits donnée
    en utilisant le modèle champion pré-entraîné correspondant.

    Args:
        unique_id (str): L'identifiant unique (ex: "ligne1_category1_01").

    Returns:
        pd.DataFrame: Un DataFrame contenant les prévisions.
    """
    print(f"Début de la prédiction pour '{unique_id}'...")
    
    # --- 1. Récupérer la configuration du modèle ---
    if unique_id not in MODELS_CONFIG:
        raise ValueError(f"ID non valide. '{unique_id}' n'est pas dans la configuration.")
    
    config = MODELS_CONFIG[unique_id]
    path_to_model = config["model_path"]
    path_to_data = config["data_source"]
    
    # --- 2. Charger le modèle ---
    try:
        predictor = TimeSeriesPredictor.load(path_to_model)
        print("Modèle chargé avec succès.")
    except Exception as e:
        print(f"🛑 Erreur lors du chargement du modèle : {e}")
        return None

    # --- 3. Préparer les données d'entrée (historique) ---
    print("Préparation des données d'historique...")
    df_ventes = pd.read_csv(path_to_data, parse_dates=['timestamp'])
    df_cat = df_ventes[df_ventes['item_id'] == config["category_id_in_file"]].copy()
    donnees_hebdo = df_cat.groupby('item_id').resample('W-MON', on='timestamp', include_groups=False).sum(numeric_only=True).reset_index()
    donnees_hebdo['item_id'] = config["category_id_in_file"]
    
    # Logique de préparation spécifique au modèle
    if "data_filter_start" in config and config["data_filter_start"] is not None:
        start_date = TimeSeriesDataFrame(donnees_hebdo).loc[config["category_id_in_file"]].index[config["data_filter_start"]]
        donnees_hebdo = donnees_hebdo.query("timestamp >= @start_date")

    if config["transformation"] == "log":
        donnees_hebdo[predictor.target] = np.log1p(donnees_hebdo[config["original_target_col"]])
    elif config["transformation"] == "sqrt":
        donnees_hebdo[predictor.target] = np.sqrt(donnees_hebdo[config["original_target_col"]])
    
    donnees_hebdo.dropna(inplace=True)
    
    data_history = TimeSeriesDataFrame.from_data_frame(
        donnees_hebdo, id_column="item_id", timestamp_column="timestamp")

    # --- 4. Faire la prédiction ---
    print("Génération des prévisions...")
    predictions = predictor.predict(data_history)

    # --- 5. Retransformer et retourner le résultat ---
    if config["transformation"] == "log":
        final_predictions = np.expm1(predictions)
    elif config["transformation"] == "sqrt":
        final_predictions = predictions ** 2
    else:
        final_predictions = predictions

    print(f"Prédiction pour '{unique_id}' terminée.")
    return final_predictions.clip(lower=0)


# --- EXEMPLE D'UTILISATION (pour tester ce script seul) ---
if __name__ == "__main__":
    test_id = "ligne1_category1_01" 
    
    try:
        predictions = get_prediction(test_id)
        if predictions is not None:
            print(f"\n--- Prédictions pour {test_id} ---")
            print(predictions.head().round(2))
    except Exception as e:
        print(f"🛑 Le test a échoué : {e}")