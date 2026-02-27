/**
 * SyncIndicator Component
 * 
 * Shows sync status in the header.
 */

import React from 'react';
import { IonBadge, IonIcon, IonSpinner } from '@ionic/react';
import {
    cloudDoneOutline,
    cloudOfflineOutline,
    alertCircleOutline,
    syncOutline,
} from 'ionicons/icons';
import { useSync } from '../hooks/useSync';

const SyncIndicator: React.FC = () => {
    const { syncStatus, pendingCount, isOnline } = useSync();

    if (!isOnline) {
        return (
            <IonBadge color="warning" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <IonIcon icon={cloudOfflineOutline} />
                <span>Offline</span>
            </IonBadge>
        );
    }

    if (syncStatus === 'syncing') {
        return (
            <IonBadge color="primary" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <IonSpinner name="crescent" style={{ width: '14px', height: '14px' }} />
                <span>Syncing</span>
            </IonBadge>
        );
    }

    if (syncStatus === 'error') {
        return (
            <IonBadge color="danger" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <IonIcon icon={alertCircleOutline} />
                <span>Sync Error</span>
            </IonBadge>
        );
    }

    if (pendingCount > 0) {
        return (
            <IonBadge color="medium" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <IonIcon icon={syncOutline} />
                <span>{pendingCount} pending</span>
            </IonBadge>
        );
    }

    return (
        <IonBadge color="success" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <IonIcon icon={cloudDoneOutline} />
            <span>Synced</span>
        </IonBadge>
    );
};

export default SyncIndicator;
