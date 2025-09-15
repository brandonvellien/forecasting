# Fichier: service-ia-python/training.Dockerfile

# Partir d'une image Python
FROM python:3.10-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les dépendances et les installer
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copier les données et le code source de l'application
COPY ./data /app/data
COPY ./app /app/app

# Définir le point d'entrée : quand le conteneur démarre, il lance le script train.py
ENTRYPOINT ["python3", "app/train.py"]