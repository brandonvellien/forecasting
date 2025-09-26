# Fichier: backend-express/Dockerfile (Version finale et explicite)

# Étape 1: Partir d'une image Node.js officielle
FROM node:20-alpine

# Étape 2: Définir le répertoire de travail
WORKDIR /usr/src/app

# Étape 3: Copier les fichiers de dépendances
COPY package.json .
COPY package-lock.json .

# Étape 4: Installer les dépendances
RUN npm ci --only=production

# --- ÉTAPE 5 : COPIE EXPLICITE DES FICHIERS ---
# On copie chaque fichier et dossier nécessaire, un par un.
# CELA GARANTIT QU'ILS SONT BIEN PRÉSENTS.
COPY index.js .
COPY controllers ./controllers

# Étape 6: Créer un utilisateur non-root
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Étape 7: Exposer le port
EXPOSE 3001

# Étape 8: La commande pour lancer le serveur
CMD [ "node", "index.js" ]