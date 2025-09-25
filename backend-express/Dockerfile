# Fichier: backend-express/Dockerfile (Version finale et correcte)

# Étape 1: Partir d'une image Node.js officielle et légère
FROM node:20-alpine

# Étape 2: Définir le répertoire de travail
WORKDIR /usr/src/app

# Étape 3: Copier les fichiers de dépendances pour optimiser le cache
COPY package*.json ./

# Étape 4: Installer les dépendances de production
RUN npm ci --only=production

# Étape 5: Copier TOUT le reste du code de l'application
COPY . .

# Étape 6: Créer un utilisateur non-root pour la sécurité
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Étape 7: Exposer le port sur lequel le serveur écoute
EXPOSE 3001

# Étape 8: La commande pour lancer le serveur
CMD [ "node", "index.js" ]