const express = require('express');
const cors = require('cors');
const admin = require('firebase-admin');

// --- 1. IMPORTS ET CONFIGURATION ---
const { getPredictionsForCategory } = require('./controllers/predictionController');
const serviceAccount = require('./firebase-admin-key.json');

const app = express();
const PORT = 3001;

// --- 2. INITIALISATION ET MIDDLEWARES ---
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

app.use(cors());
app.use(express.json());

// Middleware d'authentification (ne change pas)
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
// La route est maintenant très simple : elle applique le middleware et appelle le contrôleur.
app.get('/api/predictions', firebaseAuthMiddleware, getPredictionsForCategory);


// --- 4. DÉMARRAGE DU SERVEUR ---
app.listen(PORT, () => {
    console.log(`Serveur Express démarré sur http://localhost:${PORT}`);
    console.log("Les requêtes sur /api/predictions seront gérées par le predictionController.");
});