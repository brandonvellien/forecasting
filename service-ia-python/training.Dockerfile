# Fichier: service-ia-python/training.Dockerfile (Version corrigée pour le GPU)

# ÉTAPE 1: Utiliser une image de base NVIDIA qui inclut les outils CUDA.
# C'est l'étape la plus importante pour la compatibilité GPU.
FROM nvidia/cuda:12.1.0-base-ubuntu22.04

# ÉTAPE 2: Installer les dépendances système comme Python et Git.
# On installe git pour résoudre l'avertissement que vous aviez dans les logs.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# ÉTAPE 3: Copier et installer vos requirements Python.
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# ÉTAPE 4: Copier le reste de votre code d'application.
COPY . .

# ÉTAPE 5: Définir le point d'entrée pour lancer l'entraînement.
ENTRYPOINT ["python3", "app/train.py"]