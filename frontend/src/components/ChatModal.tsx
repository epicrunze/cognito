/**
 * Chat Modal Component
 * 
 * Bottom sheet modal for journal entry conversations using Ionic's IonModal.
 */

import React, { useState, useRef, useEffect } from 'react';
import {
    IonModal,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonButtons,
    IonButton,
    IonContent,
    IonFooter,
    IonTextarea,
    IonIcon,
    IonSpinner,
} from '@ionic/react';
import { closeOutline, sendOutline } from 'ionicons/icons';
import type { Message, Conversation } from '../db';
import { sendChatMessage } from '../api/chat';

interface ChatModalProps {
    isOpen: boolean;
    onClose: () => void;
    entryId: string;
    existingConversation?: Conversation | null;
    onConversationUpdate?: (messages: Message[]) => void;
}

/**
 * Format timestamp
 */
function formatTime(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
    });
}

const ChatModal: React.FC<ChatModalProps> = ({
    isOpen,
    onClose,
    entryId,
    existingConversation,
    onConversationUpdate,
}) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [conversationId, setConversationId] = useState<string | null>(null);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const contentRef = useRef<HTMLIonContentElement>(null);

    // Initialize with existing conversation
    useEffect(() => {
        if (existingConversation) {
            setMessages(existingConversation.messages);
            setConversationId(existingConversation.id);
        } else {
            setMessages([]);
            setConversationId(null);
        }
    }, [existingConversation, isOpen]);

    // Scroll to bottom when messages change
    useEffect(() => {
        if (contentRef.current) {
            contentRef.current.scrollToBottom(300);
        }
    }, [messages]);

    const handleSend = async () => {
        const messageText = input.trim();
        if (!messageText || isLoading) return;

        setInput('');
        setError(null);

        // Add user message immediately
        const userMessage: Message = {
            role: 'user',
            content: messageText,
            timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, userMessage]);

        setIsLoading(true);

        try {
            const response = await sendChatMessage({
                entry_id: entryId,
                message: messageText,
                conversation_id: conversationId ?? undefined,
            });

            setConversationId(response.conversation_id);
            setMessages(response.messages);
            onConversationUpdate?.(response.messages);
        } catch (err) {
            console.error('Chat error:', err);
            setError('Failed to send message. Please try again.');
            // Mark the message as pending
            setMessages((prev) =>
                prev.map((m, i) =>
                    i === prev.length - 1 ? { ...m, pending_response: true } : m
                )
            );
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <IonModal
            isOpen={isOpen}
            onDidDismiss={onClose}
            breakpoints={[0, 0.5, 0.85]}
            initialBreakpoint={0.85}
            backdropDismiss
            handle
        >
            <IonHeader>
                <IonToolbar>
                    <IonTitle>Chat</IonTitle>
                    <IonButtons slot="end">
                        <IonButton onClick={onClose}>
                            <IonIcon icon={closeOutline} />
                        </IonButton>
                    </IonButtons>
                </IonToolbar>
            </IonHeader>

            <IonContent ref={contentRef} className="ion-padding">
                {messages.length === 0 ? (
                    <div
                        style={{
                            textAlign: 'center',
                            padding: '48px 16px',
                            color: 'var(--ion-color-medium)',
                        }}
                    >
                        <p style={{ fontSize: '18px', fontWeight: 500 }}>Start a conversation</p>
                        <p style={{ fontSize: '14px', marginTop: '8px' }}>
                            Share your thoughts and I'll help you explore them.
                        </p>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {messages.map((message, index) => (
                            <div
                                key={index}
                                style={{
                                    display: 'flex',
                                    justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                                }}
                            >
                                <div
                                    style={{
                                        maxWidth: '80%',
                                        padding: '12px 16px',
                                        borderRadius: '16px',
                                        borderBottomRightRadius: message.role === 'user' ? '4px' : '16px',
                                        borderBottomLeftRadius: message.role === 'user' ? '16px' : '4px',
                                        backgroundColor:
                                            message.role === 'user'
                                                ? 'var(--ion-color-primary)'
                                                : 'var(--ion-color-light)',
                                        color:
                                            message.role === 'user'
                                                ? 'var(--ion-color-primary-contrast)'
                                                : 'var(--ion-text-color)',
                                        opacity: message.pending_response ? 0.7 : 1,
                                        border: message.pending_response
                                            ? '1px dashed var(--ion-color-warning)'
                                            : 'none',
                                    }}
                                >
                                    <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{message.content}</p>
                                    <span
                                        style={{
                                            display: 'block',
                                            fontSize: '11px',
                                            marginTop: '4px',
                                            opacity: 0.7,
                                        }}
                                    >
                                        {formatTime(message.timestamp)}
                                        {message.pending_response && (
                                            <span
                                                style={{
                                                    marginLeft: '8px',
                                                    color: 'var(--ion-color-warning)',
                                                }}
                                            >
                                                ⏳ Awaiting response
                                            </span>
                                        )}
                                    </span>
                                </div>
                            </div>
                        ))}

                        {isLoading && (
                            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                                <div
                                    style={{
                                        padding: '12px 16px',
                                        borderRadius: '16px',
                                        borderBottomLeftRadius: '4px',
                                        backgroundColor: 'var(--ion-color-light)',
                                    }}
                                >
                                    <IonSpinner name="dots" />
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {error && (
                    <div
                        style={{
                            marginTop: '12px',
                            padding: '8px 12px',
                            backgroundColor: 'var(--ion-color-danger-tint)',
                            color: 'var(--ion-color-danger)',
                            borderRadius: '8px',
                            fontSize: '14px',
                        }}
                    >
                        {error}
                    </div>
                )}
            </IonContent>

            <IonFooter>
                <IonToolbar>
                    <div style={{ display: 'flex', gap: '8px', padding: '8px' }}>
                        <IonTextarea
                            value={input}
                            onIonInput={(e) => setInput(e.detail.value || '')}
                            onKeyDown={handleKeyDown}
                            placeholder="Share your thoughts..."
                            autoGrow
                            rows={1}
                            disabled={isLoading}
                            style={{
                                flex: 1,
                                '--padding-start': '12px',
                                '--padding-end': '12px',
                                '--padding-top': '8px',
                                '--padding-bottom': '8px',
                                '--border-radius': '16px',
                                '--background': 'var(--ion-color-light)',
                            }}
                        />
                        <IonButton
                            onClick={handleSend}
                            disabled={!input.trim() || isLoading}
                            shape="round"
                            size="default"
                        >
                            {isLoading ? (
                                <IonSpinner name="crescent" />
                            ) : (
                                <IonIcon icon={sendOutline} />
                            )}
                        </IonButton>
                    </div>
                </IonToolbar>
            </IonFooter>
        </IonModal>
    );
};

export default ChatModal;
