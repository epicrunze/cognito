/**
 * Login Page
 * 
 * OAuth login page with Google sign-in.
 */

import React from 'react';
import {
    IonPage,
    IonContent,
    IonButton,
    IonIcon,
    IonSpinner,
} from '@ionic/react';
import { logoGoogle } from 'ionicons/icons';
import { useHistory, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { login } from '../api/auth';

const Login: React.FC = () => {
    const history = useHistory();
    const location = useLocation();
    const { isAuthenticated, isLoading } = useAuth();

    // Parse error from URL
    const searchParams = new URLSearchParams(location.search);
    const error = searchParams.get('error');

    // Redirect if already authenticated
    React.useEffect(() => {
        if (!isLoading && isAuthenticated) {
            history.replace('/');
        }
    }, [isLoading, isAuthenticated, history]);

    const getErrorMessage = (errorCode: string | null): string | null => {
        if (!errorCode) return null;

        switch (errorCode) {
            case 'not_authorized':
                return 'Your email is not authorized to use this app.';
            case 'access_denied':
                return 'Login was cancelled.';
            default:
                return 'An error occurred during login. Please try again.';
        }
    };

    const handleLogin = () => {
        login();
    };

    if (isLoading) {
        return (
            <IonPage>
                <IonContent
                    className="ion-padding"
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                    }}
                >
                    <IonSpinner />
                </IonContent>
            </IonPage>
        );
    }

    return (
        <IonPage>
            <IonContent className="ion-padding">
                <div
                    style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        minHeight: '100%',
                        textAlign: 'center',
                        padding: '24px',
                    }}
                >
                    {/* Logo */}
                    <div
                        style={{
                            fontSize: '72px',
                            marginBottom: '16px',
                        }}
                    >
                        🧠
                    </div>

                    {/* Title */}
                    <h1
                        style={{
                            color: 'var(--ion-color-primary-shade)',
                            fontSize: '32px',
                            fontWeight: 700,
                            marginBottom: '8px',
                        }}
                    >
                        Cognito
                    </h1>

                    {/* Subtitle */}
                    <p
                        style={{
                            color: 'var(--ion-color-medium)',
                            fontSize: '16px',
                            marginBottom: '32px',
                            maxWidth: '280px',
                        }}
                    >
                        Your AI-powered thought journal. Capture, explore, and refine your ideas.
                    </p>

                    {/* Error Message */}
                    {error && (
                        <div
                            style={{
                                backgroundColor: 'var(--ion-color-danger-tint)',
                                color: 'var(--ion-color-danger)',
                                padding: '12px 16px',
                                borderRadius: '8px',
                                marginBottom: '24px',
                                maxWidth: '300px',
                            }}
                        >
                            {getErrorMessage(error)}
                        </div>
                    )}

                    {/* Offline Warning */}
                    {!navigator.onLine && (
                        <div
                            style={{
                                backgroundColor: 'var(--ion-color-warning-tint)',
                                color: 'var(--ion-color-warning-shade)',
                                padding: '12px 16px',
                                borderRadius: '8px',
                                marginBottom: '24px',
                                maxWidth: '300px',
                            }}
                        >
                            You're offline. Connect to the internet to sign in.
                        </div>
                    )}

                    {/* Login Button */}
                    <IonButton
                        onClick={handleLogin}
                        size="large"
                        disabled={!navigator.onLine}
                        style={{
                            '--border-radius': '12px',
                            '--padding-start': '24px',
                            '--padding-end': '24px',
                        }}
                    >
                        <IonIcon icon={logoGoogle} slot="start" />
                        Sign in with Google
                    </IonButton>

                    {/* Footer */}
                    <p
                        style={{
                            color: 'var(--ion-color-medium)',
                            fontSize: '12px',
                            marginTop: '48px',
                        }}
                    >
                        © 2024 Cognito - Your Thought Journal
                    </p>
                </div>
            </IonContent>
        </IonPage>
    );
};

export default Login;
