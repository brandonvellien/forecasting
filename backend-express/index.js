// Fichier: backend-express/index.js (Version corrigée et complète)

const express = require('express');
const cors = require('cors');
const admin = require('firebase-admin');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');

// --- 1. IMPORTS ET CONFIGURATION ---
// MODIFICATION ICI : On importe les deux fonctions depuis le controller
const { getPredictionsForCategory, getHistoricalForCategory } = require('./controllers/predictionController');
const serviceAccount = require('./secrets/firebase-admin-key.json');

const app = express();
const PORT = 3001;
app.set('trust proxy', 1);

// --- 2. INITIALISATION ET MIDDLEWARES ---
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

// --- AJOUT DES MIDDLEWARES DE SÉCURITÉ ---
app.use(helmet());
app.use(cors());
app.use(express.json());

const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // Fenêtre de 15 minutes
    max: 100, // Limite chaque IP à 100 requêtes par fenêtre
    standardHeaders: true,
    legacyHeaders: false,
    message: 'Trop de requêtes envoyées depuis cette IP, veuillez réessayer dans 15 minutes.',
});

app.use(limiter);
// --- FIN DES AJOUTS DE SÉCURITÉ ---


// Middleware d'authentification (inchangé)
const firebaseAuthMiddleware = async (req, res, next) => {
    const authHeader = req.headers['authorization'];
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).send({ message: 'Accès non autorisé.' });
    }
    const idToken = authHeader.split(' ')[1];
    try {
        req.user = await admin.auth().verifyIdToken(idToken);
        next();
    } catch (error) {
        return res.status(403).send({ message: 'Token invalide.' });
    }
};


// --- 3. ROUTAGE ---
app.get('/api/predictions', firebaseAuthMiddleware, getPredictionsForCategory);

// MODIFICATION ICI : Ajout de la nouvelle route pour l'historique
app.get('/api/historical', firebaseAuthMiddleware, getHistoricalForCategory);


// --- 4. DÉMARRAGE DU SERVEUR ---
app.listen(PORT, () => {
    console.log(`Serveur Express démarré sur http://localhost:${PORT}`);
    // MODIFICATION ICI : Mise à jour du message de log
    console.log("Les requêtes sur /api/predictions et /api/historical sont gérées par le predictionController.");
});