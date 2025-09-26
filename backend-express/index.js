// Fichier: backend-express/index.js (Version finale avec Helmet et Rate Limiting)

const express = require('express');
const cors = require('cors');
const admin = require('firebase-admin');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet'); // <--- 1. IMPORTEZ HELMET

// --- 1. IMPORTS ET CONFIGURATION ---
const { getPredictionsForCategory } = require('./controllers/predictionController');
const serviceAccount = require('./secrets/firebase-admin-key.json');

const app = express();
const PORT = 3001;
app.set('trust proxy', 1); 

// --- 2. INITIALISATION ET MIDDLEWARES ---
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

// --- AJOUT DES MIDDLEWARES DE SÉCURITÉ ---
// 2. APPLIQUEZ HELMET
// Ajoute plusieurs en-têtes de sécurité, y compris une Content-Security-Policy de base.
app.use(helmet()); 

app.use(cors());
app.use(express.json());

// 3. CONFIGUREZ LE LIMITEUR DE DÉBIT (DDoS)
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // Fenêtre de 15 minutes
    max: 100, // Limite chaque IP à 100 requêtes par fenêtre
    standardHeaders: true,
    legacyHeaders: false,
    message: 'Trop de requêtes envoyées depuis cette IP, veuillez réessayer dans 15 minutes.',
});

// 4. APPLIQUEZ LE LIMITEUR À TOUTES LES REQUÊTES
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


// --- 4. DÉMARRAGE DU SERVEUR ---
app.listen(PORT, () => {
    console.log(`Serveur Express démarré sur http://localhost:${PORT}`);
    console.log("Les requêtes sur /api/predictions seront gérées par le predictionController.");
});