# Fichier: service-ia-python/app/config.py (Version finale pour Supabase)
from pathlib import Path

SERVICE_ROOT = Path(__file__).parent.parent
MODELS_ROOT = SERVICE_ROOT / "AutogluonModels"
# La référence à DATA_ROOT n'est plus nécessaire

# ==============================================================================
# --- REGISTRE DES MODÈLES ---
# ==============================================================================
MODELS_CONFIG = {
    "ligne1_category1_01": {
        "category_id_in_file": "category1_01",
        "original_target_col": "qty_sold",
        "data_filter_start": 118,
        # Pour ce modèle, nous n'utilisons aucune donnée externe.
        "known_covariates": []
    },

    "ligne1_category1_08": {
        "category_id_in_file": "category1_08",
        "original_target_col": "qty_sold",
        "data_filter_start": 52,
        "transformation": "log",  # <-- NOUVEAU: Spécifie la transformation log
        "known_covariates": [     # <-- NOUVEAU: Liste des données externes
            "temperature_mean",
            "rain",
            "ipc",
            "moral_menages"
        ],
        "hyperparameters": {
            'context_length': 36,
            'hidden_dim': 64,
            'dropout_rate': 0.2,
            'max_epochs': 80,
            'early_stopping_patience': 15
        }
        
    }
    
    # --- EXEMPLE POUR UN FUTUR MODÈLE UTILISANT DES DONNÉES EXTERNES ---
    # "ligne2_category1_08": {
    #     "category_id_in_file": "category1_08",
    #     "original_target_col": "qty_sold",
    #     # Pour ce modèle, on spécifie les données à joindre
    #     "known_covariates": [
    #         "temperature_mean",
    #         "precipitation",
    #         "ipc_clothing_shoes",
    #         "household_confidence"
    #     ]
    # },
}