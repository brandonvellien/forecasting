import React from 'react';
import { Card, Text, Group, Loader, Center, Alert, useMantineTheme } from '@mantine/core';
import { VictoryChart, VictoryLine, VictoryTheme, VictoryAxis, VictoryTooltip, VictoryVoronoiContainer, VictoryArea } from 'victory';
import usePredictions from '../hooks/usePredictions';

// Un composant pour un titre de section stylé
const SectionTitle = ({ children }) => (
    <Text size="lg" weight={700} style={{ fontFamily: 'Greycliff CF, sans-serif' }}>
        {children}
    </Text>
);

const VictoryPredictionChart = ({ categoryId }) => {
    const theme = useMantineTheme();
    const { data, loading, error } = usePredictions(categoryId);

    if (loading) {
        return (
            <Card withBorder radius="md" p="xl" mb="xl" shadow="sm">
                <Center style={{ height: 350 }}><Loader color="blue" /></Center>
            </Card>
        );
    }

    if (error) {
        return (
            <Card withBorder radius="md" p="xl" mb="xl" shadow="sm">
                <Alert title="Erreur de chargement" color="red" variant="light">
                    Impossible de charger les prédictions pour cette catégorie. Veuillez réessayer plus tard.
                </Alert>
            </Card>
        );
    }

    // Garde de sécurité robuste pour les nouvelles données
    if (!data || !data.dates || data.dates.length === 0) {
        return (
            <Card withBorder radius="md" p="xl" mb="xl" shadow="sm">
                <Alert title="Données indisponibles" color="yellow" variant="light">
                    Aucune donnée de prédiction n'a pu être trouvée pour {categoryId}.
                </Alert>
            </Card>
        );
    }

    // Préparation des données pour le graphique à partir du nouveau format
    const chartDataMean = data.dates.map((date, i) => ({ x: new Date(date), y: data.predicted_sales_mean[i] }));
    const chartDataConfidence = data.dates.map((date, i) => ({
        x: new Date(date),
        y: data.predicted_sales_upper[i],
        y0: data.predicted_sales_lower[i]
    }));

    return (
        <Card withBorder radius="md" p="xl" mb="xl" shadow="sm">
            <Group position="apart">
                <SectionTitle>{categoryId.replace(/_/g, ' ').replace('category', 'Catégorie ')}</SectionTitle>
            </Group>

            <div style={{ userSelect: 'none' }}>
                {/* Définition du dégradé pour l'intervalle de confiance */}
                <svg style={{ height: 0 }}>
                    <defs>
                        <linearGradient id="confidenceGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stopColor={theme.colors.blue[2]} stopOpacity={0.4} />
                            <stop offset="100%" stopColor={theme.colors.blue[0]} stopOpacity={0.1} />
                        </linearGradient>
                    </defs>
                </svg>

                <VictoryChart
                    theme={VictoryTheme.material}
                    width={900}
                    height={400}
                    scale={{ x: "time" }}
                    padding={{ top: 20, bottom: 60, left: 60, right: 30 }}
                    containerComponent={
                        <VictoryVoronoiContainer
                            labels={({ datum }) => `Date: ${datum.x.toLocaleDateString('fr-FR')}\nPrédiction: ${Math.round(datum.y)}`}
                            labelComponent={<VictoryTooltip cornerRadius={5} flyoutStyle={{ fill: "white", stroke: theme.colors.gray[3] }} />}
                        />
                    }
                >
                    <VictoryAxis
                        tickFormat={(x) => new Date(x).toLocaleDateString('fr-FR', { month: 'short', year: '2-digit' })}
                        style={{
                            axis: { stroke: theme.colors.gray[3] },
                            tickLabels: { angle: -40, fontSize: 10, padding: 15, fill: theme.colors.gray[6] },
                            grid: { stroke: theme.colors.gray[2], strokeDasharray: '4, 8' }
                        }}
                    />
                    <VictoryAxis
                        dependentAxis
                        tickFormat={(y) => `${Math.round(y)}`}
                        style={{
                            axis: { stroke: 'transparent' },
                            tickLabels: { fontSize: 10, fill: theme.colors.gray[6] },
                            grid: { stroke: theme.colors.gray[2], strokeDasharray: '4, 8' }
                        }}
                    />

                    {/* Zone de l'intervalle de confiance */}
                    <VictoryArea
                        data={chartDataConfidence}
                        style={{ data: { fill: "url(#confidenceGradient)", stroke: "none" } }}
                    />

                    {/* Ligne de la prédiction moyenne */}
                    <VictoryLine
                        data={chartDataMean}
                        style={{ data: { stroke: theme.colors.blue[6], strokeWidth: 2 } }}
                        animate={{ duration: 1500, onLoad: { duration: 1000 } }}
                    />
                </VictoryChart>
            </div>
        </Card>
    );
};

export default VictoryPredictionChart;