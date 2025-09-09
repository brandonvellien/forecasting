// Fichier: src/api/predictionService.js
import axios from 'axios';

const BACKEND_URL = "http://localhost:3001"; // L'URL de votre backend Express

export const fetchPredictions = async (uniqueId) => {
    const response = await axios.get(`${BACKEND_URL}/api/forecast/${uniqueId}`);
    return response.data;
};