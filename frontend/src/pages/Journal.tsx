/**
 * Journal Page
 * 
 * Main page showing list of journal entries with pull-to-refresh.
 */

import React, { useState, useCallback } from 'react';
import {
    IonPage,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonList,
    IonRefresher,
    IonRefresherContent,
    IonFab,
    IonFabButton,
    IonIcon,
    IonButtons,
    IonSpinner,
    RefresherEventDetail,
} from '@ionic/react';
import { add } from 'ionicons/icons';
import { useHistory } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useEntries } from '../hooks/useEntries';
import { useSync } from '../hooks/useSync';
import EntryCard from '../components/EntryCard';
import ChatModal from '../components/ChatModal';
import SyncIndicator from '../components/SyncIndicator';
import type { Entry } from '../db';
import { updateEntry } from '../db/entries';

const Journal: React.FC = () => {
    const history = useHistory();
    const { user, isAuthenticated, isLoading: authLoading } = useAuth();
    const { activeEntries, isLoading: entriesLoading, refresh } = useEntries();
    const { triggerSync } = useSync();

    const [chatEntry, setChatEntry] = useState<Entry | null>(null);
    const [isChatOpen, setIsChatOpen] = useState(false);

    // Redirect to login if not authenticated
    React.useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            history.replace('/login');
        }
    }, [authLoading, isAuthenticated, history]);

    const handleRefresh = useCallback(
        async (event: CustomEvent<RefresherEventDetail>) => {
            try {
                triggerSync();
                await refresh();
            } finally {
                event.detail.complete();
            }
        },
        [refresh, triggerSync]
    );

    const handleEntryClick = (entry: Entry) => {
        history.push(`/entry/${entry.id}`);
    };

    const handleChat = (entry: Entry) => {
        setChatEntry(entry);
        setIsChatOpen(true);
    };

    const handleArchive = async (entry: Entry) => {
        await updateEntry(entry.id, { status: 'archived' });
        await refresh();
    };

    const handleCloseChat = () => {
        setIsChatOpen(false);
        setChatEntry(null);
        refresh();
    };

    const handleNewEntry = () => {
        history.push('/entry/new');
    };

    if (authLoading) {
        return (
            <IonPage>
                <IonContent className="ion-padding" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <IonSpinner />
                </IonContent>
            </IonPage>
        );
    }

    return (
        <IonPage>
            <IonHeader>
                <IonToolbar>
                    <IonTitle>🧠 Cognito</IonTitle>
                    <IonButtons slot="end">
                        <SyncIndicator />
                        {user && (
                            <img
                                src={user.picture}
                                alt={user.name}
                                style={{
                                    width: '32px',
                                    height: '32px',
                                    borderRadius: '50%',
                                    marginLeft: '8px',
                                    marginRight: '8px',
                                }}
                            />
                        )}
                    </IonButtons>
                </IonToolbar>
            </IonHeader>

            <IonContent fullscreen>
                <IonRefresher slot="fixed" onIonRefresh={handleRefresh}>
                    <IonRefresherContent pullingText="Pull to refresh" refreshingSpinner="circles" />
                </IonRefresher>

                <div className="ion-padding">
                    <h1 style={{ color: 'var(--ion-color-primary-shade)', marginBottom: '4px' }}>
                        Your Journal
                    </h1>
                    <p style={{ color: 'var(--ion-color-medium)', marginTop: 0 }}>
                        Capture your thoughts and insights
                    </p>
                </div>

                {entriesLoading ? (
                    <div style={{ textAlign: 'center', padding: '48px' }}>
                        <IonSpinner />
                    </div>
                ) : activeEntries.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '48px 16px' }}>
                        <div
                            style={{
                                width: '80px',
                                height: '80px',
                                margin: '0 auto 16px',
                                opacity: 0.5,
                                fontSize: '64px',
                            }}
                        >
                            📔
                        </div>
                        <h2 style={{ color: 'var(--ion-text-color)' }}>No entries yet</h2>
                        <p style={{ color: 'var(--ion-color-medium)', maxWidth: '300px', margin: '8px auto' }}>
                            Start your journaling journey by creating your first entry. Share your thoughts, ideas, and reflections.
                        </p>
                    </div>
                ) : (
                    <IonList>
                        {activeEntries.map((entry) => (
                            <EntryCard
                                key={entry.id}
                                entry={entry}
                                onClick={() => handleEntryClick(entry)}
                                onChat={() => handleChat(entry)}
                                onArchive={() => handleArchive(entry)}
                            />
                        ))}
                    </IonList>
                )}

                <IonFab vertical="bottom" horizontal="end" slot="fixed">
                    <IonFabButton onClick={handleNewEntry}>
                        <IonIcon icon={add} />
                    </IonFabButton>
                </IonFab>

                {chatEntry && (
                    <ChatModal
                        isOpen={isChatOpen}
                        onClose={handleCloseChat}
                        entryId={chatEntry.id}
                        existingConversation={
                            chatEntry.conversations.length > 0
                                ? chatEntry.conversations[chatEntry.conversations.length - 1]
                                : null
                        }
                    />
                )}
            </IonContent>
        </IonPage>
    );
};

export default Journal;
