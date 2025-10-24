// Fichier: backend-express/controllers/predictionController.js (Version corrigée et simplifiée)

const axios = require('axios');
const { GoogleAuth } = require('google-auth-library');

const IA_SERVICE_URL = process.env.IA_SERVICE_URL || "http://127.0.0.1:8000";
const IS_PRODUCTION = process.env.NODE_ENV === 'production';

const auth = IS_PRODUCTION ? new GoogleAuth() : null;
let client;

const makeIaRequest = async (url) => {
    if (IS_PRODUCTION) {
        if (!client) {
            client = await auth.getIdTokenClient(IA_SERVICE_URL);
        }
        return client.request({ url });
    } else {
        return axios.get(url);
    }
};

// =================================================================
// FONCTION 1 : Gère UNIQUEMENT les prédictions (ne change pas)
// =================================================================
const getPredictionsForCategory = async (req, res) => {
    const { id } = req.query;
    console.log(`[Controller] Demande de prévision pour : ${id}`);

    const url = `${IA_SERVICE_URL}/predict/${id}`;

    try {
        const response = await makeIaRequest(url);
        const rawData = response.data;

        if (!Array.isArray(rawData) || rawData.length === 0) {
            return res.json({ dates: [], predicted_sales_mean: [], predicted_sales_lower: [], predicted_sales_upper: [] });
        }

        // On garde le formatage car le frontend original en dépend
        const formattedData = {
            dates: rawData.map(item => item.timestamp),
            predicted_sales_mean: rawData.map(item => item.mean),
            predicted_sales_lower: rawData.map(item => item['0.1']),
            predicted_sales_upper: rawData.map(item => item['0.9'])
        };

        res.json(formattedData);

    } catch (error) {
        console.error(`[Controller] Erreur critique pour les prédictions de ${id}:`, error.message);
        res.status(500).json({ message: "Le service de prédiction est indisponible." });
    }
};

// =================================================================
// FONCTION 2 : Gère UNIQUEMENT les données historiques N-1
// =================================================================
const getHistoricalForCategory = async (req, res) => {
    const { id, start_date, end_date } = req.query;
    console.log(`[Controller] Demande d'historique reçue pour : ${id} de ${start_date} à ${end_date}`);

    const url = `${IA_SERVICE_URL}/historical/${id}?start_date=${start_date}&end_date=${end_date}`;

    try {
        const response = await makeIaRequest(url);
        // On transfère la réponse JSON (qui est un tableau) directement au frontend
        res.json(response.data);

    } catch (error) {
        console.error(`[Controller] Erreur lors de la récupération de l'historique pour ${id}:`, error.message);
        res.status(500).json({ message: "Le service de données historiques est indisponible." });
    }
};


// On exporte les DEUX fonctions
module.exports = {
    getPredictionsForCategory,
    getHistoricalForCategory
};