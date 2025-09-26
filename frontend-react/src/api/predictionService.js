// src/api/predictionService.js

import axios from 'axios';
import { auth } from '../firebase';

// --- MODIFICATION ICI ---
// On récupère l'URL de base de l'API depuis les variables d'environnement.
// Si la variable n'existe pas (en local), on utilise http://localhost:3001 par défaut.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3001';

// On construit l'URL complète de l'endpoint
const API_ENDPOINT = `${API_BASE_URL}/api/predictions`;
// --- FIN DE LA MODIFICATION ---


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

// Votre logique existante est conservée, elle est parfaite
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