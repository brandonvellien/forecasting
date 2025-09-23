# Fichier: service-ia-python/app/config.py (Version finale pour Supabase)
from pathlib import Path

SERVICE_ROOT = Path(__file__).parent.parent
MODELS_ROOT = SERVICE_ROOT / "AutogluonModels"
# La référence à DATA_ROOT n'est plus nécessaire

# ==============================================================================
# --- REGISTRE DES MODÈLES ---
# ==============================================================================
# Fichier: service-ia-python/app/config.py (Version finale corrigée et complète)

MODELS_CONFIG = {
    "ligne1_category1_01": {
        "source_table": "sales",
        "category_id_in_file": "category1_01",
        "original_target_col": "qty_sold",
        "transformation": None,  # Pas de transformation log
        "data_filter_start": 118, # Le filtre de date correct
        "known_covariates": [],
        # On spécifie le modèle et ses hyperparamètres
        "hyperparameters": {
            'model': 'TemporalFusionTransformer',
            'context_length': 36,      # prediction_length * 3
            'hidden_dim': 64,
            'dropout_rate': 0.1,
            'max_epochs': 120,
            'early_stopping_patience': 20
        }
    },
    "ligne1_category1_08": {
        "source_table": "sales",  # <-- CORRECTION AJOUTÉE
        "category_id_in_file": "category1_08",
        "original_target_col": "qty_sold",
        "transformation": "log",
        "data_filter_start": 52,
        "known_covariates": ["temperature_mean", "rain", "ipc", "moral_menages"],
        "hyperparameters": {
            'model': 'TemporalFusionTransformer',
            'context_length': 36,
            'hidden_dim': 64,
            'dropout_rate': 0.2,
            'max_epochs': 80,
            'early_stopping_patience': 15
        }
    },
    "ligne1_category1_CA": {
        "source_table": "sales",  # <-- CORRECTION AJOUTÉE
        "category_id_in_file": "category1_CA",
        "original_target_col": "qty_sold",
        "transformation": "log",
        "data_filter_start": 35,
        "known_covariates": [],
        "time_limit": 600,
        "hyperparameters": {
            'model': 'TemporalFusionTransformer',
            'context_length': 36,
            'hidden_dim': 64,
            'num_heads': 4,
            'dropout_rate': 0.2,
            'lr': 0.001,
            'max_epochs': 130,
            'early_stopping_patience': 15
        }
    },
    "ligne2_category1_08": {
        "source_table": "sales_product_line_2",
        "category_id_in_file": "category1_08",
        "original_target_col": "qty_sold",
        "transformation": "log",
        "training_start_date": "2021-02-01",
        "feature_engineering": {
            "lags": [1],
            "rolling_means": [4]
        },
        "hyperparameters": {
            "model": "PatchTST",
            'context_length': 48,
            'patch_len': 8,
            'stride': 4,
            'd_model': 64,
            'nhead': 8,
            'num_encoder_layers': 3,
            'max_epochs': 100,
            'early_stopping_patience': 15
        }
    },
    
    "ligne2_category1_CA": {
        "source_table": "sales_product_line_2", # Table pour la ligne de produits 2
        "category_id_in_file": "category1_CA",
        "original_target_col": "qty_sold",
        "transformation": "log",
        "data_filter_start": 13,
        "known_covariates": [],
        "hyperparameters": {
            "model": "DeepAR", # Le nouveau modèle
            'context_length': 24, # prediction_length * 2
            'num_layers': 2,
            'hidden_size': 40,
            'dropout_rate': 0.1,
            'max_epochs': 50,
            'early_stopping_patience': 10
        }
    }
}