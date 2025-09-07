# Fichier: service-ia-python/app/config.py
from pathlib import Path

# La racine de notre service Python est le dossier parent de 'app'
SERVICE_ROOT = Path(__file__).parent.parent 

# On construit les chemins à l'intérieur de notre service
MODELS_ROOT = SERVICE_ROOT / "AutogluonModels"
DATA_ROOT = SERVICE_ROOT / "data"

# ==============================================================================
# --- REGISTRE DES MODÈLES CHAMPIONS ---
# ==============================================================================
MODELS_CONFIG = {
    "ligne1_category1_01": {
        "model_path": str(MODELS_ROOT / "ts_TFT_ONLY_category1_01"),
        "category_id_in_file": "category1_01",
        "data_source": str(DATA_ROOT / "ventes_paris_ligne1_par_categorie.csv"),
        "transformation": None,
        "data_filter_start": 118,
        "model_type": "univariate",
        "original_target_col": "qty_sold"
    },
    # --- Ajoutez vos autres modèles champions ici ---
    # "ligne2_category1_08": { ... },
}