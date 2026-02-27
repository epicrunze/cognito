/**
 * EntryCard Component
 * 
 * Displays a journal entry with swipe actions using Ionic's IonItemSliding.
 */

import React from 'react';
import {
    IonCard,
    IonCardHeader,
    IonCardContent,
    IonCardTitle,
    IonBadge,
    IonItemSliding,
    IonItem,
    IonItemOptions,
    IonItemOption,
    IonLabel,
    IonIcon,
} from '@ionic/react';
import { chatbubbleOutline, archiveOutline, eyeOutline } from 'ionicons/icons';
import type { Entry } from '../db';

interface EntryCardProps {
    entry: Entry;
    onClick?: () => void;
    onChat?: () => void;
    onArchive?: () => void;
}

/**
 * Format date nicely - Today, Yesterday, or Month Day
 */
function formatDate(dateStr: string): string {
    const [year, month, day] = dateStr.split('-').map(Number);
    const date = new Date(year, month - 1, day);

    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const yesterdayOnly = new Date(
        yesterday.getFullYear(),
        yesterday.getMonth(),
        yesterday.getDate()
    );

    if (dateOnly.getTime() === todayOnly.getTime()) {
        return 'Today';
    } else if (dateOnly.getTime() === yesterdayOnly.getTime()) {
        return 'Yesterday';
    } else {
        return date.toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: date.getFullYear() !== today.getFullYear() ? 'numeric' : undefined,
        });
    }
}

/**
 * Format relative time
 */
function formatRelativeTime(timestamp: string): string {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Truncate text
 */
function truncate(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength).trim() + '...';
}

/**
 * Get relevance color
 */
function getRelevanceColor(score: number): string {
    if (score >= 0.8) return 'success';
    if (score >= 0.5) return 'warning';
    return 'medium';
}

const EntryCard: React.FC<EntryCardProps> = ({
    entry,
    onClick,
    onChat,
    onArchive,
}) => {
    return (
        <IonItemSliding>
            {/* Left swipe option - Chat */}
            <IonItemOptions side="start">
                <IonItemOption color="primary" onClick={onChat}>
                    <IonIcon slot="icon-only" icon={chatbubbleOutline} />
                </IonItemOption>
            </IonItemOptions>

            <IonItem lines="none" onClick={onClick} button detail={false}>
                <IonCard style={{ width: '100%', margin: 0 }}>
                    <IonCardHeader>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                {/* Relevance Indicator */}
                                <IonBadge
                                    color={getRelevanceColor(entry.relevance_score)}
                                    style={{ width: '8px', height: '8px', borderRadius: '50%', padding: 0 }}
                                />
                                <IonCardTitle>{formatDate(entry.date)}</IonCardTitle>
                            </div>
                            {/* Status Badge */}
                            <IonBadge color={entry.status === 'active' ? 'success' : 'medium'}>
                                {entry.status}
                            </IonBadge>
                        </div>
                    </IonCardHeader>

                    <IonCardContent>
                        {/* Preview Text */}
                        {entry.refined_output ? (
                            <p style={{ color: 'var(--ion-color-medium)', marginBottom: '12px' }}>
                                {truncate(entry.refined_output, 150)}
                            </p>
                        ) : (
                            <p style={{ color: 'var(--ion-color-medium)', fontStyle: 'italic', marginBottom: '12px' }}>
                                No summary yet
                            </p>
                        )}

                        {/* Footer Metadata */}
                        <div
                            style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                fontSize: '12px',
                                color: 'var(--ion-color-medium)',
                                paddingTop: '8px',
                                borderTop: '1px solid var(--ion-color-light)',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                {/* Conversation Count */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <IonIcon icon={chatbubbleOutline} style={{ fontSize: '14px' }} />
                                    <span>
                                        {entry.conversations.length}{' '}
                                        {entry.conversations.length === 1 ? 'conversation' : 'conversations'}
                                    </span>
                                </div>

                                {/* Interaction Count */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <IonIcon icon={eyeOutline} style={{ fontSize: '14px' }} />
                                    <span>{entry.interaction_count}</span>
                                </div>
                            </div>

                            {/* Last Interacted */}
                            <span>{formatRelativeTime(entry.last_interacted_at)}</span>
                        </div>
                    </IonCardContent>
                </IonCard>
            </IonItem>

            {/* Right swipe option - Archive */}
            <IonItemOptions side="end">
                <IonItemOption color="warning" onClick={onArchive}>
                    <IonIcon slot="icon-only" icon={archiveOutline} />
                </IonItemOption>
            </IonItemOptions>
        </IonItemSliding>
    );
};

export default EntryCard;
