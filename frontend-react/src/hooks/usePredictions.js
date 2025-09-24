// src/hooks/usePredictions.js

import { useState, useEffect } from 'react';
// 1. On importe la nouvelle fonction 'getPredictions'
import { getPredictions } from '../api/predictionService';

const usePredictions = (categoryId) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // La logique interne du hook ne change pas
    const loadPredictions = async () => {
      try {
        setError(null);
        setLoading(true);
        // 2. On appelle la nouvelle fonction 'getPredictions'
        const predictionData = await getPredictions(categoryId);
        setData(predictionData);
      } catch (err) {
        // On s'assure que si l'erreur vient du token (ex: expiré), l'utilisateur le sache.
        if (err.message.includes('connecté')) {
            setError(new Error('Session expirée. Veuillez vous reconnecter.'));
        } else {
            setError(err);
        }
      } finally {
        setLoading(false);
      }
    };

    if (categoryId) {
      loadPredictions();
    }
  }, [categoryId]);

  return { data, loading, error };
};

export default usePredictions;