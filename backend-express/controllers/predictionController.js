const axios = require('axios');
const IA_SERVICE_URL = process.env.IA_SERVICE_URL || "http://127.0.0.1:8000";

// Voici la fonction qui contient toute la logique métier
const getPredictionsForCategory = async (req, res) => {
    // 1. On récupère l'ID de la catégorie depuis la requête
    const { id } = req.query;
    console.log(`[Controller] Demande de prévision pour : ${id}`);

    // 2. On appelle le service d'IA
    try {
        const response = await axios.get(`${IA_SERVICE_URL}/predict/${id}`);
        const rawData = response.data;

        // 3. On vérifie et transforme les données (le travail du "traducteur")
        if (!Array.isArray(rawData) || rawData.length === 0) {
            return res.json({ dates: [], predicted_sales_mean: [], predicted_sales_lower: [], predicted_sales_upper: [] });
        }

        const formattedData = {
            dates: rawData.map(item => item.timestamp),
            predicted_sales_mean: rawData.map(item => item.mean),
            predicted_sales_lower: rawData.map(item => item['0.1']),
            predicted_sales_upper: rawData.map(item => item['0.9'])
        };
        
        // 4. On renvoie la réponse JSON parfaitement formatée
        res.json(formattedData);

    } catch (error) {
        console.error(`[Controller] Erreur lors de l'appel au service IA pour ${id}:`, error.code);
        res.status(500).json({ message: "Le service de prédiction est indisponible." });
    }
};

// On exporte la fonction pour que index.js puisse l'utiliser
module.exports = {
    getPredictionsForCategory
};