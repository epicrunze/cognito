<script lang="ts">
  import type { Task, TaskProposal, Subtask } from '$lib/types';
  import { projectsStore } from '$lib/stores.svelte';
  import { updateTask, toggleDone, deleteTask } from '$lib/stores/taskMutations';
  import { filterStore } from '$lib/stores/filter.svelte';
  import { bubbleStore } from '$lib/stores/bubble.svelte';
  import { taskDetailStore } from '$lib/stores/taskDetail.svelte';
  import { proposalsApi, subtasksApi } from '$lib/api';
  import { addToast } from '$lib/stores/toast.svelte';
  import { showConfirmDialog } from '$lib/stores/confirmDialog.svelte';
  import { tick } from 'svelte';
  import PriorityIndicator from '$components/ui/PriorityIndicator.svelte';
  import PriorityMeter from '$components/ui/PriorityMeter.svelte';
  import Badge from '$components/ui/Badge.svelte';
  import DateDisplay from '$components/ui/DateDisplay.svelte';
  import DatePicker from '$components/ui/DatePicker.svelte';
  import ScheduleDisplay from '$components/ui/ScheduleDisplay.svelte';
  import Checkbox from '$components/ui/Checkbox.svelte';
  import { registerCelebrationElement, unregisterCelebrationElement } from '$lib/celebrate';
  import { hexToRgb } from '$lib/formatUtils';
  import { isOverdue as checkOverdue, formatRelativeDate } from '$lib/dateUtils';
  import { responsiveStore } from '$lib/stores/responsive.svelte';


  let {
    task,
    proposal,
    compact = false,
    kanbanCompact = false,
    kanban = false,
    proposalMode = false,
    selected = false,
    showPip = false,
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
    kanbanCompact?: boolean;
    kanban?: boolean;
    proposalMode?: boolean;
    selected?: boolean;
    showPip?: boolean;
    onselect?: () => void;
    onapprove?: () => void;
    onreject?: () => void;
    onproposalupdate?: (p: TaskProposal) => void;
    ontoggle?: () => void;
    onclick?: () => void;
  } = $props();

  let hovering = $state(false);
  let celebrating = $state(false);
  let miniCheckRef = $state<HTMLButtonElement | undefined>(undefined);
  let doneButtonRef = $state<HTMLButtonElement | undefined>(undefined);
  let compactCheckboxEl = $state<HTMLDivElement | undefined>(undefined);

  // Register celebration elements
  $effect(() => {
    if (data.isProposal || typeof data.id !== 'number') return;
    const taskId = data.id;
    // Pick the best element to register based on mode
    const el = miniCheckRef ?? doneButtonRef ?? compactCheckboxEl;
    if (el) {
      registerCelebrationElement(taskId, el);
      return () => unregisterCelebrationElement(taskId);
    }
  });

  // --- Unified BubbleData ---
  interface BubbleData {
    id: number | string;
    title: string;
    description: string;
    priority: number;
    dueDate: string | null;
    startDate: string | null;
    endDate: string | null;
    projectId: number | null;
    projectName: string | null;
    labels: { id?: number; title: string; hex_color?: string }[];
    done: boolean;
    attachmentCount: number;
    subtaskDone: number;
    subtaskTotal: number;
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
        startDate: null,
        endDate: null,
        projectId: proposal.project_id,
        projectName: proposal.project_name,
        labels: proposal.labels.map(l => ({ title: l })),
        done: false,
        attachmentCount: 0,
        subtaskDone: 0,
        subtaskTotal: 0,
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
        startDate: task.start_date && !task.start_date.startsWith('0001-01-01') ? task.start_date : null,
        endDate: task.end_date && !task.end_date.startsWith('0001-01-01') ? task.end_date : null,
        projectId: task.project_id,
        projectName: null,
        labels: task.labels,
        done: task.done,
        attachmentCount: task.attachments?.length ?? 0,
        subtaskDone: task.subtask_done ?? 0,
        subtaskTotal: task.subtask_total ?? 0,
        estimatedMinutes: null,
        isProposal: false,
        status: null,
      };
    }
    return { id: 0, title: '', description: '', priority: 3, dueDate: null, startDate: null, endDate: null, projectId: null, projectName: null, labels: [], done: false, attachmentCount: 0, subtaskDone: 0, subtaskTotal: 0, estimatedMinutes: null, isProposal: false, status: null };
  });

  const project = $derived(data.projectId ? projectsStore.projects.find(p => p.id === data.projectId) : null);
  const projectColor = $derived(project?.hex_color || '');
  const isOverdue = $derived(Boolean(!data.done && checkOverdue(data.dueDate)));
  const isAiTagged = $derived(data.isProposal || (typeof data.id === 'number' && filterStore.aiTaggedIds.has(data.id)));
  const viewed = $derived(typeof data.id === 'number' && filterStore.viewedTaskIds.has(data.id));
  const showGlow = $derived(isAiTagged && (!viewed || data.isProposal));

  const isScheduled = $derived(Boolean(data.startDate && data.endDate));
  const isScheduledToday = $derived.by(() => {
    if (!data.startDate) return false;
    const start = new Date(data.startDate);
    const now = new Date();
    return start.getFullYear() === now.getFullYear() && start.getMonth() === now.getMonth() && start.getDate() === now.getDate();
  });
  const expanded = $derived(bubbleStore.expandedTaskId === data.id);
  const supportsVT = $derived(typeof document !== 'undefined' && !!document.startViewTransition);

  // Whether the leading project pip shows in the data line (cross-project stream)
  const pipColor = $derived(showPip && projectColor ? projectColor : '');

  // Swipe-to-complete (mobile only)
  let swipeX = $state(0);
  let swiping = $state(false);
  let swipeStartX = 0;
  let swipeStartY = 0;
  let swipeLocked = false;
  const SWIPE_THRESHOLD = 96;
  const swipePast = $derived(swipeX >= SWIPE_THRESHOLD);

  function handleSwipeStart(e: TouchEvent) {
    if (!responsiveStore.isMobile || data.done || data.isProposal || expanded) return;
    const touch = e.touches[0];
    swipeStartX = touch.clientX;
    swipeStartY = touch.clientY;
    swiping = false;
    swipeLocked = false;
    swipeX = 0;
  }

  function handleSwipeMove(e: TouchEvent) {
    if (!responsiveStore.isMobile || data.done || data.isProposal || expanded) return;
    const touch = e.touches[0];
    const dx = touch.clientX - swipeStartX;
    const dy = touch.clientY - swipeStartY;

    // Lock direction after 10px movement
    if (!swipeLocked && (Math.abs(dx) > 10 || Math.abs(dy) > 10)) {
      swipeLocked = true;
      swiping = Math.abs(dx) > Math.abs(dy); // horizontal wins
    }

    if (swiping) {
      e.preventDefault();
      swipeX = Math.max(0, Math.min(140, dx)); // only swipe right
    }
  }

  function handleSwipeEnd() {
    if (!swiping) { swipeX = 0; return; }
    if (swipeX >= SWIPE_THRESHOLD && typeof data.id === 'number') {
      // Complete the task
      if (typeof navigator?.vibrate === 'function') navigator.vibrate(15);
      if (!data.done) {
        celebrating = true;
        setTimeout(() => celebrating = false, 750);
      }
      toggleDone(data.id);
    }
    swipeX = 0;
    swiping = false;
  }

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

  // --- Priority as presence (one vocabulary: position/weight/brightness/opacity/shadow) ---
  type Tier = 'urgent' | 'high' | 'medium' | 'low' | 'none';
  const tier = $derived.by((): Tier => {
    const p = data.priority;
    if (p >= 5) return 'urgent';
    if (p === 4) return 'high';
    if (p === 3) return 'medium';
    if (p >= 1) return 'low';
    return 'none';
  });
  const tierColor: Record<Tier, string> = {
    urgent: 'var(--urgent)', high: 'var(--high)', medium: 'var(--medium)', low: 'var(--low)', none: 'transparent',
  };
  const presence = $derived.by(() => {
    switch (tier) {
      case 'urgent': return { ink: 'var(--text-primary)', op: 1, weight: 600, fs: '16px' };
      case 'high': return { ink: 'var(--text-primary)', op: 1, weight: 500, fs: '15px' };
      case 'medium': return { ink: 'var(--text-primary)', op: 1, weight: 400, fs: '15px' };
      case 'low': return { ink: 'var(--text-secondary)', op: 0.8, weight: 400, fs: '15px' };
      default: return { ink: 'var(--text-secondary)', op: 0.92, weight: 400, fs: '15px' };
    }
  });

  // Whisper rail — 45% at rest, full color on hover; overdue forces red; hidden when done/none.
  const railBase = $derived(isOverdue && !data.done ? 'var(--urgent)' : tierColor[tier]);
  const hasRail = $derived(railBase !== 'transparent' && !data.done);
  const railColor = $derived(
    hovering
      ? (isOverdue && !data.done ? 'var(--overdue-hint)' : railBase)
      : `color-mix(in srgb, ${railBase} 45%, transparent)`
  );

  const presenceOpacity = $derived(data.done ? 0.55 : presence.op);
  const titleColor = $derived(data.done ? 'var(--text-tertiary)' : presence.ink);

  const shadowStyle = $derived.by(() => {
    if (compact || data.done) return 'none';
    if (expanded) return 'var(--shadow-md)';
    if (hovering) return 'var(--shadow-lift)';
    return 'var(--shadow-rest)';
  });

  const bubbleBorder = $derived.by(() => {
    if (showGlow) return 'var(--ai)';
    if (expanded) return 'var(--border-strong)';
    return 'transparent';
  });

  // Card padding — reserve the left rail gutter without changing geometry on hover.
  const cardPadding = $derived(
    expanded
      ? '18px 20px'
      : kanbanCompact
        ? (hasRail ? '8px 10px 8px 13px' : '8px 10px')
        : (hasRail ? '13px 14px 12px 17px' : '13px 14px 12px')
  );

  // Collapsed check shows on hover (or stays once done); real tasks only.
  const showCollapsedCheck = $derived(!data.isProposal && !proposalMode && (hovering || data.done));
  const canCollapsedCheck = $derived(!data.isProposal && !proposalMode);

  // --- Expanded state editing ---
  let editTitle = $state('');
  let editDescription = $state('');
  let titleFocused = $state(false);
  let descFocused = $state(false);
  let titleTimer: ReturnType<typeof setTimeout> | null = null;
  let descTimer: ReturnType<typeof setTimeout> | null = null;

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
      if (!titleFocused) editTitle = data.title;
      if (!descFocused) editDescription = data.description;
      showDatePicker = false;
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
    } catch (e) {
      addToast(e instanceof Error ? e.message : 'Failed to update proposal', 'error');
    }
  }

  function handleBubbleClick(e: MouseEvent) {
    e.stopPropagation();
    if (compact || kanban || responsiveStore.isMobile) {
      if (typeof data.id === 'number') {
        filterStore.markViewed(data.id);
      }
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
    // Flash celebrating class when completing
    if (!data.done) {
      celebrating = true;
      setTimeout(() => celebrating = false, 750);
    }
    if (ontoggle) {
      ontoggle();
    } else if (task) {
      toggleDone(task.id);
    }
  }

  async function handleDelete(e: MouseEvent) {
    e.stopPropagation();
    if (task) {
      const confirmed = await showConfirmDialog({
        title: 'Delete task',
        message: 'Delete this task? This cannot be undone.',
        confirmLabel: 'Delete',
        destructive: true,
      });
      if (confirmed) {
        deleteTask(task.id);
        bubbleStore.collapse();
        taskDetailStore.close();
      }
    }
  }

  function handleEdit(e: MouseEvent) {
    e.stopPropagation();
    onclick?.();
  }

  function formatDate(dateStr: string): string {
    return formatRelativeDate(dateStr);
  }
</script>

{#if compact}
  <!-- COMPACT MODE (list row) -->
  <div
    role="button"
    tabindex="0"
    class:task-celebrating={celebrating}
    onmouseenter={() => hovering = true}
    onmouseleave={() => hovering = false}
    onclick={handleBubbleClick}
    onkeydown={handleKeydown}
    data-transition-id="{data.id}"
    data-task-priority="{data.priority}"
    style="view-transition-name: {data.isProposal ? 'proposal' : 'task'}-{data.id}; display: flex; align-items: center; width: 100%; border-radius: 8px; padding: 8px 12px; gap: 10px; background: {hovering ? 'var(--surface-card-hover)' : 'transparent'}; border-bottom: 1px solid var(--border-subtle); border-left: {showGlow ? '2px solid var(--ai)' : '2px solid transparent'}; box-shadow: {showGlow ? 'inset 3px 0 8px -4px var(--ai-glow)' : 'none'}; cursor: pointer; transition: background var(--t-fast) var(--ease-out), border-bottom-color var(--t-fast) var(--ease-out), box-shadow var(--t-fast) var(--ease-out), opacity var(--t-fast) var(--ease-out); opacity: {presenceOpacity}; min-height: 44px;"
  >
    {#if proposalMode}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div onclick={(e) => { e.stopPropagation(); onselect?.(); }}>
        <Checkbox checked={selected} onchange={() => onselect?.()} />
      </div>
    {:else}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div bind:this={compactCheckboxEl} onclick={(e) => { e.stopPropagation(); ontoggle?.(); }}>
        <Checkbox checked={data.done} onchange={() => ontoggle?.()} />
      </div>
    {/if}
    <div style="padding-top: 1px;">
      <PriorityIndicator level={data.priority} size="sm" />
    </div>
    <span style="flex: 1; font-size: 14.5px; font-weight: {presence.weight}; color: {titleColor}; text-decoration: {data.done ? 'line-through' : 'none'}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;">
      {data.title}
    </span>
    {#if data.labels.length > 0}
      <Badge color={data.labels[0].hex_color}>{data.labels[0].title}</Badge>
    {/if}
    {#if data.dueDate}
      <DateDisplay date={data.dueDate} overdue={isOverdue} />
    {/if}
    {#if isScheduled}
      <ScheduleDisplay startDate={data.startDate} endDate={data.endDate} done={data.done} />
    {/if}
    {#if project}
      <div style="width: 8px; height: 8px; border-radius: 50%; background: {projectColor}; flex-shrink: 0;"></div>
    {/if}
  </div>

{:else}
  <!-- BUBBLE MODE (card) -->
  <div class="swipe-wrapper" style="position: relative; {responsiveStore.isMobile && !data.done && !data.isProposal ? 'overflow: hidden; border-radius: var(--radius-card);' : ''}">
    {#if swipeX > 0}
      <div class="swipe-reveal" style="background: color-mix(in srgb, var(--done) {swipePast ? 16 : 10}%, transparent);">
        <span class="swipe-check" class:past={swipePast}>
          {#if swipePast}
            <svg width="12" height="12" viewBox="0 0 11 11" fill="none">
              <path d="M2.5 6L4.5 8L8.5 3.5" stroke="var(--bg-base)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          {/if}
        </span>
      </div>
    {/if}
  <div
    role="button"
    tabindex="0"
    class:task-celebrating={celebrating}
    onmouseenter={() => hovering = true}
    onmouseleave={() => hovering = false}
    onclick={handleBubbleClick}
    onkeydown={handleKeydown}
    ontouchstart={handleSwipeStart}
    ontouchmove={handleSwipeMove}
    ontouchend={handleSwipeEnd}
    data-transition-id="{data.id}"
    data-task-priority="{data.priority}"
    style="view-transition-name: {data.isProposal ? 'proposal' : 'task'}-{data.id}; position: relative; width: {expanded ? 'min(360px, 100%)' : (kanban || responsiveStore.isMobile) ? '100%' : '232px'}; min-height: {expanded ? 'auto' : kanbanCompact ? '50px' : 'auto'}; border-radius: var(--radius-card); background: {expanded ? 'var(--bg-elevated)' : (hovering && !data.done ? 'var(--surface-card-hover)' : 'var(--surface-card)')}; border: 1px solid {bubbleBorder}; padding: {cardPadding}; cursor: pointer; box-shadow: {showGlow && !expanded ? '0 0 10px var(--ai-glow), ' + shadowStyle : shadowStyle}; transition: background var(--t-fast) var(--ease-out), border-color var(--t-fast) var(--ease-out), box-shadow var(--t-fast) var(--ease-out), opacity var(--t-fast) var(--ease-out){swiping ? '' : ', transform var(--t-normal) var(--ease-out)'}; opacity: {presenceOpacity}; display: flex; flex-direction: column; overflow: hidden; transform: {swipeX > 0 ? `translateX(${swipeX}px)` : (hovering && !expanded && !swiping ? 'translateY(-2px)' : 'none')};"
  >
    <!-- Whisper rail (priority as presence — 45% at rest, full on hover) -->
    {#if hasRail && !expanded}
      <span class="priority-rail" style="background: {railColor};"></span>
    {/if}

    {#if proposalMode && !expanded}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div style="position: absolute; top: 12px; left: 12px;" onclick={(e) => { e.stopPropagation(); onselect?.(); }}>
        <Checkbox checked={selected} onchange={() => onselect?.()} />
      </div>
    {/if}

    {#if !expanded}
      <!-- COLLAPSED STATE — quiet anatomy -->
      <span
        class="bubble-title"
        style="font-size: {kanbanCompact ? '13px' : presence.fs}; font-weight: {presence.weight}; color: {titleColor}; text-decoration: {data.done ? 'line-through' : 'none'}; -webkit-line-clamp: {kanbanCompact ? 2 : 3}; {proposalMode ? 'margin-left: 28px;' : ''}"
      >
        {data.title}
      </span>

      <!-- One mono data line. No checkbox at rest; hover slides the check in. -->
      {#if !kanbanCompact}
        <div class="data-line" style="{proposalMode ? 'margin-left: 28px;' : ''}">
          {#if canCollapsedCheck}
            <button
              bind:this={miniCheckRef}
              class="mini-check-slot"
              class:show={showCollapsedCheck}
              onclick={handleDoneToggle}
              aria-label={data.done ? 'Mark not done' : 'Complete task'}
            >
              <span class="mini-check" class:checked={data.done}>
                {#if data.done}
                  <svg width="8" height="8" viewBox="0 0 11 11" fill="none">
                    <path d="M2.5 6L4.5 8L8.5 3.5" stroke="var(--bg-base)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                {/if}
              </span>
            </button>
          {/if}
          <span class="data-parts">
            {#if pipColor}
              <span class="dp"><span class="pip" style="background: {pipColor};"></span></span>
            {/if}
            {#if data.dueDate}
              <span class="dp" style="color: {isOverdue ? 'var(--overdue)' : 'inherit'};">{formatDate(data.dueDate)}</span>
            {/if}
            {#if data.subtaskTotal > 0}
              <span class="dp">{data.subtaskDone}/{data.subtaskTotal}</span>
            {/if}
            {#if data.attachmentCount > 0}
              <span class="dp attach">
                <svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13.5 7.5l-5.4 5.4a3.2 3.2 0 01-4.5-4.5l5.4-5.4a2 2 0 012.8 2.8L6.4 11.2a.8.8 0 01-1.1-1.1l4.5-4.5" stroke-linecap="round" /></svg>
                {data.attachmentCount}
              </span>
            {/if}
            {#if isScheduledToday && !data.done}
              <span class="dp"><span class="today-dot"></span></span>
            {/if}
            {#if isAiTagged}
              <span class="dp ai-tag">
                <svg width="8" height="8" viewBox="0 0 10 10"><rect x="2.2" y="2.2" width="5.6" height="5.6" fill="none" stroke="currentColor" stroke-width="1.2" transform="rotate(45 5 5)"></rect></svg>
                cognito
              </span>
            {/if}
          </span>
        </div>
      {/if}

    {:else}
      <!-- EXPANDED STATE -->
      <div style="{supportsVT ? '' : 'animation: expandIn var(--transition-normal) ease-out;'}">
        <!-- Editable title -->
        <textarea
          bind:this={titleTextarea}
          bind:value={editTitle}
          oninput={(e) => { autoResize(e.currentTarget as HTMLTextAreaElement); debounceSaveTitle(); }}
          onfocus={() => titleFocused = true}
          onblur={() => titleFocused = false}
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
          onfocus={() => descFocused = true}
          onblur={() => descFocused = false}
          onclick={(e) => e.stopPropagation()}
          placeholder="Add description..."
          rows="1"
          class="bubble-editable"
          style="width: 100%; padding: 5px 4px; margin-bottom: 10px; font-size: 13.5px; color: var(--text-secondary); resize: none; overflow-y: auto; max-height: 200px; line-height: 1.55;"
        ></textarea>

        <!-- Metadata row -->
        <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px; align-items: center; padding-left: 4px;">
          <!-- Priority — editable meter -->
          <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
          <div onclick={(e) => e.stopPropagation()}>
            <PriorityMeter value={data.priority} showLabel={false} segWidth={18} onchange={(p) => handlePriorityClick(p)} />
          </div>

          <!-- Due date — click to open portal DatePicker -->
          <button
            bind:this={dateAnchorRef}
            class="bubble-editable-zone"
            onclick={(e) => { e.stopPropagation(); showDatePicker ? closeDatePicker() : openDatePicker(); }}
            style="font-size: 12.5px; color: {isOverdue ? 'var(--overdue)' : 'var(--text-tertiary)'}; background: none; border: none; cursor: pointer; padding: 4px 8px; border-radius: 6px; font-family: var(--font-sans); opacity: {data.dueDate ? 1 : 0.5};"
          >{data.dueDate ? formatDate(data.dueDate) : '+ date'}</button>

          {#if isScheduled}
            <ScheduleDisplay startDate={data.startDate} endDate={data.endDate} done={data.done} />
          {/if}

          <!-- Project name -->
          {#if project || data.projectName}
            <span style="font-size: 12px; color: {projectColor || 'var(--text-tertiary)'}; opacity: 0.7;">
              {project?.title ?? data.projectName}
            </span>
          {/if}

          <!-- Labels -->
          {#each data.labels as label (label.title)}
            <span style="font-size: 10px; font-weight: 500; color: #{label.hex_color || 'A1A09A'}; background: rgba({hexToRgb(label.hex_color || 'A1A09A')}, 0.15); border-radius: 4px; padding: 2px 7px; font-family: var(--font-mono);">{label.title}</span>
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
                    style="background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 14px; padding: 0 2px; line-height: 1; opacity: 0; transition: opacity var(--transition-fast);"
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
            <button class="bubble-action-btn" style="--hover-color: var(--done); --hover-bg: rgba(91,188,110,0.08);" onclick={(e) => { e.stopPropagation(); onapprove?.(); bubbleStore.collapse(); }}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6.5" /><path d="M5.5 8l2 2 3.5-3.5" /></svg>
              Approve
            </button>
            <button class="bubble-action-btn" style="--hover-color: var(--overdue); --hover-bg: rgba(239,87,68,0.08);" onclick={(e) => { e.stopPropagation(); onreject?.(); bubbleStore.collapse(); }}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6.5" /><path d="M5.5 5.5l5 5M10.5 5.5l-5 5" /></svg>
              Reject
            </button>
          {:else}
            <button bind:this={doneButtonRef} class="bubble-action-btn" style="--hover-color: var(--done); --hover-bg: rgba(91,188,110,0.08);" onclick={(e) => handleDoneToggle(e)}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6.5" /><path d="M5.5 8l2 2 3.5-3.5" /></svg>
              {data.done ? 'Undo' : 'Done'}
            </button>
            <button class="bubble-action-btn" style="--hover-color: var(--overdue); --hover-bg: rgba(239,87,68,0.08);" onclick={(e) => handleDelete(e)}>
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4.5h10M6 4.5V3a1 1 0 011-1h2a1 1 0 011 1v1.5M12 4.5l-.5 8a1.5 1.5 0 01-1.5 1.5H6a1.5 1.5 0 01-1.5-1.5L4 4.5" /></svg>
              Delete
            </button>
          {/if}
          <button class="bubble-action-btn bubble-open-btn" style="margin-left: auto; --hover-color: var(--accent); --hover-bg: rgba(232,119,46,0.1);" onclick={(e) => handleEdit(e)}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="12" height="12" rx="2" /><path d="M6 8h4M8 6v4" /></svg>
            Open
          </button>
        </div>
      </div>
    {/if}
  </div>
  </div>
{/if}

<!-- Date picker portal — renders at document level so it's never clipped -->
{#if showDatePicker}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div bind:this={datePortalRef} style={datePortalStyle} onclick={(e) => e.stopPropagation()}>
    <DatePicker value={data.dueDate ? data.dueDate.split('T')[0] : ''} onchange={handleDueDateChange} initialOpen={true} />
  </div>
{/if}

<style>
  /* Collapsed title — owns the full first line */
  .bubble-title {
    font-family: var(--font-sans);
    line-height: 1.3;
    letter-spacing: -0.01em;
    text-decoration-color: var(--text-tertiary);
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-wrap: pretty;
  }

  /* Whisper rail */
  .priority-rail {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    border-top-left-radius: var(--radius-card);
    border-bottom-left-radius: var(--radius-card);
    transition: background var(--t-fast) var(--ease-out);
    pointer-events: none;
  }

  /* One mono data line — reserved height so hover never resizes the card */
  .data-line {
    display: flex;
    align-items: center;
    min-height: 14px;
    margin-top: 9px;
  }

  .mini-check-slot {
    display: inline-flex;
    align-items: center;
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    overflow: hidden;
    width: 0;
    margin-right: 0;
    opacity: 0;
    transition: width var(--t-fast) var(--ease-out), margin-right var(--t-fast) var(--ease-out), opacity var(--t-fast) var(--ease-out);
  }
  .mini-check-slot.show {
    width: 14px;
    margin-right: 8px;
    opacity: 1;
  }
  .mini-check {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    flex-shrink: 0;
    box-sizing: border-box;
    border: 1.5px solid var(--border-strong);
    background: transparent;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition-property: background-color, border-color, color, box-shadow, transform, opacity; transition-duration: var(--t-normal); transition-timing-function: var(--ease-out);
  }
  .mini-check.checked {
    border: none;
    background: var(--done);
  }
  /* Hovering the bubble cues completability — the unchecked box goes green. */
  :global([role="button"]:hover) .mini-check:not(.checked) {
    border-color: var(--done);
  }
  /* Hovering the check itself fills it, for a clear click target. */
  .mini-check-slot:hover .mini-check:not(.checked) {
    background: var(--done);
    border-color: var(--done);
  }

  .data-parts {
    display: inline-flex;
    align-items: center;
    font: var(--type-data);
    color: var(--text-tertiary);
    letter-spacing: var(--tracking-mono);
    white-space: nowrap;
    min-width: 0;
  }
  .dp {
    display: inline-flex;
    align-items: center;
  }
  .dp + .dp::before {
    content: '·';
    opacity: 0.5;
    padding: 0 5px;
  }
  .dp.attach {
    gap: 2px;
  }
  .ai-tag {
    color: var(--ai);
    gap: 4px;
  }
  .pip {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
  }
  .today-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--accent);
    opacity: 0.5;
    display: inline-block;
  }

  /* Editable text fields (title, description) */
  .bubble-editable {
    background: transparent;
    border: 1px solid transparent;
    border-bottom: 1px solid transparent;
    border-radius: 6px;
    font-family: var(--font-sans);
    outline: none;
    transition: border-color var(--transition-fast), background-color var(--transition-fast);
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
    transition: background-color var(--transition-fast);
  }
  .bubble-editable-zone:hover {
    background-color: rgba(0, 0, 0, 0.15) !important;
  }

  .bubble-action-btn {
    font-size: 12px;
    font-family: var(--font-sans);
    font-weight: 400;
    color: var(--text-tertiary);
    background: none;
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: color var(--transition-fast), background-color var(--transition-fast);
  }
  .bubble-action-btn:hover {
    color: var(--hover-color, var(--text-secondary));
    background-color: var(--hover-bg, var(--bg-surface));
  }

  /* Open button — accent by default */
  .bubble-open-btn {
    color: var(--accent);
  }

  .subtask-row:hover .subtask-delete {
    opacity: 1 !important;
  }

  /* Swipe-to-complete (mobile) — green gutter with a check that fills past threshold */
  .swipe-reveal {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    padding-left: 18px;
    border-radius: var(--radius-card);
  }
  .swipe-check {
    width: 22px;
    height: 22px;
    border-radius: 6px;
    box-sizing: border-box;
    border: 1.5px solid var(--done);
    background: transparent;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition-property: background-color, border-color, color, box-shadow, transform, opacity; transition-duration: var(--t-fast); transition-timing-function: var(--ease-out);
  }
  .swipe-check.past {
    border: none;
    background: var(--done);
    transform: scale(1.1);
  }
</style>
