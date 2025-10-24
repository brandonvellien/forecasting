import React, { useState, useEffect } from 'react';
import { Card, Stack, Text, Loader, Center, Alert, Accordion, Table, Group, Switch } from '@mantine/core';
import { VictoryChart, VictoryLine, VictoryAxis, VictoryTooltip, VictoryVoronoiContainer, VictoryArea, VictoryLabel } from 'victory';
import usePredictions from '../hooks/usePredictions';
import { getHistoricalData } from '../api/predictionService';

const SectionTitle = ({ children }) => (
    <Text size="lg" weight={700} style={{ fontFamily: 'Greycliff CF, sans-serif' }}>
        {children}
    </Text>
);

const CHART_COLORS = {
    axis: "#000000",
    predictionLine: "#082644",
    confidenceArea: "#757575",
    grid: "#e0e0e050",
    historicalLine: "#381A1A",
};

const formatDate = (dateString) => new Date(dateString).toISOString().split('T')[0];

const VictoryPredictionChart = ({ categoryId }) => {
    const { data, loading, error } = usePredictions(categoryId);

    const [historicalData, setHistoricalData] = useState([]);
    const [showHistorical, setShowHistorical] = useState(false);

    useEffect(() => {
        if (data && data.dates && data.dates.length > 0) {
            const fetchHistorical = async () => {
                const startDate = formatDate(data.dates[0]);
                const endDate = formatDate(data.dates[data.dates.length - 1]);
                const result = await getHistoricalData(categoryId, startDate, endDate);
                setHistoricalData(result);
            };
            fetchHistorical();
        }
    }, [data, categoryId]);

    if (loading) {
        return (
            <Card withBorder radius="md" p="xl" mb="xl" shadow="sm">
                <Center style={{ height: 350 }}>
                    <Loader color="blue" aria-label="Chargement du graphique de prédictions" />
                </Center>
            </Card>
        );
    }

    if (error) {
        return (
            <Card withBorder radius="md" p="xl" mb="xl" shadow="sm">
                <Alert title="Erreur de chargement" color="red" variant="light" role="alert">
                    Impossible de charger les prédictions pour cette catégorie. Veuillez réessayer plus tard.
                </Alert>
            </Card>
        );
    }

    if (!data || !data.dates || data.dates.length === 0) {
        return (
            <Card withBorder radius="md" p="xl" mb="xl" shadow="sm">
                <Alert title="Données indisponibles" color="yellow" variant="light" role="alert">
                    Aucune donnée de prédiction n'a pu être trouvée pour {categoryId.replace(/_/g, ' ')}.
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
    const chartHistorical = historicalData.map(item => ({ x: new Date(item.timestamp), y: item.qty_sold }));

    const categoryName = categoryId.replace(/_/g, ' ').replace('category', 'Catégorie ');
    const chartDescription = `Graphique de prédiction de ventes pour ${categoryName}. La ligne bleue foncée représente la prédiction moyenne de ventes. La zone grise encadrant la ligne représente l'intervalle de confiance (valeurs minimales et maximales prédites). ${showHistorical ? 'La ligne verte pointillée affiche les ventes de l\'année précédente (N-1) pour comparaison. ' : ''}L'axe horizontal affiche les dates, l'axe vertical affiche la quantité vendue.`;

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
            <Group position="apart" align="center" style={{ marginBottom: '1rem' }}>
                <Text component="h2" size="xl" weight={900}>
                    {categoryName}
                </Text>
                <Switch
                    label="Comparer avec N-1"
                    checked={showHistorical}
                    onChange={(event) => setShowHistorical(event.currentTarget.checked)}
                    color="green"
                    aria-label="Afficher les données de ventes de l'année précédente"
                    aria-pressed={showHistorical}
                />
            </Group>

            {/* Description du graphique */}
            <div id="chart-description" style={{ marginTop: '1rem', padding: '0.75rem', backgroundColor: '#f5f5f5', borderLeft: `4px solid ${CHART_COLORS.predictionLine}`, borderRadius: '4px' }} role="doc-subtitle" aria-live="polite">
                <Text size="sm" style={{ color: '#333', lineHeight: 1.6 }}>
                    {chartDescription}
                </Text>
            </div>

            <div style={{ userSelect: 'none', position: 'relative' }}>
                <VictoryChart
                    width={900}
                    height={400}
                    scale={{ x: "time" }}
                    padding={{ top: 50, bottom: 60, left: 60, right: 30 }}
                    role="img"
                    aria-label={`Graphique de prédiction de ventes - ${categoryName}`}
                    aria-describedby="chart-description"
                    containerComponent={
                        <VictoryVoronoiContainer
                            labels={({ datum, index }) => {
                                const dateStr = datum.x.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' });
                                
                                // Chercher l'index pour récupérer les valeurs basse et haute
                                const lower = data.predicted_sales_lower[index] !== undefined ? Math.round(data.predicted_sales_lower[index]) : null;
                                const mean = data.predicted_sales_mean[index] !== undefined ? Math.round(data.predicted_sales_mean[index]) : null;
                                const upper = data.predicted_sales_upper[index] !== undefined ? Math.round(data.predicted_sales_upper[index]) : null;
                                
                                if (lower !== null && mean !== null && upper !== null) {
                                    return `Date: ${dateStr}\nPrédiction basse: ${lower} unités\nPrédiction moyenne: ${mean} unités\nPrédiction haute: ${upper} unités`;
                                }
                                return `Date: ${dateStr}\nVentes: ${Math.round(datum.y)} unités`;
                            }}
                            labelComponent={
                                <VictoryTooltip
                                    cornerRadius={5}
                                    flyoutStyle={{ fill: "white", stroke: CHART_COLORS.grid }}
                                    style={{ fontSize: 12, fill: "#000" }}
                                />
                            }
                        />
                    }
                >

                    <VictoryLabel 
                        text="Quantités vendue"
                        x={60}
                        y={25}
                        textAnchor="middle"
                        style={{ fill: CHART_COLORS.axis, fontWeight: 'bold', fontFamily: "'Greycliff CF', sans-serif", fontSize: 13 }}
                    />
                    
                    <VictoryAxis
                        label='Date'
                        tickFormat={(x) => new Date(x).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}
                        tickCount={6}
                        style={{
                            axis: { stroke: CHART_COLORS.axis, strokeWidth: 2 },
                            axisLabel: { padding: 30, fill: CHART_COLORS.axis, textAnchor: 'end', fontWeight: 'bold', fontFamily: "'Greycliff CF', sans-serif", fontSize: 13 },
                            tickLabels: { angle: 0, textAnchor: 'middle', fill: CHART_COLORS.axis, fontSize: 12 }
                        }}
                    />
                    
                    <VictoryAxis
                        dependentAxis
                        tickFormat={(y) => `${Math.round(y)}`}
                        style={{
                            axis: { stroke: CHART_COLORS.axis, strokeWidth: 2 },
                            tickLabels: { fill: CHART_COLORS.axis, fontSize: 12 },
                            grid: { stroke: CHART_COLORS.grid, strokeWidth: 0.5 }
                        }}
                    />
                    
                    <VictoryArea
                        data={chartDataConfidence}
                        style={{ data: { fill: CHART_COLORS.confidenceArea, fillOpacity: 0.3 } }}
                    />
                    
                    <VictoryLine
                        data={chartDataMean}
                        style={{ data: { stroke: CHART_COLORS.predictionLine, strokeWidth: 2.5 } }}
                        animate={{ duration: 1500, onLoad: { duration: 1000 } }}
                    />

                    {showHistorical && (
                        <VictoryLine
                            data={chartHistorical}
                            style={{ data: { stroke: CHART_COLORS.historicalLine, strokeWidth: 2.5, strokeDasharray: "5, 5" } }}
                        />
                    )}
                </VictoryChart>
            </div>

            {/* Légende avec ARIA */}
            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'center', gap: '2rem', flexWrap: 'wrap' }} role="region" aria-label="Légende du graphique">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div 
                        style={{ width: '24px', height: '3px', backgroundColor: CHART_COLORS.predictionLine }} 
                        aria-hidden="true"
                    ></div>
                    <Text size="sm" component="span">Prédiction moyenne</Text>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div 
                        style={{ 
                            width: '24px', 
                            height: '3px', 
                            backgroundColor: CHART_COLORS.historicalLine, 
                            backgroundImage: 'repeating-linear-gradient(90deg, ' + CHART_COLORS.historicalLine + ' 0px, ' + CHART_COLORS.historicalLine + ' 5px, transparent 5px, transparent 10px)' 
                        }}
                        aria-hidden="true"
                    ></div>
                    <Text size="sm" component="span">Ventes N-1</Text>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <div 
                        style={{ width: '24px', height: '15px', backgroundColor: CHART_COLORS.confidenceArea, opacity: 0.3, border: `1px solid ${CHART_COLORS.confidenceArea}` }}
                        aria-hidden="true"
                    ></div>
                    <Text size="sm" component="span">Intervalle de confiance</Text>
                </div>
            </div>

            {/* Tableau de données détaillées */}
            <Accordion variant="separated" radius="md" mt="xl">
                <Accordion.Item value="prediction-data-table">
                    <Accordion.Control>Afficher les données détaillées</Accordion.Control>
                    <Accordion.Panel>
                        <Table 
                            captionSide="top" 
                            highlightOnHover 
                            withBorder 
                            withColumnBorders
                            role="table"
                            aria-label="Tableau détaillé des prédictions de ventes"
                        >
                            <caption id="table-caption" style={{ fontWeight: 'bold', marginBottom: '1rem', color: '#000', textAlign: 'left' }}>
                                Prédictions détaillées par semaine pour {categoryName}
                            </caption>
                            <thead>
                                <tr>
                                    <th style={{ textAlign: 'start', paddingBottom: 10 }} scope="col">Date de la Semaine</th>
                                    <th style={{ textAlign: 'start', paddingBottom: 10 }} scope="col">Prédiction Basse</th>
                                    <th style={{ textAlign: 'start', paddingBottom: 10 }} scope="col">Prédiction Moyenne</th>
                                    <th style={{ textAlign: 'start', paddingBottom: 10 }} scope="col">Prédiction Haute</th>
                                </tr>
                            </thead>
                            <tbody style={{ textAlign: 'start' }}>
                                {tableRows}
                            </tbody>
                        </Table>
                    </Accordion.Panel>
                </Accordion.Item>
            </Accordion>
        </Card>
    );
};

export default VictoryPredictionChart;