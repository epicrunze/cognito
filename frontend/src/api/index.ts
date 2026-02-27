// Barrel exports for API
export { api, apiClient, isOnline, getApiUrl, type ApiError } from './client';
export { login, logout, getMe, refreshToken, type User } from './auth';
export { performSync, type SyncRequest, type SyncResponse } from './sync';
export { sendChatMessage, getChatHistory, type ChatRequest, type ChatResponse } from './chat';
