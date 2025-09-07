const express = require('express');
const axios = require('axios');
const cors = require('cors');

const app = express();
const PORT = 3001;

app.use(cors());

const IA_SERVICE_URL = process.env.IA_SERVICE_URL || "http://127.0.0.1:8000";

// LIGNE DE DÉBUGGAGE : Affiche l'URL que Node.js va utiliser
console.log(`Le service IA sera contacté à l'adresse : ${IA_SERVICE_URL}`);

app.get('/api/forecast/:unique_id', async (req, res) => {
    const { unique_id } = req.params;
    console.log(`Reçu une demande pour la prévision de : ${unique_id}`);

    try {
        const response = await axios.get(`${IA_SERVICE_URL}/predict/${unique_id}`);
        res.json(response.data);
    } catch (error) {
        // Affiche une erreur plus détaillée dans la console du backend
        console.error("Erreur détaillée lors de l'appel au service IA:", error.code, "à l'adresse", error.config.url);
        res.status(500).json({ message: "Le service de prédiction est indisponible." });
    }
});

app.listen(PORT, () => {
    console.log(`Serveur Express démarré sur http://localhost:${PORT}`);
});