# Fichier: service-ia-python/app/main.py

from fastapi import FastAPI, HTTPException, Path, Request, Query
# --- 1. IMPORTER LES NOUVEAUX ÉLÉMENTS ---
from datetime import date
from .predict import get_prediction
from .historical import get_historical_data # <-- AJOUT
from dotenv import load_dotenv
import re

# --- IMPORTS POUR SLOWAPI (inchangés) ---
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

# --- INITIALISATION (inchangée) ---
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="API de Prédiction des Ventes",
    description="Un service pour prédire les ventes hebdomadaires et consulter l'historique.",
    version="1.1.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- ENDPOINT DE PRÉDICTION (inchangé) ---
@app.get("/predict/{unique_id}")
@limiter.limit("30/minute")
def predict_endpoint(
    request: Request,
    unique_id: str = Path(
        ...,
        title="ID Unique du modèle",
        description="Doit être alphanumérique et peut contenir des tirets et underscores."
    )
):
    print(f"Demande de prédiction API reçue pour : {unique_id}")
    try:
        predictions_df = get_prediction(unique_id, future_only=True)
        if predictions_df is None:
             raise HTTPException(status_code=500, detail="La prédiction a échoué.")
        
        return predictions_df.reset_index().to_dict(orient="records")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Une erreur interne est survenue : {e}")

# --- 2. AJOUT DU NOUVEL ENDPOINT POUR L'HISTORIQUE ---
@app.get("/historical/{unique_id}")
@limiter.limit("30/minute")
def historical_endpoint(
    request: Request,
    unique_id: str = Path(
        ...,
        title="ID Unique de la catégorie",
        description="L'ID utilisé pour la prédiction (ex: ligne1_category1_01)."
    ),
    start_date: date = Query(..., description="Date de début de la période de prédiction (YYYY-MM-DD)."),
    end_date: date = Query(..., description="Date de fin de la période de prédiction (YYYY-MM-DD).")
):
    """
    Récupère les données de ventes N-1 pour une période donnée.
    """
    print(f"Demande de données historiques reçue pour {unique_id} entre {start_date} et {end_date}")
    try:
        historical_df = get_historical_data(unique_id, start_date, end_date)
        if historical_df is None:
            # Si aucune donnée n'est trouvée, retourner une liste vide est plus simple pour le frontend
            return []
        
        # Convertir les Timestamps en chaînes de caractères au format ISO
        historical_df['timestamp'] = historical_df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')

        return historical_df.to_dict(orient="records")

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Une erreur interne est survenue : {e}")


# --- ENDPOINT RACINE (inchangé) ---
@app.get("/")
def read_root():
    return {"status": "API de prédiction des ventes est en ligne."}