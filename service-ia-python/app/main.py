# Fichier: service-ia-python/app/main.py (Version finale avec Rate Limiting)

from fastapi import FastAPI, HTTPException, Path, Request
from .predict import get_prediction
from dotenv import load_dotenv
import re

# --- 1. IMPORTS POUR SLOWAPI ---
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()

# --- 2. INITIALISATION DU LIMITEUR ---
# On utilise l'adresse IP du client comme clé pour le suivi
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="API de Prédiction des Ventes",
    description="Un service pour prédire les ventes hebdomadaires par catégorie de produits.",
    version="1.0.0"
)

# --- 3. APPLICATION DU LIMITEUR À L'APP FASTAPI ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# L'endpoint de prédiction (inchangé mais avec le décorateur ajouté)
@app.get("/predict/{unique_id}")
@limiter.limit("30/minute") # <-- 4. LIMITE DE 60 REQUÊTES PAR MINUTE
def predict_endpoint(
    request: Request, # <-- Le décorateur a besoin de l'objet Request
    unique_id: str = Path(
        ...,
        title="ID Unique du modèle",
        description="Doit être alphanumérique et peut contenir des tirets et underscores.",
        regex="^[a-zA-Z0-9_-]+$"
    )
):
    """
    Exécute la prédiction pour un ID unique et retourne le résultat au format JSON.
    """
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

# L'endpoint racine (inchangé)
@app.get("/")
def read_root():
    return {"status": "API de prédiction des ventes est en ligne."}