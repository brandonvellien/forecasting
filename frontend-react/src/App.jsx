// Fichier: src/App.jsx
import { Container, Title, Space } from '@mantine/core';
import VictoryPredictionChart from './components/VictoryPredictionChart'; // On importe le nouveau composant
import './App.css';

function App() {
  return (
    <Container size="xl" my="xl">
      <Title order={1} align="center" style={{ fontFamily: 'Greycliff CF, sans-serif' }}>
        Dashboard de Prévision des Ventes
      </Title>
      <Space h="xl" />
      
      {/* On utilise le nouveau composant graphique Victory */}
      <VictoryPredictionChart categoryId="ligne1_category1_01" />
      <VictoryPredictionChart categoryId="ligne1_category1_08" />
      <VictoryPredictionChart categoryId="ligne1_category1_CA" />

    </Container>
  );
}

export default App;