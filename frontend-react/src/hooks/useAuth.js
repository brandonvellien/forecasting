// src/hooks/useAuth.js
import { useState, useEffect } from 'react';
import { 
    onAuthStateChanged, 
    signOut, 
    GoogleAuthProvider, 
    signInWithPopup 
} from 'firebase/auth';
import { auth } from '../firebase';

const DOMAINE_AUTORISE = '@agnesb.fr';

export const useAuth = () => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true); // Pour savoir si on vérifie l'état initial
    const [error, setError] = useState('');

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
            setUser(currentUser);
            setLoading(false);
        });
        // Nettoyage de l'écouteur lors du démontage du composant
        return () => unsubscribe();
    }, []);

    const loginWithGoogle = async () => {
        const provider = new GoogleAuthProvider();
        setError('');
        setLoading(true);
        try {
            const result = await signInWithPopup(auth, provider);
            const userEmail = result.user.email;

            if (userEmail && userEmail.endsWith(DOMAINE_AUTORISE)) {
                // Succès, on laisse onAuthStateChanged faire son travail
            } else {
                // Erreur de domaine, on déconnecte l'utilisateur
                await signOut(auth);
                setError(`Accès refusé. Le domaine ${DOMAINE_AUTORISE} est requis.`);
            }
        } catch (error) {
            console.error("Erreur de connexion Google :", error);
            setError("Une erreur est survenue lors de la tentative de connexion.");
        } finally {
            setLoading(false);
        }
    };

    const logout = async () => {
        await signOut(auth);
    };

    return { user, loading, error, loginWithGoogle, logout };
};