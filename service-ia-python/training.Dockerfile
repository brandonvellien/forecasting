# Fichier: service-ia-python/training.Dockerfile (Version finale corrigée et robuste pour GPU)

# ÉTAPE 1: Utiliser une image de base NVIDIA qui inclut les outils CUDA.
FROM nvidia/cuda:12.1.0-base-ubuntu22.04

# ÉTAPE 2: Installer Python et créer un alias pour la commande 'python'.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    # Crée un lien pour que 'python' pointe vers 'python3'. C'est la correction clé.
    && ln -s /usr/bin/python3 /usr/bin/python

# ÉTAPE 3: Copier et installer vos requirements Python.
WORKDIR /app
COPY requirements.txt .
# Utiliser 'python' (maintenant disponible grâce à l'alias) pour plus de cohérence
RUN python -m pip install --no-cache-dir --upgrade pip
RUN python -m pip install --no-cache-dir -r requirements.txt

# ÉTAPE 4: Copier le reste de votre code d'application.
# On copie uniquement le dossier 'app' qui contient le code nécessaire.
COPY ./app ./app

# Il n'y a plus besoin de ENTRYPOINT ici, car il est défini dans le workflow YAML.