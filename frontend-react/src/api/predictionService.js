// src/api/predictionService.js (Version corrigée et complète)

import axios from 'axios';
import { auth } from '../firebase';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001';
const PREDICTIONS_ENDPOINT = `${API_BASE_URL}/api/predictions`;
// AJOUT : L'URL pour la nouvelle route
const HISTORICAL_ENDPOINT = `${API_BASE_URL}/api/historical`;

// Fonction pour obtenir les en-têtes d'authentification (inchangée)
const getAuthHeaders = async () => {
    const user = auth.currentUser;
    if (!user) {
        throw new Error('Aucun utilisateur n\'est connecté.');
    }
    const token = await user.getIdToken();
    return {
        headers: {
            'Authorization': `Bearer ${token}`,
        },
    };
};

// Fonction pour les prédictions (inchangée)
export const getPredictions = async (categoryId) => {
  try {
    const config = {
      ...(await getAuthHeaders()),
      params: {
        id: categoryId
      }
    };
    const response = await axios.get(PREDICTIONS_ENDPOINT, config);
    return response.data;

  } catch (error) {
    console.error('Erreur lors de la récupération des prédictions:', error);
    throw error;
  }
};

// --- NOUVELLE FONCTION AJOUTÉE ---
// Elle appellera la route /api/historical avec les bons paramètres
export const getHistoricalData = async (categoryId, startDate, endDate) => {
    try {
        const config = {
            ...(await getAuthHeaders()),
            params: {
                id: categoryId,
                start_date: startDate,
                end_date: endDate
            }
        };
        const response = await axios.get(HISTORICAL_ENDPOINT, config);
        return response.data; // Renvoie le tableau de données historiques
    } catch (error) {
        console.error('Erreur lors de la récupération des données historiques:', error);
        throw []; // En cas d'erreur, on renvoie un tableau vide pour ne pas faire planter le graphique
    }
};