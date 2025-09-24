// src/App.jsx

import React from 'react';
import { Container, Title, Space, Button, Group, Center, Loader, Text } from '@mantine/core';
import { useAuth } from './hooks/useAuth';
import LoginScreen from './components/LoginScreen';
import VictoryPredictionChart from './components/VictoryPredictionChart';

// --- Le composant qui contient votre tableau de bord ---
const Dashboard = ({ user, onLogout }) => (
    <Container size="xl" my="xl">
        <Group position="apart" mb="md">
            <Title order={1} style={{ fontFamily: 'Greycliff CF, sans-serif' }}>
                Dashboard de Prévision des Ventes
            </Title>
            <Group>
                <Text>Bienvenue, <strong>{user.displayName || user.email}</strong></Text>
                <Button variant="outline" onClick={onLogout}>Déconnexion</Button>
            </Group>
        </Group>
        
        <Space h="xl" />
        
        {/* Vos graphiques restent inchangés */}
        <VictoryPredictionChart categoryId="ligne1_category1_01" />
        <VictoryPredictionChart categoryId="ligne1_category1_08" />
        <VictoryPredictionChart categoryId="ligne1_category1_CA" />
        <VictoryPredictionChart categoryId="ligne2_category1_08" />
        <VictoryPredictionChart categoryId="ligne2_category1_CA" />
    </Container>
);

// --- Le composant App principal ---
function App() {
    const { user, loading, error, loginWithGoogle, logout } = useAuth();

    // 1. Affiche un Loader Mantine centré pendant la vérification
    if (loading) {
        return (
            <Center style={{ height: '100vh' }}>
                <Loader size="lg" />
            </Center>
        );
    }

    // 2. Si pas d'utilisateur, affiche l'écran de connexion (version Mantine)
    if (!user) {
        return <LoginScreen onLogin={loginWithGoogle} error={error} loading={loading} />;
    }
    
    // 3. Si l'utilisateur est authentifié, affiche le tableau de bord
    return <Dashboard user={user} onLogout={logout} />;
}

export default App;