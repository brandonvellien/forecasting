# Fichier: service-ia-python/app/main.py

from fastapi import FastAPI, HTTPException
from .predict import get_prediction
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="API de Prédiction des Ventes",
    description="Un service pour prédire les ventes hebdomadaires par catégorie de produits.",
    version="1.0.0"
)

@app.get("/predict/{unique_id}")
def predict_endpoint(unique_id: str):
    """
    Exécute la prédiction pour un ID unique et retourne le résultat au format JSON.
    """
    print(f"Demande de prédiction API reçue pour : {unique_id}")
    try:
        predictions_df = get_prediction(unique_id)
        if predictions_df is None:
             raise HTTPException(status_code=500, detail="La prédiction a échoué.")
        
        # Convertit le DataFrame en JSON pour la réponse API
        return predictions_df.reset_index().to_dict(orient="records")

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Une erreur interne est survenue : {e}")

@app.get("/")
def read_root():
    return {"status": "API de prédiction des ventes est en ligne."}