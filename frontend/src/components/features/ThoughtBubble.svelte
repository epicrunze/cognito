<script lang="ts">
  import type { Task, TaskProposal, Subtask } from '$lib/types';
  import { projectsStore } from '$lib/stores.svelte';
  import { updateTask, toggleDone, deleteTask } from '$lib/stores/taskMutations';
  import { filterStore } from '$lib/stores/filter.svelte';
  import { bubbleStore } from '$lib/stores/bubble.svelte';
  import { taskDetailStore } from '$lib/stores/taskDetail.svelte';
  import { proposalsApi, subtasksApi } from '$lib/api';
  import { addToast } from '$lib/stores/toast.svelte';
  import { onMount, tick } from 'svelte';
  import PriorityIndicator from '$components/ui/PriorityIndicator.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import DateDisplay from '$components/ui/DateDisplay.svelte';
  import DatePicker from '$components/ui/DatePicker.svelte';
  import Checkbox from '$components/ui/Checkbox.svelte';


  let {
    task,
    proposal,
    compact = false,
    proposalMode = false,
    selected = false,
    onselect,
    onapprove,
    onreject,
    onproposalupdate,
    ontoggle,
    onclick,
  }: {
    task?: Task;
    proposal?: TaskProposal;
    compact?: boolean;
    proposalMode?: boolean;
    selected?: boolean;
    onselect?: () => void;
    onapprove?: () => void;
    onreject?: () => void;
    onproposalupdate?: (p: TaskProposal) => void;
    ontoggle?: () => void;
    onclick?: () => void;
  } = $props();

  let hovering = $state(false);

  // --- Unified BubbleData ---
  interface BubbleData {
    id: number | string;
    title: string;
    description: string;
    priority: number;
    dueDate: string | null;
    projectId: number | null;
    projectName: string | null;
    labels: { id?: number; title: string; hex_color?: string }[];
    done: boolean;
    attachmentCount: number;
    estimatedMinutes: number | null;
    isProposal: boolean;
    status: string | null;
  }

  const data = $derived.by((): BubbleData => {
    if (proposal) {
      return {
        id: proposal.id,
        title: proposal.title,
        description: proposal.description,
        priority: proposal.priority,
        dueDate: proposal.due_date,
        projectId: proposal.project_id,
        projectName: proposal.project_name,
        labels: proposal.labels.map(l => ({ title: l })),
        done: false,
        attachmentCount: 0,
        estimatedMinutes: proposal.estimated_minutes,
        isProposal: true,
        status: proposal.status,
      };
    }
    if (task) {
      return {
        id: task.id,
        title: task.title,
        description: task.description,
        priority: task.priority,
        dueDate: task.due_date && !task.due_date.startsWith('0001-01-01') ? task.due_date : null,
        projectId: task.project_id,
        projectName: null,
        labels: task.labels,
        done: task.done,
        attachmentCount: task.attachments?.length ?? 0,
        estimatedMinutes: null,
        isProposal: false,
        status: null,
      };
    }
    return { id: 0, title: '', description: '', priority: 3, dueDate: null, projectId: null, projectName: null, labels: [], done: false, attachmentCount: 0, estimatedMinutes: null, isProposal: false, status: null };
  });

  const project = $derived(data.projectId ? projectsStore.projects.find(p => p.id === data.projectId) : null);
  const projectColor = $derived(project?.hex_color || '');
  const isOverdue = $derived(Boolean(!data.done && data.dueDate && new Date(data.dueDate) < new Date()));
  const isAiTagged = $derived(data.isProposal || (typeof data.id === 'number' && filterStore.aiTaggedIds.has(data.id)));
  const viewed = $derived(typeof data.id === 'number' && filterStore.viewedTaskIds.has(data.id));
  const showGlow = $derived(isAiTagged && (!viewed || data.isProposal));

  const expanded = $derived(bubbleStore.expandedTaskId === data.id);
  const supportsVT = $derived(typeof document !== 'undefined' && !!document.startViewTransition);

  // Auto-resize textareas to fit content
  function autoResize(el: HTMLTextAreaElement) {
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }

  let titleTextarea: HTMLTextAreaElement | undefined = $state();
  let descTextarea: HTMLTextAreaElement | undefined = $state();

  $effect(() => {
    if (expanded) {
      tick().then(() => {
        if (titleTextarea) autoResize(titleTextarea);
        if (descTextarea) autoResize(descTextarea);
      });
    }
  });

  // --- Priority as presence ---
  const presenceOpacity = $derived.by(() => {
    if (data.done) return 0.35;
    const p = data.priority;
    if (p >= 4) return 1;
    if (p === 3) return 0.85;
    if (p === 2) return 0.65;
    return 0.55;
  });

  const titleColor = $derived.by(() => {
    if (data.done) return 'var(--text-tertiary)';
    const p = data.priority;
    if (p >= 5) return '#fff';
    if (p >= 3) return 'var(--text-primary)';
    return 'var(--text-secondary)';
  });

  const shadowStyle = $derived.by(() => {
    if (compact || data.done) return 'none';
    if (expanded) return 'var(--shadow-md)';
    if (hovering) return 'var(--shadow-lift)';
    const p = data.priority;
    if (p >= 5) return 'var(--shadow-md)';
    if (p >= 3) return 'var(--shadow-sm)';
    return 'none';
  });

  // --- Bubble size by priority (spatial gravity) ---
  const bubbleWidth = $derived.by(() => {
    const widths: Record<number, number> = { 5: 220, 4: 210, 3: 200, 2: 185, 1: 175 };
    return widths[data.priority] ?? 200;
  });
  const bubbleMinHeight = $derived.by(() => {
    const heights: Record<number, number> = { 5: 95, 4: 92, 3: 90, 2: 85, 1: 82 };
    return heights[data.priority] ?? 90;
  });

  // --- Expanded state editing ---
  let editTitle = $state('');
  let editDescription = $state('');
  let titleTimer: ReturnType<typeof setTimeout> | null = null;
  let descTimer: ReturnType<typeof setTimeout> | null = null;

  // Priority hover preview
  let hoveredPriority = $state<number | null>(null);

  // Date picker portal state
  let showDatePicker = $state(false);
  let dateAnchorRef = $state<HTMLElement | undefined>(undefined);
  let datePortalRef = $state<HTMLDivElement | null>(null);
  let datePortalStyle = $state('');

  // Subtask state
  let subtasks: Subtask[] = $state([]);
  let subtasksLoading = $state(false);
  let newSubtaskTitle = $state('');
  let addingSubtask = $state(false);

  // Fetch subtasks when expanded (real tasks only)
  $effect(() => {
    if (expanded && !data.isProposal && task) {
      subtasksLoading = true;
      subtasksApi.list(task.id).then(list => {
        subtasks = list;
      }).catch(() => {
        subtasks = [];
      }).finally(() => {
        subtasksLoading = false;
      });
    }
    if (!expanded) {
      subtasks = [];
      newSubtaskTitle = '';
    }
  });

  // Re-fetch subtasks when changed externally (e.g. from TaskDetailContent)
  $effect(() => {
    if (!expanded || data.isProposal || !task) return;
    const taskId = task.id;
    function onSubtasksChanged(e: Event) {
      const detail = (e as CustomEvent<{ taskId: number }>).detail;
      if (detail.taskId === taskId) {
        subtasksApi.list(taskId).then(list => { subtasks = list; }).catch(() => {});
      }
    }
    window.addEventListener('subtasks-changed', onSubtasksChanged);
    return () => window.removeEventListener('subtasks-changed', onSubtasksChanged);
  });

  function notifySubtasksChanged(taskId: number) {
    window.dispatchEvent(new CustomEvent('subtasks-changed', { detail: { taskId } }));
  }

  async function toggleSubtask(st: Subtask) {
    if (!task) return;
    const prev = st.done;
    st.done = !st.done;
    subtasks = [...subtasks];
    try {
      await subtasksApi.update(task.id, st.id, { done: st.done });
      notifySubtasksChanged(task.id);
    } catch {
      st.done = prev;
      subtasks = [...subtasks];
      addToast('Failed to update subtask', 'error');
    }
  }

  async function handleAddSubtask() {
    if (!task || !newSubtaskTitle.trim()) return;
    addingSubtask = true;
    try {
      const created = await subtasksApi.create(task.id, { title: newSubtaskTitle.trim(), project_id: task.project_id });
      subtasks = [created, ...subtasks];
      newSubtaskTitle = '';
      notifySubtasksChanged(task.id);
    } catch {
      addToast('Failed to add subtask', 'error');
    } finally {
      addingSubtask = false;
    }
  }

  async function deleteSubtask(st: Subtask) {
    if (!task) return;
    const idx = subtasks.indexOf(st);
    subtasks = subtasks.filter(s => s !== st);
    try {
      await subtasksApi.delete(task.id, st.id);
      notifySubtasksChanged(task.id);
    } catch {
      subtasks = [...subtasks.slice(0, idx), st, ...subtasks.slice(idx)];
      addToast('Failed to delete subtask', 'error');
    }
  }

  function openDatePicker() {
    if (!dateAnchorRef) return;
    const rect = dateAnchorRef.getBoundingClientRect();
    datePortalStyle = `position: fixed; top: ${rect.bottom + 4}px; left: ${rect.left}px; z-index: 9999;`;
    showDatePicker = true;
  }

  function closeDatePicker() {
    showDatePicker = false;
  }

  // Close date picker on outside click
  function handleDatePortalOutsideClick(e: MouseEvent) {
    if (dateAnchorRef?.contains(e.target as Node)) return;
    if (datePortalRef?.contains(e.target as Node)) return;
    closeDatePicker();
  }

  $effect(() => {
    if (showDatePicker) {
      // Delay to avoid the same click closing it
      const timer = setTimeout(() => {
        document.addEventListener('mousedown', handleDatePortalOutsideClick);
      }, 0);
      return () => {
        clearTimeout(timer);
        document.removeEventListener('mousedown', handleDatePortalOutsideClick);
      };
    }
  });

  $effect(() => {
    if (expanded) {
      editTitle = data.title;
      editDescription = data.description;
      showDatePicker = false;
      hoveredPriority = null;
    }
  });

  function debounceSaveTitle() {
    if (titleTimer) clearTimeout(titleTimer);
    titleTimer = setTimeout(() => {
      if (editTitle.trim() && editTitle !== data.title) {
        if (data.isProposal && proposal) {
          saveProposalField({ title: editTitle });
        } else if (task) {
          updateTask(task.id, { title: editTitle });
        }
      }
    }, 500);
  }

  function debounceSaveDescription() {
    if (descTimer) clearTimeout(descTimer);
    descTimer = setTimeout(() => {
      if (editDescription !== data.description) {
        if (data.isProposal && proposal) {
          saveProposalField({ description: editDescription });
        } else if (task) {
          updateTask(task.id, { description: editDescription });
        }
      }
    }, 500);
  }

  function handlePriorityClick(p: number) {
    if (data.isProposal && proposal) {
      saveProposalField({ priority: p });
    } else if (task) {
      updateTask(task.id, { priority: p as Task['priority'] });
    }
  }

  function handleDueDateChange(date: string | null) {
    closeDatePicker();
    // Skip no-op updates (e.g. blur firing onchange(null) when already no date)
    if (!date && !data.dueDate) return;
    if (date && data.dueDate && data.dueDate.startsWith(date)) return;
    if (data.isProposal && proposal) {
      saveProposalField({ due_date: date });
    } else if (task) {
      updateTask(task.id, { due_date: date });
    }
  }

  async function saveProposalField(fields: Record<string, unknown>) {
    if (!proposal) return;
    try {
      const updated = await proposalsApi.update(proposal.id, fields);
      onproposalupdate?.(updated);
    } catch {
      addToast('Failed to update proposal', 'error');
    }
  }

  function handleBubbleClick(e: MouseEvent) {
    e.stopPropagation();
    if (compact) {
      onclick?.();
      return;
    }
    if (typeof data.id === 'number') {
      filterStore.markViewed(data.id);
    }
    if (expanded) {
      // Clicking non-interactive area of expanded bubble opens full edit
      onclick?.();
    } else {
      bubbleStore.toggle(data.id);
      if (taskDetailStore.isOpen) {
        onclick?.();
      }
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      handleBubbleClick(e as unknown as MouseEvent);
    }
  }

  function handleDoneToggle(e: MouseEvent) {
    e.stopPropagation();
    if (ontoggle) {
      ontoggle();
    } else if (task) {
      toggleDone(task.id);
    }
  }

  function handleDelete(e: MouseEvent) {
    e.stopPropagation();
    if (task && confirm('Delete this task?')) {
      deleteTask(task.id);
      bubbleStore.collapse();
    }
  }

  function handleEdit(e: MouseEvent) {
    e.stopPropagation();
    onclick?.();
  }

  // Border style
  const borderStyle = $derived.by(() => {
    if (compact) {
      if (showGlow) return '1px solid var(--bg-surface); border-left: 2px solid var(--accent)';
      if (selected) return '1px solid var(--accent)';
      return '1px solid transparent';
    }
    if (expanded) return `1px solid var(--border-strong)`;
    if (showGlow) return `1px solid rgba(232,119,46,0.5)`;
    if (hovering) return `1px solid var(--border-strong)`;
    return `1px solid var(--border-default)`;
  });

  // Compact-mode border-left for AI-tagged
  const compactBorderLeft = $derived(showGlow ? '2px solid var(--accent)' : selected ? '2px solid var(--accent)' : '2px solid transparent');

  // Priority dot color helper — uses hovered level for preview
  function dotColor(dotIndex: number): string {
    const previewLevel = hoveredPriority ?? data.priority;
    const activeColor = priorityDotColor(previewLevel);
    return dotIndex <= previewLevel ? activeColor : 'var(--border-default)';
  }
</script>

{#if compact}
  <!-- COMPACT MODE (list row) -->
  <div
    role="button"
    tabindex="0"
    onmouseenter={() => hovering = true}
    onmouseleave={() => hovering = false}
    onclick={handleBubbleClick}
    onkeydown={handleKeydown}
    data-transition-id="{data.id}"
    data-task-priority="{data.priority}"
    style="view-transition-name: {data.isProposal ? 'proposal' : 'task'}-{data.id}; display: flex; align-items: center; width: 100%; border-radius: 8px; padding: 8px 12px; gap: 10px; background: {selected ? 'var(--accent-subtle)' : hovering ? 'var(--bg-surface-hover)' : 'transparent'}; border-bottom: 1px solid var(--border-subtle); border-left: {compactBorderLeft}; box-shadow: {showGlow ? 'inset 3px 0 8px -4px var(--accent-glow)' : 'none'}; cursor: pointer; transition: width 150ms ease-out, background 150ms ease-out, border-color 150ms ease-out, box-shadow 150ms ease-out, opacity 150ms ease-out; opacity: {presenceOpacity}; min-height: 44px;"
  >
    {#if proposalMode}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div onclick={(e) => { e.stopPropagation(); onselect?.(); }}>
        <Checkbox checked={selected} onchange={() => onselect?.()} />
      </div>
    {:else}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div onclick={(e) => { e.stopPropagation(); ontoggle?.(); }}>
        <Checkbox checked={data.done} onchange={() => ontoggle?.()} />
      </div>
    {/if}
    <div style="padding-top: 1px;">
      <PriorityIndicator level={data.priority} size="sm" />
    </div>
    <span style="flex: 1; font-size: 14.5px; font-weight: {data.priority >= 4 ? 500 : 400}; color: {titleColor}; text-decoration: {data.done ? 'line-through' : 'none'}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;">
      {data.title}
    </span>
    {#if data.labels.length > 0}
      <Badge color={data.labels[0].hex_color}>{data.labels[0].title}</Badge>
    {/if}
    {#if data.dueDate}
      <DateDisplay date={data.dueDate} overdue={isOverdue} />
    {/if}
    {#if project}
      <div style="width: 8px; height: 8px; border-radius: 50%; background: {projectColor}; flex-shrink: 0;"></div>
    {/if}
  </div>

{:else}
  <!-- BUBBLE MODE (card) -->
  <div
    role="button"
    tabindex="0"
    onmouseenter={() => hovering = true}
    onmouseleave={() => hovering = false}
    onclick={handleBubbleClick}
    onkeydown={handleKeydown}
    data-transition-id="{data.id}"
    data-task-priority="{data.priority}"
    style="view-transition-name: {data.isProposal ? 'proposal' : 'task'}-{data.id}; position: relative; width: {expanded ? '360px' : `${bubbleWidth}px`}; min-height: {expanded ? 'auto' : `${bubbleMinHeight}px`}; border-radius: 10px; background: {expanded ? 'var(--bg-elevated)' : 'var(--bg-surface)'}; border: {borderStyle}; padding: {expanded ? '18px 20px' : '14px 16px'}; cursor: pointer; box-shadow: {shadowStyle}{showGlow && !expanded ? ', inset 0 0 12px -4px var(--accent-glow)' : ''}; translate: {hovering && !expanded ? '0 -1px' : 'none'}; transition: background 200ms ease-out, border-color 200ms ease-out, box-shadow 200ms ease-out, opacity 200ms ease-out, padding 200ms ease-out, translate 200ms ease-out; opacity: {presenceOpacity}; display: flex; flex-direction: column; overflow: hidden;"
  >
    <!-- Project corner triangle -->
    {#if projectColor}
      <div style="position: absolute; top: 0; right: 0; width: 0; height: 0; border-left: 18px solid transparent; border-top: 18px solid {projectColor}; border-top-right-radius: 9px; opacity: {expanded ? 0.6 : 0.3}; transition: opacity 200ms; pointer-events: none;"></div>
    {/if}

    {#if proposalMode && !expanded}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div style="position: absolute; top: 12px; left: 12px;" onclick={(e) => { e.stopPropagation(); onselect?.(); }}>
        <Checkbox checked={selected} onchange={() => onselect?.()} />
      </div>
    {/if}

    {#if !expanded}
      <!-- COLLAPSED STATE -->
      <div style="font-size: 14.5px; font-weight: {data.priority >= 4 ? 500 : 400}; color: {titleColor}; text-decoration: {data.done ? 'line-through' : 'none'}; line-height: 1.4; letter-spacing: -0.01em; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; padding-right: {projectColor ? '14px' : '0'}; {proposalMode ? 'margin-left: 28px;' : ''}">
        {data.title}
      </div>
      <div style="flex: 1;"></div>
      <!-- Hover info zone -->
      <div style="min-height: 20px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; {proposalMode ? 'margin-left: 28px;' : ''}">
        {#if hovering}
          {#if data.dueDate}
            <span style="font-size: 12px; color: {isOverdue ? 'var(--overdue)' : 'var(--text-tertiary)'};">{formatDate(data.dueDate)}</span>
          {/if}
          {#if data.labels.length > 0}
            <span style="font-size: 11.5px; color: var(--text-tertiary);">{data.labels[0].title}</span>
          {/if}
          {#if data.attachmentCount > 0}
            <span style="font-size: 11.5px; color: var(--text-tertiary);">&#128206;{data.attachmentCount}</span>
          {/if}
        {/if}
      </div>

    {:else}
      <!-- EXPANDED STATE -->
      <div style="{supportsVT ? '' : 'animation: expandIn 200ms ease-out;'}">
        <!-- Editable title -->
        <textarea
          bind:this={titleTextarea}
          bind:value={editTitle}
          oninput={(e) => { autoResize(e.currentTarget as HTMLTextAreaElement); debounceSaveTitle(); }}
          onclick={(e) => e.stopPropagation()}
          rows="1"
          class="bubble-editable"
          style="width: 100%; padding: 5px 4px; margin-bottom: 4px; font-size: 16px; font-weight: 500; color: var(--text-primary); resize: none; overflow: hidden; white-space: pre-wrap;"
        ></textarea>

        <!-- Editable description -->
        <textarea
          bind:this={descTextarea}
          bind:value={editDescription}
          oninput={(e) => { autoResize(e.currentTarget as HTMLTextAreaElement); debounceSaveDescription(); }}
          onclick={(e) => e.stopPropagation()}
          placeholder="Add description..."
          rows="1"
          class="bubble-editable"
          style="width: 100%; padding: 5px 4px; margin-bottom: 10px; font-size: 13.5px; color: var(--text-secondary); resize: none; overflow: hidden; line-height: 1.55;"
        ></textarea>

        <!-- Metadata row -->
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; align-items: center; padding-left: 4px;">
          <!-- Priority dots — hover previews the level -->
          <div
            style="display: flex; gap: 3px; padding: 4px 2px; border-radius: 6px; margin-right: 0; cursor: pointer;"
            onmouseleave={() => hoveredPriority = null}
          >
            {#each [1, 2, 3, 4, 5] as p (p)}
              <button
                aria-label="Priority {p}"
                onmouseenter={() => hoveredPriority = p}
                onclick={(e) => { e.stopPropagation(); handlePriorityClick(p); hoveredPriority = null; }}
                style="width: 8px; height: 8px; border-radius: 50%; border: none; padding: 0; cursor: pointer; background: {dotColor(p)}; transition: background 100ms;"
              ></button>
            {/each}
          </div>

          <!-- Due date — click to open portal DatePicker -->
          <button
            bind:this={dateAnchorRef}
            class="bubble-editable-zone"
            onclick={(e) => { e.stopPropagation(); showDatePicker ? closeDatePicker() : openDatePicker(); }}
            style="font-size: 12.5px; color: {isOverdue ? 'var(--overdue)' : 'var(--text-tertiary)'}; background: none; border: none; cursor: pointer; padding: 4px 8px; border-radius: 6px; font-family: var(--font-sans); opacity: {data.dueDate ? 1 : 0.5};"
          >{data.dueDate ? formatDate(data.dueDate) : '+ date'}</button>

          <!-- Project name -->
          {#if project || data.projectName}
            <span style="font-size: 12px; color: {projectColor || 'var(--text-tertiary)'}; opacity: 0.7;">
              {project?.title ?? data.projectName}
            </span>
          {/if}

          <!-- Labels -->
          {#each data.labels as label (label.title)}
            <span style="font-size: 11.5px; font-weight: 500; color: var(--text-secondary); background: var(--bg-surface-hover); border-radius: 9999px; padding: 2px 8px;">{label.title}</span>
          {/each}

          <!-- Attachments -->
          {#if data.attachmentCount > 0}
            <span style="font-size: 12px; color: var(--text-tertiary);">
              <svg style="display: inline; vertical-align: -1px;" width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13.5 7.5l-5.4 5.4a3.2 3.2 0 01-4.5-4.5l5.4-5.4a2 2 0 012.8 2.8L6.4 11.2a.8.8 0 01-1.1-1.1l4.5-4.5" stroke-linecap="round" /></svg>
              {data.attachmentCount}
            </span>
          {/if}
        </div>

        <!-- Subtasks (real tasks only) -->
        {#if !data.isProposal && task}
          <div style="margin-bottom: 12px; padding-left: 4px;">
            {#if subtasksLoading}
              <span style="font-size: 12px; color: var(--text-tertiary);">Loading subtasks...</span>
            {:else}
              {#each subtasks as st (st.id)}
                <div
                  class="subtask-row"
                  style="display: flex; align-items: center; gap: 6px; height: 28px; padding: 0 6px; border-radius: 6px; background: var(--bg-surface); margin-bottom: 2px;"
                >
                  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
                  <div onclick={(e) => e.stopPropagation()}>
                    <Checkbox checked={st.done} size={16} onchange={() => toggleSubtask(st)} />
                  </div>
                  <span style="flex: 1; font-size: 12.5px; color: {st.done ? 'var(--text-tertiary)' : 'var(--text-secondary)'}; text-decoration: {st.done ? 'line-through' : 'none'}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{st.title}</span>
                  <button
                    class="subtask-delete"
                    onclick={(e) => { e.stopPropagation(); deleteSubtask(st); }}
                    aria-label="Delete subtask"
                    style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 14px; padding: 0 2px; line-height: 1; opacity: 0; transition: opacity 150ms;"
                  >&times;</button>
                </div>
              {/each}
              <!-- Add subtask input -->
              <div style="display: flex; align-items: center; gap: 6px; height: 28px; padding: 0 6px;">
                <span style="font-size: 14px; color: var(--text-tertiary); width: 16px; text-align: center;">+</span>
                <input
                  type="text"
                  bind:value={newSubtaskTitle}
                  placeholder="Add subtask..."
                  disabled={addingSubtask}
                  onclick={(e) => e.stopPropagation()}
                  onkeydown={(e) => { e.stopPropagation(); if (e.key === 'Enter') handleAddSubtask(); }}
                  style="flex: 1; background: transparent; border: none; outline: none; font-size: 12.5px; color: var(--text-secondary); font-family: var(--font-sans); padding: 0;"
                />
              </div>
            {/if}
          </div>
        {/if}

        {#if data.isProposal && data.estimatedMinutes}
          <div style="font-size: 13px; color: var(--text-tertiary); margin-bottom: 12px; padding-left: 4px;">
            {data.estimatedMinutes} min estimated
          </div>
        {/if}

        <!-- Action row -->
        <div style="display: flex; gap: 6px; align-items: center; padding-left: 0;">
          {#if data.isProposal}
            <button class="bubble-action-btn" style="--hover-color: var(--done);" onclick={(e) => { e.stopPropagation(); onapprove?.(); bubbleStore.collapse(); }}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6.5" /><path d="M5.5 8l2 2 3.5-3.5" /></svg>
              Approve
            </button>
            <button class="bubble-action-btn" style="--hover-color: var(--overdue);" onclick={(e) => { e.stopPropagation(); onreject?.(); bubbleStore.collapse(); }}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6.5" /><path d="M5.5 5.5l5 5M10.5 5.5l-5 5" /></svg>
              Reject
            </button>
          {:else}
            <button class="bubble-action-btn" style="--hover-color: var(--done);" onclick={(e) => handleDoneToggle(e)}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6.5" /><path d="M5.5 8l2 2 3.5-3.5" /></svg>
              {data.done ? 'Undo' : 'Done'}
            </button>
            <button class="bubble-action-btn" style="--hover-color: var(--overdue);" onclick={(e) => handleDelete(e)}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4.5h10M6 4.5V3a1 1 0 011-1h2a1 1 0 011 1v1.5M12 4.5l-.5 8a1.5 1.5 0 01-1.5 1.5H6a1.5 1.5 0 01-1.5-1.5L4 4.5" /></svg>
              Delete
            </button>
          {/if}
          <button class="bubble-action-btn bubble-open-btn" style="margin-left: auto; --hover-color: var(--accent);" onclick={(e) => handleEdit(e)}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="12" height="12" rx="2" /><path d="M6 8h4M8 6v4" /></svg>
            Open
          </button>
        </div>
      </div>
    {/if}
  </div>
{/if}

<!-- Date picker portal — renders at document level so it's never clipped -->
{#if showDatePicker}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div bind:this={datePortalRef} style={datePortalStyle} onclick={(e) => e.stopPropagation()}>
    <DatePicker value={data.dueDate ? data.dueDate.split('T')[0] : ''} onchange={handleDueDateChange} initialOpen={true} />
  </div>
{/if}

<script module lang="ts">
  const priorityColors = ['', 'var(--priority-low)', 'var(--priority-low)', 'var(--priority-medium)', 'var(--priority-high)', 'var(--priority-urgent)'];

  function priorityDotColor(level: number): string {
    return priorityColors[level] ?? priorityColors[0];
  }

  function formatDate(dateStr: string): string {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = d.getTime() - now.getTime();
    const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Tomorrow';
    if (diffDays === -1) return 'Yesterday';
    if (diffDays < -1) return `${Math.abs(diffDays)}d overdue`;
    if (diffDays <= 7) return `In ${diffDays}d`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }
</script>

<style>
  /* Editable text fields (title, description) */
  .bubble-editable {
    background: transparent;
    border: 1px solid transparent;
    border-bottom: 1px solid transparent;
    border-radius: 6px;
    font-family: var(--font-sans);
    outline: none;
    transition: border-color 150ms, background-color 150ms;
  }
  .bubble-editable::placeholder {
    color: var(--text-tertiary);
    opacity: 0.7;
    font-style: italic;
  }
  .bubble-editable:hover {
    border-color: var(--border-default);
    background-color: rgba(0, 0, 0, 0.15);
  }
  .bubble-editable:focus {
    border-color: var(--border-strong);
    background-color: rgba(0, 0, 0, 0.2);
  }

  /* Editable inline zones (date label) */
  .bubble-editable-zone {
    transition: background-color 150ms;
  }
  .bubble-editable-zone:hover {
    background-color: rgba(0, 0, 0, 0.15) !important;
  }

  .bubble-action-btn {
    font-size: 12px;
    font-family: var(--font-sans);
    font-weight: 500;
    color: var(--text-tertiary);
    background: none;
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: color 150ms, background-color 150ms;
  }
  .bubble-action-btn:hover {
    color: var(--hover-color, var(--text-secondary));
    background-color: rgba(0, 0, 0, 0.12);
  }

  /* Open button — accent tint by default, stronger on card hover */
  .bubble-open-btn {
    color: color-mix(in srgb, var(--accent) 65%, var(--text-tertiary));
  }
  :global([role="button"]:hover) .bubble-open-btn {
    background-color: rgba(232, 119, 46, 0.1);
    color: var(--accent);
  }

  .subtask-row:hover .subtask-delete {
    opacity: 1 !important;
  }

  @keyframes expandIn {
    from { opacity: 0; transform: translateY(-4px); }
    to { opacity: 1; transform: translateY(0); }
  }
</style>
