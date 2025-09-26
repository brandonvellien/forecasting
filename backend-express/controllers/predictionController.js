const axios = require('axios');
const { GoogleAuth } = require('google-auth-library');

const IA_SERVICE_URL = process.env.IA_SERVICE_URL || "http://127.0.0.1:8000";
const IS_PRODUCTION = process.env.NODE_ENV === 'production';

// On prépare l'authentification seulement si on est en production
const auth = IS_PRODUCTION ? new GoogleAuth() : null;
let client;

const getPredictionsForCategory = async (req, res) => {
    const { id } = req.query;
    console.log(`[Controller] Demande de prévision pour : ${id}`);

    const url = `${IA_SERVICE_URL}/predict/${id}`;

    try {
        let response;

        // On choisit la méthode d'appel en fonction de l'environnement
        if (IS_PRODUCTION) {
            // --- Logique de PRODUCTION ---
            if (!client) {
                client = await auth.getIdTokenClient(IA_SERVICE_URL);
            }
            response = await client.request({ url });
        } else {
            // --- Logique LOCALE ---
            response = await axios.get(url);
        }

        const rawData = response.data;

        // Le reste du code est identique
        if (!Array.isArray(rawData) || rawData.length === 0) {
            return res.json({ dates: [], predicted_sales_mean: [], predicted_sales_lower: [], predicted_sales_upper: [] });
        }

        const formattedData = {
            dates: rawData.map(item => item.timestamp),
            predicted_sales_mean: rawData.map(item => item.mean),
            predicted_sales_lower: rawData.map(item => item['0.1']),
            predicted_sales_upper: rawData.map(item => item['0.9'])
        };

        res.json(formattedData);

    } catch (error) {
        if (error.response) {
            console.error(`[Controller] Erreur ${error.response.status} du service IA:`, error.response.data);
        } else {
            console.error(`[Controller] Erreur de communication avec le service IA pour ${id}:`, error.message);
        }
        res.status(500).json({ message: "Le service de prédiction est indisponible." });
    }
};

module.exports = {
    getPredictionsForCategory
};