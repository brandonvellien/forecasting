import React from 'react';
// 1. Importer Accordion et Table depuis Mantine
import { Card, Stack, Text, Loader, Center, Alert, Accordion, Table } from '@mantine/core';
import { VictoryChart, VictoryLine, VictoryAxis, VictoryTooltip, VictoryVoronoiContainer, VictoryArea, VictoryLabel } from 'victory';
import usePredictions from '../hooks/usePredictions';

const SectionTitle = ({ children }) => (
    <Text size="lg" weight={700} style={{ fontFamily: 'Greycliff CF, sans-serif' }}>
        {children}
    </Text>
);

const CHART_COLORS = {
    axis: "#000000",
    predictionLine: "#082644",
    confidenceArea: "#757575",
    grid: "#e0e0e050"
};

const VictoryPredictionChart = ({ categoryId }) => {
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

    if (!data || !data.dates || data.dates.length === 0) {
        return (
            <Card withBorder radius="md" p="xl" mb="xl" shadow="sm">
                <Alert title="Données indisponibles" color="yellow" variant="light">
                    Aucune donnée de prédiction n'a pu être trouvée pour {categoryId}.
                </Alert>
            </Card>
        );
    }
    
    const chartDataMean = data.dates.map((date, i) => ({ x: new Date(date), y: data.predicted_sales_mean[i] }));
    const chartDataConfidence = data.dates.map((date, i) => ({
        x: new Date(date),
        y: data.predicted_sales_upper[i],
        y0: data.predicted_sales_lower[i]
    }));

    const chartDescription = ` Prédiction de ventes pour ${categoryId.replace(/_/g, ' ').replace('category', 'Catégorie ')}. 
La ligne bleue foncée représente la prédiction moyenne de ventes. 
La zone grise encadrant la ligne représente l'intervalle de confiance (valeurs minimales et maximales prédites). 
L'axe horizontal affiche les dates, l'axe vertical affiche la quantité vendue.`;

    // 2. Préparer les données pour les lignes du tableau
    const tableRows = data.dates.map((date, index) => (
        <tr key={date}>
            <td>{new Date(date).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' })}</td>
            <td>~{Math.round(data.predicted_sales_lower[index])} unités</td>
            <td><strong>~{Math.round(data.predicted_sales_mean[index])} unités</strong></td>
            <td>~{Math.round(data.predicted_sales_upper[index])} unités</td>
        </tr>
    ));

    return (
        <Card withBorder radius="md" p="xl" mb="xl" shadow="sm">
            <Stack align="center" style={{ marginBottom: '1rem' }}>
                <Text size="xl" weight={900} align="center">
                    {categoryId.replace(/_/g, ' ').replace('category', 'Catégorie ')}
                </Text>
            </Stack>

            <div style={{ userSelect: 'none' }}>
                <VictoryChart
                    width={900}
                    height={400}
                    scale={{ x: "time" }}
                    padding={{ top: 50, bottom: 60, left: 60, right: 30 }}
                    role="img"
                    aria-label={`Graphique de prédiction - ${categoryId.replace(/_/g, ' ')}`}
                    aria-describedby="chart-description" // Note : L'ID est maintenant plus bas
                    containerComponent={
                        <VictoryVoronoiContainer
                            labels={({ datum }) => `Date: ${datum.x.toLocaleDateString('fr-FR')}\nPrédiction: ${Math.round(datum.y)}`}
                            labelComponent={<VictoryTooltip cornerRadius={5} flyoutStyle={{ fill: "white", stroke: CHART_COLORS.grid }} />}
                        />
                    }
                >
                    {/* --- TITRES, AXES, LIGNES, ETC. --- */}
                    <VictoryLabel 
                        text="Quantité vendue"
                        x={60}
                        y={25}
                        textAnchor="middle"
                        style={{ fill: CHART_COLORS.axis, fontWeight: 'bold', fontFamily: "'Greycliff CF', sans-serif" }}
                    />
                    <VictoryAxis
                        label='Date'
                        tickFormat={(x) => new Date(x).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}
                        tickCount={6}
                        style={{
                            axis: { stroke: CHART_COLORS.axis },
                            axisLabel: { padding: 30, fill: CHART_COLORS.axis, textAnchor: 'end', fontWeight: 'bold', fontFamily: "'Greycliff CF', sans-serif" },
                            tickLabels: { angle: 0, textAnchor: 'middle', fill: CHART_COLORS.axis }
                        }}
                    />
                    <VictoryAxis
                        dependentAxis
                        tickFormat={(y) => `${Math.round(y)}`}
                        style={{
                            axis: { stroke: CHART_COLORS.axis },
                            tickLabels: { fill: CHART_COLORS.axis },
                            grid: { stroke: CHART_COLORS.grid }
                        }}
                    />
                    <VictoryArea
                        data={chartDataConfidence}
                        style={{ data: { fill: CHART_COLORS.confidenceArea, fillOpacity: 0.3 } }}
                    />
                    <VictoryLine
                        data={chartDataMean}
                        style={{ data: { stroke: CHART_COLORS.predictionLine, strokeWidth: 2 } }}
                        animate={{ duration: 1500, onLoad: { duration: 1000 } }}
                    />
                </VictoryChart>
            </div>

            {/* --- LÉGENDE VISUELLE --- */}
            <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'center', gap: '2rem' }} role="region" aria-label="Légende du graphique">
                {/* ... (votre code de légende existant) ... */}
            </div>

            {/* 3. AJOUT DE L'ACCORDÉON ET DU TABLEAU */}
            <Accordion variant="separated" radius="md" mt="xl">
                <Accordion.Item value="prediction-data-table">
                    <Accordion.Control>Afficher les données détaillées</Accordion.Control>
                    <Accordion.Panel>
                        <Table captionSide="top" highlightOnHover withBorder withColumnBorders>
                            <caption id="chart-description" style={{ fontWeight: 'bold', marginBottom: '1rem', color: '#000' }}>
                                {chartDescription.split('\n')[0]} 
                            </caption>
                            <thead>
                                <tr>
                                    <th style={{ textAlign: 'start', paddingBottom:10 } }>Date de la Semaine</th>
                                    <th style={{ textAlign: 'start', paddingBottom:10 }}>Prédiction Basse</th>
                                    <th style={{ textAlign: 'start', paddingBottom:10 }}>Prédiction Moyenne</th>
                                    <th style={{ textAlign: 'start', paddingBottom:10 }}>Prédiction Haute</th>
                                </tr>
                            </thead>
                            <tbody style={{ textAlign: 'start' }}>{tableRows}</tbody>
                        </Table>
                    </Accordion.Panel>
                </Accordion.Item>
            </Accordion>
        </Card>
    );
};

export default VictoryPredictionChart;