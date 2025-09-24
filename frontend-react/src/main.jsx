// src/main.jsx

import React from 'react';
import ReactDOM from 'react-dom/client';

// 1. Assurez-vous d'importer les styles CSS de Mantine
import '@mantine/core/styles.css';
import { MantineProvider } from '@mantine/core';

import App from './App.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* 2. Enveloppez TOUTE votre application avec le MantineProvider */}
    <MantineProvider 
      withGlobalStyles 
      withNormalizeCSS
      theme={{
        /** * Vous pouvez personnaliser votre thème ici si vous le souhaitez.
         * Par exemple, pour utiliser la police de votre projet :
         * fontFamily: 'Greycliff CF, sans-serif',
         */
      }}
    >
      <App />
    </MantineProvider>
  </React.StrictMode>
);