// src/hooks/useHistoricalData.js

import { useState, useEffect } from 'react';
import { getHistoricalData } from '../api/predictionService';

const useHistoricalData = (categoryId, startDate, endDate, enabled) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Ne fait rien si l'interrupteur est désactivé ou si les dates manquent
        if (!enabled || !categoryId || !startDate || !endDate) {
            setData(null); // Vider les données si on désactive
            return;
        }

        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);
                const result = await getHistoricalData(categoryId, startDate, endDate);
                setData(result);
            } catch (err) {
                setError(err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [categoryId, startDate, endDate, enabled]); // Se redéclenche si l'un de ces éléments change

    return { data, loading, error };
};

export default useHistoricalData;