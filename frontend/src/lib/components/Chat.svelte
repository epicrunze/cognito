<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';
	import {
		chatMessages,
		chatLoading,
		chatError,
		offlineQueueCount,
		sendMessage,
		clearChat,
		initializeChat
	} from '$lib/stores/chat';
	import type { Message, Conversation } from '$lib/db';

	// Props
	export let entryId: string;
	export let existingConversation: Conversation | null = null;

	// Local state
	let messageInput = '';
	let messagesContainer: HTMLElement;

	// Initialize chat with existing conversation
	onMount(() => {
		if (existingConversation) {
			initializeChat(existingConversation.messages, existingConversation.id);
		} else {
			clearChat();
		}

		return () => {
			// Cleanup on unmount
		};
	});

	// Scroll to bottom when messages change
	afterUpdate(() => {
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	});

	// Handle send message
	async function handleSend() {
		const message = messageInput.trim();
		if (!message || $chatLoading) return;

		messageInput = '';
		await sendMessage(entryId, message);
	}

	// Handle keydown for Enter to send
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSend();
		}
	}

	// Format timestamp
	function formatTime(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleTimeString('en-US', {
			hour: 'numeric',
			minute: '2-digit',
			hour12: true
		});
	}
</script>

<div class="chat-container flex flex-col h-full bg-white">
	<!-- Offline Queue Indicator -->
	{#if $offlineQueueCount > 0}
		<div
			class="offline-indicator bg-warning/20 text-warning px-4 py-2 text-sm flex items-center gap-2"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
				/>
			</svg>
			<span>{$offlineQueueCount} message{$offlineQueueCount > 1 ? 's' : ''} queued offline</span>
		</div>
	{/if}

	<!-- Error Message -->
	{#if $chatError}
		<div class="error-banner bg-error/20 text-error px-4 py-2 text-sm">
			{$chatError}
		</div>
	{/if}

	<!-- Messages Area -->
	<div bind:this={messagesContainer} class="messages-area flex-1 overflow-y-auto p-4 space-y-4">
		{#if $chatMessages.length === 0}
			<!-- Empty state -->
			<div class="empty-state text-center py-12 text-text-secondary">
				<svg
					class="w-16 h-16 mx-auto mb-4 opacity-50"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
					/>
				</svg>
				<p class="text-lg font-medium">Start a conversation</p>
				<p class="text-sm mt-2">Share your thoughts and I'll help you explore them.</p>
			</div>
		{:else}
			{#each $chatMessages as message (message.timestamp)}
				<div class="message {message.role === 'user' ? 'message-user' : 'message-assistant'}">
					<div
						class="message-bubble {message.role === 'user'
							? 'bg-primary text-white ml-auto'
							: 'bg-surface-alt text-text-primary mr-auto'}"
					>
						<p class="message-content whitespace-pre-wrap">{message.content}</p>
						<span class="message-time text-xs opacity-70 mt-1 block">
							{formatTime(message.timestamp)}
						</span>
					</div>
				</div>
			{/each}
		{/if}

		<!-- Typing indicator -->
		{#if $chatLoading}
			<div class="message message-assistant">
				<div class="message-bubble bg-surface-alt text-text-primary mr-auto">
					<div class="typing-indicator flex gap-1">
						<span class="dot"></span>
						<span class="dot"></span>
						<span class="dot"></span>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Input Area -->
	<div class="input-area border-t border-primary-light/20 p-4">
		<div class="input-wrapper flex gap-3">
			<textarea
				bind:value={messageInput}
				on:keydown={handleKeydown}
				placeholder="Share your thoughts..."
				rows="1"
				class="flex-1 resize-none rounded-xl border border-primary-light/30 bg-surface px-4 py-3 text-text-primary placeholder:text-text-secondary focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
				disabled={$chatLoading}
			></textarea>
			<button
				on:click={handleSend}
				disabled={!messageInput.trim() || $chatLoading}
				class="send-button p-3 rounded-xl bg-primary text-white hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
				title="Send message"
			>
				{#if $chatLoading}
					<svg class="w-6 h-6 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
						/>
					</svg>
				{:else}
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
						/>
					</svg>
				{/if}
			</button>
		</div>
	</div>
</div>

<style>
	.chat-container {
		min-height: 400px;
	}

	.messages-area {
		background-color: #f8fafc;
	}

	.message {
		display: flex;
	}

	.message-bubble {
		max-width: 80%;
		padding: 0.75rem 1rem;
		border-radius: 1rem;
	}

	.message-user .message-bubble {
		border-bottom-right-radius: 0.25rem;
	}

	.message-assistant .message-bubble {
		border-bottom-left-radius: 0.25rem;
	}

	.bg-surface-alt {
		background-color: rgba(var(--primary-rgb, 99, 102, 241), 0.1);
	}

	.typing-indicator {
		padding: 0.5rem 0;
	}

	.typing-indicator .dot {
		width: 8px;
		height: 8px;
		background-color: currentColor;
		border-radius: 50%;
		animation: bounce 1.4s infinite ease-in-out both;
	}

	.typing-indicator .dot:nth-child(1) {
		animation-delay: -0.32s;
	}

	.typing-indicator .dot:nth-child(2) {
		animation-delay: -0.16s;
	}

	@keyframes bounce {
		0%,
		80%,
		100% {
			transform: scale(0);
		}
		40% {
			transform: scale(1);
		}
	}

	textarea {
		min-height: 48px;
		max-height: 150px;
	}
</style>
