/**
 * Logging utility for Cognito frontend.
 *
 * Provides structured logging with configurable levels.
 */

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

// Log level priority for filtering
const LOG_LEVELS: Record<LogLevel, number> = {
    debug: 0,
    info: 1,
    warn: 2,
    error: 3,
};

// Get configured log level from environment or default to 'info'
function getConfiguredLevel(): LogLevel {
    if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_LOG_LEVEL) {
        const level = import.meta.env.VITE_LOG_LEVEL.toLowerCase();
        if (level in LOG_LEVELS) {
            return level as LogLevel;
        }
    }
    // Default to 'debug' in development, 'info' in production
    if (typeof import.meta !== 'undefined' && import.meta.env?.DEV) {
        return 'debug';
    }
    return 'info';
}

const configuredLevel = getConfiguredLevel();

/**
 * Check if a log level should be output.
 */
function shouldLog(level: LogLevel): boolean {
    return LOG_LEVELS[level] >= LOG_LEVELS[configuredLevel];
}

/**
 * Format a log message with timestamp and context.
 */
function formatMessage(level: LogLevel, message: string, context?: Record<string, unknown>): string {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${level.toUpperCase()}]`;

    if (context && Object.keys(context).length > 0) {
        const contextStr = Object.entries(context)
            .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
            .join(' ');
        return `${prefix} ${message} | ${contextStr}`;
    }

    return `${prefix} ${message}`;
}

/**
 * Logger interface for consistent logging throughout the app.
 */
export const logger = {
    /**
     * Log a debug message (development only by default).
     */
    debug(message: string, context?: Record<string, unknown>): void {
        if (!shouldLog('debug')) return;
        console.debug(formatMessage('debug', message, context));
    },

    /**
     * Log an info message.
     */
    info(message: string, context?: Record<string, unknown>): void {
        if (!shouldLog('info')) return;
        console.info(formatMessage('info', message, context));
    },

    /**
     * Log a warning message.
     */
    warn(message: string, context?: Record<string, unknown>): void {
        if (!shouldLog('warn')) return;
        console.warn(formatMessage('warn', message, context));
    },

    /**
     * Log an error message.
     */
    error(message: string, context?: Record<string, unknown>): void {
        if (!shouldLog('error')) return;
        console.error(formatMessage('error', message, context));
    },

    /**
     * Log with a specific level.
     */
    log(level: LogLevel, message: string, context?: Record<string, unknown>): void {
        switch (level) {
            case 'debug':
                this.debug(message, context);
                break;
            case 'info':
                this.info(message, context);
                break;
            case 'warn':
                this.warn(message, context);
                break;
            case 'error':
                this.error(message, context);
                break;
        }
    },
};

export default logger;
