// src/components/LoginScreen.jsx
import React from 'react';

const LoginScreen = ({ onLogin, error, loading }) => {
    return (
        <div style={{ textAlign: 'center', marginTop: '100px' }}>
            <h2>Accès à l'application Forecasting</h2>
            <p>Veuillez vous connecter en utilisant votre compte professionnel.</p>
            <button onClick={onLogin} disabled={loading}>
                {loading ? 'Connexion en cours...' : 'Se connecter avec Google'}
            </button>
            {error && <p style={{ color: 'red', marginTop: '20px' }}>{error}</p>}
        </div>
    );
};

export default LoginScreen;