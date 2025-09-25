# Fichier: service-ia-python/Dockerfile

# Étape 1: Partir d'une image Python officielle et légère
FROM python:3.10-slim


# --- FIN DE L'AJOUT ---
# Étape 2: Définir le répertoire de travail à l'intérieur du conteneur
WORKDIR /app

# Étape 3: Copier le fichier des dépendances
COPY requirements.txt requirements.txt

# Étape 4: Installer les dépendances
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Étape 5: Copier le code source de l'application (le dossier 'app')
COPY ./app /app/app
# --- AJOUT DE SÉCURITÉ ---
# Crée un groupe applicatif et un utilisateur applicatif non-root
RUN addgroup --system appgroup && adduser --system --ingroup appgroup --no-create-home appuser

# Spécifie que toutes les commandes suivantes doivent être exécutées par cet utilisateur
USER appuser

# Étape 6: Exposer le port sur lequel l'API va tourner
EXPOSE 8000

# Étape 7: La commande pour lancer l'API au démarrage du conteneur
# Note: On utilise --host 0.0.0.0 pour rendre le serveur accessible depuis l'extérieur du conteneur
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]