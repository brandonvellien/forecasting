// Fichier: src/components/PredictionCard.jsx
import { Card, Title, Table, Loader, Alert, Text } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { usePredictions } from '../hooks/usePredictions';

const PredictionCard = ({ categoryId }) => {
    const { data, isLoading, error } = usePredictions(categoryId);

    if (isLoading) {
        return <Card withBorder p="xl" radius="md"><Loader /></Card>;
    }

    if (error) {
        return (
            <Alert icon={<IconAlertCircle size="1rem" />} title="Erreur !" color="red">
                {error}
            </Alert>
        );
    }

    return (
        <Card withBorder p="xl" radius="md" mt="md">
            <Title order={3}>Prédictions pour : <Text span c="blue" inherit>{categoryId}</Text></Title>
            <Table mt="md" striped highlightOnHover withBorder>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Prédiction</th>
                        <th>Borne Basse (10%)</th>
                        <th>Borne Haute (90%)</th>
                    </tr>
                </thead>
                <tbody>
                    {data.map((item) => (
                        <tr key={item.timestamp}>
                            <td>{new Date(item.timestamp).toLocaleDateString()}</td>
                            <td>{item['0.5'].toFixed(2)}</td>
                            <td>{item['0.1'].toFixed(2)}</td>
                            <td>{item['0.9'].toFixed(2)}</td>
                        </tr>
                    ))}
                </tbody>
            </Table>
        </Card>
    );
};

export default PredictionCard;