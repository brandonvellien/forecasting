// Fichier: src/hooks/usePredictions.js
import { useState, useEffect } from 'react';
import { fetchPredictions } from '../api/predictionService';

export const usePredictions = (categoryId) => {
    const [data, setData] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const getPredictions = async () => {
            try {
                setIsLoading(true);
                const result = await fetchPredictions(categoryId);
                setData(result);
                setError(null);
            } catch (err) {
                setError("Erreur lors de la récupération des prédictions.");
                console.error(err);
            } finally {
                setIsLoading(false);
            }
        };
        getPredictions();
    }, [categoryId]);

    return { data, isLoading, error };
};