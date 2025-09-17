import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

def create_db_connection():
    """
    Crée et retourne une connexion à la base de données Supabase.
    """
    db_password = os.environ.get("DB_PASSWORD")
    db_host = os.environ.get("DB_HOST")
    db_user = os.environ.get("DB_USER")
    db_name = os.environ.get("DB_NAME")
    db_port = os.environ.get("DB_PORT")

    # Construire la chaîne de connexion
    connection_str = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Créer le "moteur" de connexion
    engine = create_engine(connection_str)
    print("Connexion à la base de données établie avec succès.")
    return engine

# --- Exemple d'utilisation ---
if __name__ == "__main__":
    db_engine = create_db_connection()
    
    # Vous pouvez maintenant lire des données
    df = pd.read_sql("SELECT * FROM sales LIMIT 10", db_engine)
    print(df.head())