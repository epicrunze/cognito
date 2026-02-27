/**
 * Entry Detail Page
 * 
 * Shows a single journal entry with chat functionality.
 */

import React, { useState, useEffect } from 'react';
import {
    IonPage,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonButtons,
    IonBackButton,
    IonButton,
    IonIcon,
    IonSpinner,
    IonCard,
    IonCardHeader,
    IonCardTitle,
    IonCardContent,
} from '@ionic/react';
import { chatbubbleOutline, archiveOutline, refreshOutline } from 'ionicons/icons';
import { useParams, useHistory } from 'react-router-dom';
import { getEntry, updateEntry } from '../db/entries';
import type { Entry } from '../db';
import ChatModal from '../components/ChatModal';

const EntryDetail: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const history = useHistory();
    const [entry, setEntry] = useState<Entry | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isChatOpen, setIsChatOpen] = useState(false);

    useEffect(() => {
        loadEntry();
    }, [id]);

    const loadEntry = async () => {
        setIsLoading(true);
        try {
            const loadedEntry = await getEntry(id);
            setEntry(loadedEntry || null);
        } catch (err) {
            console.error('Failed to load entry:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleArchive = async () => {
        if (!entry) return;
        await updateEntry(entry.id, { status: 'archived' });
        history.goBack();
    };

    const handleOpenChat = () => {
        setIsChatOpen(true);
    };

    const handleCloseChat = () => {
        setIsChatOpen(false);
        loadEntry(); // Refresh entry to get updated conversations
    };

    const formatDate = (dateStr: string): string => {
        const [year, month, day] = dateStr.split('-').map(Number);
        const date = new Date(year, month - 1, day);
        return date.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        });
    };

    if (isLoading) {
        return (
            <IonPage>
                <IonHeader>
                    <IonToolbar>
                        <IonButtons slot="start">
                            <IonBackButton defaultHref="/" />
                        </IonButtons>
                        <IonTitle>Entry</IonTitle>
                    </IonToolbar>
                </IonHeader>
                <IonContent className="ion-padding" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <IonSpinner />
                </IonContent>
            </IonPage>
        );
    }

    if (!entry) {
        return (
            <IonPage>
                <IonHeader>
                    <IonToolbar>
                        <IonButtons slot="start">
                            <IonBackButton defaultHref="/" />
                        </IonButtons>
                        <IonTitle>Entry</IonTitle>
                    </IonToolbar>
                </IonHeader>
                <IonContent className="ion-padding">
                    <div style={{ textAlign: 'center', padding: '48px' }}>
                        <h2>Entry not found</h2>
                        <p style={{ color: 'var(--ion-color-medium)' }}>
                            This entry may have been deleted or doesn't exist.
                        </p>
                    </div>
                </IonContent>
            </IonPage>
        );
    }

    return (
        <IonPage>
            <IonHeader>
                <IonToolbar>
                    <IonButtons slot="start">
                        <IonBackButton defaultHref="/" />
                    </IonButtons>
                    <IonTitle>{formatDate(entry.date)}</IonTitle>
                    <IonButtons slot="end">
                        <IonButton onClick={loadEntry}>
                            <IonIcon icon={refreshOutline} />
                        </IonButton>
                        <IonButton onClick={handleArchive} color="warning">
                            <IonIcon icon={archiveOutline} />
                        </IonButton>
                    </IonButtons>
                </IonToolbar>
            </IonHeader>

            <IonContent fullscreen className="ion-padding">
                {/* Refined Output */}
                <IonCard>
                    <IonCardHeader>
                        <IonCardTitle>Summary</IonCardTitle>
                    </IonCardHeader>
                    <IonCardContent>
                        {entry.refined_output ? (
                            <p style={{ whiteSpace: 'pre-wrap' }}>{entry.refined_output}</p>
                        ) : (
                            <p style={{ color: 'var(--ion-color-medium)', fontStyle: 'italic' }}>
                                No summary yet. Chat with the assistant to generate insights.
                            </p>
                        )}
                    </IonCardContent>
                </IonCard>

                {/* Conversations */}
                <h2 style={{ margin: '24px 0 16px' }}>Conversations</h2>
                {entry.conversations.length === 0 ? (
                    <div
                        style={{
                            textAlign: 'center',
                            padding: '32px',
                            backgroundColor: 'var(--ion-color-light)',
                            borderRadius: '12px',
                        }}
                    >
                        <p style={{ color: 'var(--ion-color-medium)' }}>No conversations yet.</p>
                        <IonButton onClick={handleOpenChat}>
                            <IonIcon icon={chatbubbleOutline} slot="start" />
                            Start a Conversation
                        </IonButton>
                    </div>
                ) : (
                    <>
                        {entry.conversations.map((conv, index) => (
                            <IonCard key={conv.id}>
                                <IonCardHeader>
                                    <IonCardTitle style={{ fontSize: '16px' }}>
                                        Conversation {index + 1}
                                    </IonCardTitle>
                                    <p style={{ fontSize: '12px', color: 'var(--ion-color-medium)', margin: 0 }}>
                                        {new Date(conv.started_at).toLocaleString()} · {conv.messages.length} messages
                                    </p>
                                </IonCardHeader>
                                <IonCardContent>
                                    {conv.messages.slice(-2).map((msg, msgIndex) => (
                                        <div
                                            key={msgIndex}
                                            style={{
                                                padding: '8px 12px',
                                                marginBottom: '8px',
                                                borderRadius: '8px',
                                                backgroundColor:
                                                    msg.role === 'user'
                                                        ? 'var(--ion-color-primary-tint)'
                                                        : 'var(--ion-color-light)',
                                            }}
                                        >
                                            <strong style={{ fontSize: '12px', textTransform: 'capitalize' }}>
                                                {msg.role}:
                                            </strong>
                                            <p style={{ margin: '4px 0 0', fontSize: '14px' }}>
                                                {msg.content.substring(0, 100)}
                                                {msg.content.length > 100 ? '...' : ''}
                                            </p>
                                        </div>
                                    ))}
                                </IonCardContent>
                            </IonCard>
                        ))}

                        <IonButton expand="block" onClick={handleOpenChat} style={{ marginTop: '16px' }}>
                            <IonIcon icon={chatbubbleOutline} slot="start" />
                            Continue Conversation
                        </IonButton>
                    </>
                )}

                {/* Chat Modal */}
                <ChatModal
                    isOpen={isChatOpen}
                    onClose={handleCloseChat}
                    entryId={entry.id}
                    existingConversation={
                        entry.conversations.length > 0
                            ? entry.conversations[entry.conversations.length - 1]
                            : null
                    }
                />
            </IonContent>
        </IonPage>
    );
};

export default EntryDetail;
