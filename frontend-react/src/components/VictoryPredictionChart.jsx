// Fichier: src/components/VictoryPredictionChart.jsx

import React from 'react';
import { Paper, Title, Loader, Alert, Text, Grid } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { usePredictions } from '../hooks/usePredictions';
import { VictoryChart, VictoryAxis, VictoryArea, VictoryLine, VictoryBar, VictoryVoronoiContainer, VictoryTooltip, VictoryTheme } from 'victory';

const VictoryPredictionChart = ({ categoryId }) => {
    const { data, isLoading, error } = usePredictions(categoryId);

    if (isLoading) {
        return <Paper withBorder shadow="md" p="xl" radius="md" mt="xl"><Loader color="blue" /></Paper>;
    }
    if (error) {
        return <Alert icon={<IconAlertCircle size="1rem" />} title="Erreur !" color="red" mt="md">{error}</Alert>;
    }
    
    // On transforme et enrichit les données
    const chartData = data.map(item => ({
        x: new Date(item.timestamp),
        y_pred: Number(item['0.5']) || 0,
        y_low: Number(item['0.1']) || 0,
        y_high: Number(item['0.9']) || 0,
        // On calcule la largeur de l'intervalle pour le 2ème graphique
        uncertainty: (Number(item['0.9']) || 0) - (Number(item['0.1']) || 0),
    }));
    
    const colors = { prediction: "#1976D2", interval: "#90CAF9" };

    return (
        <Paper withBorder shadow="md" p="xl" radius="md" mt="xl">
            <Title order={3} align="center" mb="md">
                Analyse des Prédictions pour : <Text span c="blue" inherit>{categoryId}</Text>
            </Title>
            
            <Grid>
                {/* --- GRAPHIQUE 1 : PRÉVISIONS --- */}
                <Grid.Col span={8}>
                    <Title order={5} c="dimmed">Prévisions vs Intervalle de Confiance</Title>
                    <VictoryChart width={600} height={350} theme={VictoryTheme.material}
                        containerComponent={
                            <VictoryVoronoiContainer voronoiDimension="x"
                                labels={({ datum }) => `Date: ${datum.x.toLocaleDateString('fr-FR')}\nPrédit: ${datum.y_pred.toFixed(2)}`}
                                labelComponent={<VictoryTooltip cornerRadius={3} flyoutStyle={{ fill: "white" }}/>}
                            />
                        }
                    >
                        <VictoryAxis tickFormat={(t) => new Date(t).toLocaleDateString('fr-FR', { month: 'short' })} />
                        <VictoryAxis dependentAxis />

                        {/* --- AMÉLIORATION 1 : DOUBLE DÉGRADÉ --- */}
                        <VictoryArea data={chartData} x="x" y0="y_low" y="y_pred"
                            style={{ data: { fill: colors.interval, fillOpacity: 0.2, stroke: "none" } }}
                        />
                        <VictoryArea data={chartData} x="x" y0="y_pred" y="y_high"
                            style={{ data: { fill: colors.interval, fillOpacity: 0.4, stroke: "none" } }}
                        />
                        
                        <VictoryLine data={chartData} x="x" y="y_pred"
                            style={{ data: { stroke: colors.prediction, strokeWidth: 2.5 } }}
                        />
                    </VictoryChart>
                </Grid.Col>

                {/* --- GRAPHIQUE 2 : INCERTITUDE --- */}
                <Grid.Col span={4}>
                     <Title order={5} c="dimmed">Évolution de l'Incertitude</Title>
                     <VictoryChart width={300} height={350} theme={VictoryTheme.material}
                        padding={{ top: 50, bottom: 50, left: 50, right: 30 }}
                        containerComponent={
                            <VictoryVoronoiContainer voronoiDimension="x"
                                labels={({ datum }) => `Incertitude: ${datum.uncertainty.toFixed(2)}`}
                                labelComponent={<VictoryTooltip cornerRadius={3} flyoutStyle={{ fill: "white" }}/>}
                            />
                        }
                     >
                        <VictoryAxis tickFormat={() => ''} />
                        <VictoryAxis dependentAxis />
                        <VictoryBar
                            data={chartData}
                            x="x"
                            y="uncertainty"
                            style={{ data: { fill: colors.interval } }}
                        />
                     </VictoryChart>
                </Grid.Col>
            </Grid>
        </Paper>
    );
};

export default VictoryPredictionChart;