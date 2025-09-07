# Fichier: backend-express/Dockerfile

# Étape 1: Partir d'une image Node.js officielle et légère (version Long Term Support)
FROM node:20-alpine

# Étape 2: Définir le répertoire de travail à l'intérieur du conteneur
WORKDIR /usr/src/app

# Étape 3: Copier les fichiers de dépendances pour optimiser le cache de Docker
COPY package*.json ./

# Étape 4: Installer les dépendances de production
RUN npm install --production

# Étape 5: Copier le reste du code de l'application
COPY . .

# Étape 6: Exposer le port sur lequel le serveur tourne
EXPOSE 3001

# Étape 7: La commande pour lancer le serveur en production
CMD [ "node", "index.js" ]