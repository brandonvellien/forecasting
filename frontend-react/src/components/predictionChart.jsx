import React from 'react';
import { Card, Title, Loader, Alert, Text, Paper } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { usePredictions } from '../hooks/usePredictions';
import {
  ResponsiveContainer,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Line,
  Area,
} from 'recharts';

const PredictionChart = ({ categoryId }) => {
    const { data, isLoading, error } = usePredictions(categoryId);

    if (isLoading) {
        return <Paper withBorder shadow="md" p="xl" radius="md"><Loader /></Paper>;
    }

    if (error) {
        return (
            <Alert icon={<IconAlertCircle size="1rem" />} title="Erreur !" color="red" mt="md">
                {error}
            </Alert>
        );
    }
    
    // Formatter les données pour le graphique
    const chartData = data.map(item => ({
        ...item,
        date: new Date(item.timestamp).toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' }),
        Prédiction: item['0.5'],
        'Ventes Réelles': item.actual, // Ajout de la colonne pour les ventes réelles si disponible
        intervalle: [item['0.1'], item['0.9']], // Utilisé pour l'aire
    }));

    return (
        <Paper withBorder shadow="md" p="xl" radius="md" mt="xl">
            <Title order={3}>
                Prédictions pour : <Text span c="blue" inherit>{categoryId}</Text>
            </Title>
            <div style={{ width: '100%', height: 400, marginTop: '20px' }}>
                <ResponsiveContainer>
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        
                        {/* L'intervalle de confiance en gris */}
                        <Area 
                            type="monotone" 
                            dataKey="intervalle" 
                            stroke={false} 
                            fill="#912139ff" 
                            fillOpacity={0.8} 
                            name="Intervalle de confiance 80%" 
                        />
                        
                        {/* La ligne des ventes réelles (si elles existent dans les données) */}
                        {chartData[0]['Ventes Réelles'] !== undefined && (
                            <Line 
                                type="monotone" 
                                dataKey="Ventes Réelles" 
                                stroke="#ff7300" 
                                strokeWidth={2} 
                                dot={{ r: 4 }}
                            />
                        )}

                        {/* La ligne de prédiction */}
                        <Line 
                            type="monotone" 
                            dataKey="Prédiction" 
                            stroke="#8884d8" 
                            strokeWidth={2} 
                            strokeDasharray="5 5" 
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </Paper>
    );
};

export default PredictionChart;