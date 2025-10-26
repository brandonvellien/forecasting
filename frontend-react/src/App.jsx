// src/App.jsx

import React from 'react';
import { Container, Title, Space, Button, Group, Center, Loader, Text } from '@mantine/core';
import { IconLogout } from '@tabler/icons-react';
import { useAuth } from './hooks/useAuth';
import LoginScreen from './components/LoginScreen';
import VictoryPredictionChart from './components/VictoryPredictionChart';

// --- Le composant qui contient votre tableau de bord ---
const Dashboard = ({ user, onLogout }) => (
    <Container size="xl" my="xl">
        <Group justify="space-between" mb="md">
            <Title order={1} style={{ fontFamily: 'Greycliff CF, sans-serif', color: '#000000' }}>
                Dashboard de Prévision des Ventes
            </Title>
            <Group>
                <Text c="#000000">Bienvenue, <strong>{user.displayName || user.email}</strong></Text>
                
                {/* MODIFICATION RGAA : Bouton déconnexion noir conforme */}
                <Button 
                    onClick={onLogout}
                    aria-label="Se déconnecter"
                    variant="filled"
                    color="dark"
                    leftSection={<IconLogout size={16} />}
                    sx={(theme) => ({
                        backgroundColor: '#000000',
                        color: '#ffffff',
                        fontWeight: 500,
                        '&:hover': {
                            backgroundColor: '#1a1a1a',
                        },
                        '&:focus': {
                            outline: '3px solid #000000',
                            outlineOffset: '2px',
                        },
                        '&:active': {
                            backgroundColor: '#000000',
                        },
                    })}
                >
                    Déconnexion
                </Button>
            </Group>
        </Group>
        
        <Space h="xl" />
        
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

    if (loading) {
        return (
            <Center style={{ height: '100vh' }}>
                <Loader size="lg" />
            </Center>
        );
    }

    if (!user) {
        return <LoginScreen onLogin={loginWithGoogle} error={error} loading={loading} />;
    }
    
    return <Dashboard user={user} onLogout={logout} />;
}

export default App;