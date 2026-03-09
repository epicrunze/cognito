import { chatApi } from '$lib/api';
import { addToast } from '$lib/stores/toast.svelte';
import type { ChatMessage, TaskProposal } from '$lib/types';

function createChatStore() {
  let messages = $state<ChatMessage[]>([]);
  let conversationId = $state<string | null>(null);
  let loading = $state(false);
  let pendingProposals = $state<TaskProposal[]>([]);

  return {
    get messages() {
      return messages;
    },
    get conversationId() {
      return conversationId;
    },
    get loading() {
      return loading;
    },
    get pendingProposals() {
      return pendingProposals;
    },

    async sendMessage(text: string, model?: string) {
      if (!text.trim() || loading) return;
      loading = true;

      // Add user message optimistically
      messages = [...messages, { role: 'user', content: text, created_at: new Date().toISOString() }];

      try {
        const res = await chatApi.send(text, conversationId ?? undefined, model);
        conversationId = res.conversation_id;
        messages = [
          ...messages,
          {
            role: 'assistant',
            content: res.reply,
            proposals: res.proposals.length > 0 ? res.proposals : undefined,
            created_at: new Date().toISOString(),
          },
        ];
        if (res.proposals.length > 0) {
          pendingProposals = [...pendingProposals, ...res.proposals];
        }
      } catch (e) {
        addToast(e instanceof Error ? e.message : 'Chat failed', 'error');
        // Remove the user message on error
        messages = messages.slice(0, -1);
      } finally {
        loading = false;
      }
    },

    startNewConversation() {
      messages = [];
      conversationId = null;
      pendingProposals = [];
    },

    removeProposal(id: string) {
      pendingProposals = pendingProposals.filter((p) => p.id !== id);
    },

    clear() {
      messages = [];
      conversationId = null;
      pendingProposals = [];
    },
  };
}

export const chatStore = createChatStore();
