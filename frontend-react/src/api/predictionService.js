// src/api/predictionService.js

import axios from 'axios';
import { auth } from '../firebase';

// On définit l'URL de base de notre API
const API_ENDPOINT = 'http://localhost:3001/api/predictions';

// Cette fonction ne change pas
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

// On utilise maintenant une méthode plus propre pour construire la requête
export const getPredictions = async (categoryId) => {
  try {
    const authConfig = await getAuthHeaders();

    // On crée un objet de configuration pour Axios
    const config = {
      ...authConfig, // On inclut les en-têtes d'authentification
      params: {
        id: categoryId // Axios va transformer ceci en "?id=valeur" dans l'URL
      }
    };

    const response = await axios.get(API_ENDPOINT, config);
    return response.data;
    
  } catch (error) {
    // Ce log est important pour voir les erreurs détaillées dans la console du navigateur
    console.error('Erreur lors de la récupération des prédictions:', error);
    throw error;
  }
};