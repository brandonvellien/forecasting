import React, { useState } from 'react';
import {
  Container,
  Paper,
  Button,
  Alert,
  Group,
  Stack,
  Image,
  Text,
  Center,
  Loader,
} from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import companyLogo from '../assets/logo.svg';

const GoogleIcon = () => (
  <svg
    version="1.1"
    xmlns="http://www.w3.org/2000/svg"
    width="20px"
    height="20px"
    viewBox="0 0 48 48"
    style={{ marginRight: '8px' }}
  >
    <path
      fill="#EA4335"
      d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
    ></path>
    <path
      fill="#4285F4"
      d="M46.98 24.55c0-1.57-.15-3.09-.42-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
    ></path>
    <path
      fill="#FBBC05"
      d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
    ></path>
    <path
      fill="#34A853"
      d="M24 48c6.48 0 11.93-2.13 15.89-5.82l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
    ></path>
    <path fill="none" d="M0 0h48v48H0z"></path>
  </svg>
);

const LoginScreen = ({ onLogin, error, loading }) => {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', backgroundColor: '#f8f9fa' }}>
      <Container size="xs" style={{ width: '100%' }}>
        <Center>
          <Paper
            radius="md"
            p="xl"
            withBorder
            shadow="sm"
            style={{ width: '100%', maxWidth: '420px' }}
          >
            <Stack gap="lg" align="center">
              {/* Header avec logo et titre */}
              <Group justify="center" gap="sm">
                <Image 
                  src={companyLogo} 
                  alt="Logo de votre entreprise"
                  h={48}
                  w="auto"
                />
                <Text fw={600} size="lg" c="#050505">
                  forecasting
                </Text>
              </Group>

              {/* Subtitle */}
              <Text size="s" c="#000000" ta="center">
                Veuillez vous connecter avec votre compte professionnel.
              </Text>

              {/* Error Alert */}
              {error && (
                <Alert
                  icon={<IconAlertCircle size={16} />}
                  title="Erreur de connexion"
                  color="red"
                  style={{ width: '100%' }}
                >
                  {error}
                </Alert>
              )}

              {/* Login Button */}
              <Button
                onClick={onLogin}
                disabled={loading}
                loading={loading}
                fullWidth
                size="md"
                leftSection={
                  !loading && <GoogleIcon />
                }
                variant="filled"
                color="dark"
                radius="md"
              >
                {loading ? 'Connexion en cours...' : 'Se connecter avec Google'}
              </Button>

              {/* Footer text */}
              <Text size="sm" c="#000000" ta="center">
                Nous utilisons Google pour sécuriser votre accès.
              </Text>
            </Stack>
          </Paper>
        </Center>
      </Container>
    </div>
  );
};

export default LoginScreen;