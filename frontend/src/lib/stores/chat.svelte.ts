import { chatApi } from '$lib/api';
import { addToast } from '$lib/stores/toast.svelte';
import type { ChatAction, ChatMessage, TaskProposal } from '$lib/types';

function createChatStore() {
  let messages = $state<ChatMessage[]>([]);
  let conversationId = $state<string | null>(null);
  let loading = $state(false);
  let pendingProposals = $state<TaskProposal[]>([]);
  let pendingActions = $state<ChatAction[]>([]);
  let extractingMsgIndex = $state<number | null>(null);

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
    get pendingActions() {
      return pendingActions;
    },

    async sendMessage(text: string, model?: string) {
      if (!text.trim() || loading) return;
      loading = true;

      // Add user message optimistically
      messages = [...messages, { role: 'user', content: text, created_at: new Date().toISOString() }];

      try {
        const res = await chatApi.send(text, conversationId ?? undefined, model);
        conversationId = res.conversation_id;

        const assistantMsg: ChatMessage = {
          role: 'assistant',
          content: res.reply,
          created_at: new Date().toISOString(),
        };
        if (res.proposals.length > 0) {
          assistantMsg.proposals = res.proposals;
        }
        const allActions = [...(res.actions || []), ...(res.pending_actions || [])];
        if (allActions.length > 0) {
          assistantMsg.actions = allActions;
        }
        messages = [...messages, assistantMsg];

        if (res.proposals.length > 0) {
          pendingProposals = [...pendingProposals, ...res.proposals];
        }
        if (res.pending_actions && res.pending_actions.length > 0) {
          pendingActions = [...pendingActions, ...res.pending_actions];
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
      pendingActions = [];
      extractingMsgIndex = null;
    },

    removeProposal(id: string) {
      pendingProposals = pendingProposals.filter((p) => p.id !== id);
    },

    updateProposal(proposalId: string, updated: TaskProposal) {
      pendingProposals = pendingProposals.map((p) => (p.id === proposalId ? updated : p));
      messages = messages.map((msg) => {
        if (msg.proposals) {
          return { ...msg, proposals: msg.proposals.map((p) => (p.id === proposalId ? updated : p)) };
        }
        return msg;
      });
    },

    addSystemMessage(content: string) {
      messages = [...messages, { role: 'assistant', content, created_at: new Date().toISOString() }];
    },

    removePendingAction(taskId: number, taskTitle?: string) {
      if (taskId === 0 && taskTitle) {
        // For create actions, match by title since task_id is 0
        pendingActions = pendingActions.filter(
          (a) => !(a.type === 'create' && a.task_title === taskTitle),
        );
      } else {
        pendingActions = pendingActions.filter((a) => a.task_id !== taskId);
      }
    },

    addMessage(msg: ChatMessage) {
      messages = [...messages, msg];
    },

    setExtractingProposals(proposals: TaskProposal[]) {
      if (extractingMsgIndex !== null && extractingMsgIndex < messages.length) {
        const msg = messages[extractingMsgIndex];
        messages = [
          ...messages.slice(0, extractingMsgIndex),
          { ...msg, proposals: [...proposals] },
          ...messages.slice(extractingMsgIndex + 1),
        ];
      } else {
        extractingMsgIndex = messages.length;
        messages = [
          ...messages,
          {
            role: 'assistant',
            content: '',
            created_at: new Date().toISOString(),
            proposals: [...proposals],
          },
        ];
      }
      pendingProposals = [...proposals];
    },

    finishExtracting() {
      extractingMsgIndex = null;
    },

    clear() {
      messages = [];
      conversationId = null;
      pendingProposals = [];
      pendingActions = [];
      extractingMsgIndex = null;
    },
  };
}

export const chatStore = createChatStore();
