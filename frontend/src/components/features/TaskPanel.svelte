<script lang="ts">
  import { untrack } from 'svelte';
  import type { Task, TaskProposal, Label, TaskAttachment, Subtask } from '$lib/types';
  import { tasksStore, projectsStore, labelsStore } from '$lib/stores.svelte';
  import { updateTask, toggleDone, deleteTask } from '$lib/stores/taskMutations';
  import { addToast } from '$lib/stores/toast.svelte';
  import { tasksApi, proposalsApi, attachmentsApi, subtasksApi } from '$lib/api';
  import SlideOver from '$components/ui/SlideOver.svelte';
  import Input from '$components/ui/Input.svelte';
  import Textarea from '$components/ui/Textarea.svelte';
  import Button from '$components/ui/Button.svelte';
  import Dropdown from '$components/ui/Dropdown.svelte';
  import Kbd from '$components/ui/Kbd.svelte';
  import DatePicker from '$components/ui/DatePicker.svelte';
  import Checkbox from '$components/ui/Checkbox.svelte';

  let {
    mode = 'create' as 'create' | 'edit' | 'proposal',
    open = false,
    onclose,
    defaultProjectId,
    task,
    proposal,
    onupdate,
  }: {
    mode?: 'create' | 'edit' | 'proposal';
    open: boolean;
    onclose?: () => void;
    defaultProjectId?: number;
    task?: Task;
    proposal?: TaskProposal;
    onupdate?: (p: TaskProposal) => void;
  } = $props();

  let title = $state('');
  let description = $state('');
  let priority = $state(3);
  let dueDate = $state('');
  let estimatedMinutes = $state('');
  let projectValue = $state('');
  let creating = $state(false);
  let deleting = $state(false);
  let titleRef = $state<HTMLInputElement | undefined>(undefined);

  // Label management
  let currentLabels = $state<Label[]>([]);
  let proposalLabelNames = $state<string[]>([]);
  let showLabelPicker = $state(false);

  // Attachments
  let attachments = $state<TaskAttachment[]>([]);
  let attachmentsLoading = $state(false);
  let uploading = $state(false);
  let dragOver = $state(false);
  let fileInputRef = $state<HTMLInputElement | undefined>(undefined);

  // Subtasks
  let subtasks = $state<Subtask[]>([]);
  let subtasksLoading = $state(false);
  let newSubtaskTitle = $state('');
  let addingSubtask = $state(false);

  // New project inline create
  let creatingProject = $state(false);
  let newProjectName = $state('');
  let newProjectLoading = $state(false);

  // New label inline create
  let creatingLabel = $state(false);
  let newLabelTitle = $state('');
  let newLabelColor = $state('#E8772E');
  let newLabelLoading = $state(false);

  // Debounce timer for auto-save
  let saveTimer: ReturnType<typeof setTimeout> | undefined;

  const projectOptions = $derived.by(() => {
    const opts = projectsStore.projects.map(p => ({ value: String(p.id), label: p.title }));
    opts.push({ value: '__new__', label: '+ New Project' });
    return opts;
  });

  const availableLabels = $derived(
    labelsStore.labels.filter(l => {
      if (mode === 'proposal') {
        return !proposalLabelNames.includes(l.title);
      }
      return !currentLabels.some(cl => cl.id === l.id);
    })
  );

  const headerText = $derived.by(() => {
    if (mode === 'create') return 'New Task';
    if (mode === 'edit' && task) return task.title || `Task #${task.id}`;
    if (mode === 'proposal') return 'Edit Proposal';
    return 'Task';
  });

  // Key that only changes when the panel opens or switches to a different task/proposal
  const editKey = $derived.by(() => {
    if (!open) return '';
    if (mode === 'create') return 'create';
    if (mode === 'edit' && task) return `edit-${task.id}`;
    if (mode === 'proposal' && proposal) return `proposal-${proposal.id}`;
    return '';
  });

  // Populate form only when editKey changes (panel open / task switch), not on every store update
  $effect(() => {
    const key = editKey;  // sole reactive dependency
    if (!key) return;

    untrack(() => {
      creatingProject = false;
      newProjectName = '';
      showLabelPicker = false;
      creatingLabel = false;
      newLabelTitle = '';
      newLabelColor = '#E8772E';
      attachments = [];
      attachmentsLoading = false;
      subtasks = [];
      subtasksLoading = false;
      newSubtaskTitle = '';
      addingSubtask = false;

      if (mode === 'create') {
        title = '';
        description = '';
        priority = 3;
        dueDate = '';
        estimatedMinutes = '';
        currentLabels = [];
        proposalLabelNames = [];
        const pid = defaultProjectId ?? projectsStore.projects[0]?.id;
        projectValue = pid ? String(pid) : '';
        creating = false;
        setTimeout(() => titleRef?.focus(), 50);
      } else if (mode === 'edit' && task) {
        title = task.title;
        description = task.description || '';
        priority = task.priority;
        dueDate = task.due_date ? task.due_date.split('T')[0] : '';
        estimatedMinutes = '';
        currentLabels = [...(task.labels ?? [])];
        proposalLabelNames = [];
        projectValue = String(task.project_id);
        // Fetch attachments
        const taskId = task.id;
        attachmentsLoading = true;
        attachmentsApi.list(taskId).then(data => {
          attachments = data;
        }).catch(() => {
          attachments = [];
        }).finally(() => {
          attachmentsLoading = false;
        });
        // Fetch subtasks
        subtasksLoading = true;
        subtasksApi.list(taskId).then(data => {
          subtasks = data;
        }).catch(() => {
          subtasks = [];
        }).finally(() => {
          subtasksLoading = false;
        });
      } else if (mode === 'proposal' && proposal) {
        title = proposal.title;
        description = proposal.description || '';
        priority = proposal.priority;
        dueDate = proposal.due_date ? proposal.due_date.split('T')[0] : '';
        estimatedMinutes = proposal.estimated_minutes ? String(proposal.estimated_minutes) : '';
        currentLabels = [];
        proposalLabelNames = [...(proposal.labels || [])];
        projectValue = proposal.project_id ? String(proposal.project_id) : '';
      }
    });
  });

  // ── Auto-save helpers ──────────────────────────────────────────────

  function debouncedSave(field: string, value: unknown) {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      if (mode === 'edit' && task) {
        saveTaskField(field, value);
      } else if (mode === 'proposal' && proposal) {
        saveProposalField(field, value);
      }
    }, 500);
  }

  function immediateSave(field: string, value: unknown) {
    if (mode === 'edit' && task) {
      saveTaskField(field, value);
    } else if (mode === 'proposal' && proposal) {
      saveProposalField(field, value);
    }
  }

  async function saveTaskField(field: string, value: unknown) {
    if (!task) return;
    try {
      const data: Record<string, unknown> = {};
      if (field === 'due_date') {
        data.due_date = value || null;
      } else {
        data[field] = value;
      }
      await updateTask(task.id, data as Partial<Task>);
    } catch {
      addToast('Failed to save changes', 'error');
    }
  }

  async function saveProposalField(field: string, value: unknown) {
    if (!proposal) return;
    try {
      const data: Record<string, unknown> = { [field]: value };
      const updated = await proposalsApi.update(proposal.id, data as Partial<TaskProposal>);
      onupdate?.(updated);
    } catch {
      addToast('Failed to save changes', 'error');
    }
  }

  // ── Event handlers ─────────────────────────────────────────────────

  function handleTitleInput() {
    debouncedSave('title', title);
  }

  function handleDescriptionInput() {
    debouncedSave('description', description);
  }

  function handlePriorityChange(level: number) {
    priority = level;
    immediateSave('priority', level);
  }

  function handleProjectChange(v: string) {
    if (v === '__new__') {
      creatingProject = true;
      newProjectName = '';
      return;
    }
    creatingProject = false;
    projectValue = v;
    const pid = Number(v);
    if (pid) immediateSave('project_id', pid);
  }

  async function handleCreateProject() {
    if (!newProjectName.trim()) return;
    newProjectLoading = true;
    try {
      const project = await projectsStore.create({ title: newProjectName.trim() });
      projectValue = String(project.id);
      creatingProject = false;
      newProjectName = '';
      if (mode !== 'create') {
        immediateSave('project_id', project.id);
      }
      addToast(`Project "${project.title}" created`, 'success');
    } catch {
      addToast('Failed to create project', 'error');
    } finally {
      newProjectLoading = false;
    }
  }

  function handleDateChange(date: string | null) {
    dueDate = date ?? '';
    immediateSave('due_date', date);
  }

  function handleEstimatedMinutesInput() {
    const val = estimatedMinutes ? Number(estimatedMinutes) : null;
    debouncedSave('estimated_minutes', val);
  }

  async function handleDoneToggle() {
    if (mode === 'edit' && task) {
      await toggleDone(task.id);
    }
  }

  // ── Label management ───────────────────────────────────────────────

  async function addLabel(label: Label) {
    if (mode === 'edit' && task) {
      currentLabels = [...currentLabels, label];
      showLabelPicker = false;
      try {
        await tasksApi.addLabel(task.id, label.id);
      } catch {
        currentLabels = currentLabels.filter(l => l.id !== label.id);
        addToast('Failed to add label', 'error');
      }
    } else if (mode === 'proposal') {
      proposalLabelNames = [...proposalLabelNames, label.title];
      showLabelPicker = false;
      immediateSave('labels', proposalLabelNames);
    } else if (mode === 'create') {
      currentLabels = [...currentLabels, label];
      showLabelPicker = false;
    }
  }

  async function removeLabel(label: Label) {
    if (mode === 'edit' && task) {
      currentLabels = currentLabels.filter(l => l.id !== label.id);
      try {
        await tasksApi.removeLabel(task.id, label.id);
      } catch {
        currentLabels = [...currentLabels, label];
        addToast('Failed to remove label', 'error');
      }
    } else if (mode === 'create') {
      currentLabels = currentLabels.filter(l => l.id !== label.id);
    }
  }

  function removeProposalLabel(name: string) {
    proposalLabelNames = proposalLabelNames.filter(l => l !== name);
    immediateSave('labels', proposalLabelNames);
  }

  async function handleCreateLabel() {
    if (!newLabelTitle.trim()) return;
    newLabelLoading = true;
    try {
      const label = await labelsStore.create({ title: newLabelTitle.trim(), hex_color: newLabelColor });
      addLabel(label);
      creatingLabel = false;
      newLabelTitle = '';
      addToast(`Label "${label.title}" created`, 'success');
    } catch {
      addToast('Failed to create label', 'error');
    } finally {
      newLabelLoading = false;
    }
  }

  // ── Attachments ────────────────────────────────────────────────────

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function getFileIcon(mime: string): string {
    if (mime.startsWith('image/')) return '🖼';
    if (mime.startsWith('video/')) return '🎬';
    if (mime.startsWith('audio/')) return '🎵';
    if (mime.includes('pdf')) return '📄';
    if (mime.includes('zip') || mime.includes('tar') || mime.includes('gz')) return '📦';
    if (mime.includes('spreadsheet') || mime.includes('csv') || mime.includes('excel')) return '📊';
    return '📎';
  }

  async function handleFileUpload(files: FileList | null) {
    if (!files || !task) return;
    uploading = true;
    for (const file of Array.from(files)) {
      try {
        const result = await attachmentsApi.upload(task.id, file);
        // Vikunja returns the attachment wrapped or directly
        if (result) {
          // Refetch to get clean data
          attachments = await attachmentsApi.list(task.id);
        }
        addToast(`Uploaded ${file.name}`, 'success');
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Upload failed';
        addToast(msg, 'error');
      }
    }
    uploading = false;
    if (fileInputRef) fileInputRef.value = '';
  }

  async function handleDeleteAttachment(att: TaskAttachment) {
    if (!task || !confirm(`Delete "${att.file.name}"?`)) return;
    const prev = attachments;
    attachments = attachments.filter(a => a.id !== att.id);
    try {
      await attachmentsApi.delete(task.id, att.id);
      addToast('Attachment deleted', 'success');
    } catch {
      attachments = prev;
      addToast('Failed to delete attachment', 'error');
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    dragOver = false;
    handleFileUpload(e.dataTransfer?.files ?? null);
  }

  // ── Subtask handlers ───────────────────────────────────────────────

  async function toggleSubtask(st: Subtask) {
    const prev = st.done;
    st.done = !prev;
    subtasks = [...subtasks];
    try {
      await subtasksApi.update(task!.id, st.id, { done: !prev });
    } catch {
      st.done = prev;
      subtasks = [...subtasks];
      addToast('Failed to update subtask', 'error');
    }
  }

  async function handleAddSubtask() {
    if (!newSubtaskTitle.trim() || !task) return;
    addingSubtask = true;
    try {
      const created = await subtasksApi.create(task.id, { title: newSubtaskTitle.trim() });
      subtasks = [created, ...subtasks];
      newSubtaskTitle = '';
    } catch {
      addToast('Failed to add subtask', 'error');
    } finally {
      addingSubtask = false;
    }
  }

  async function deleteSubtask(st: Subtask) {
    if (!task) return;
    const prev = subtasks;
    subtasks = subtasks.filter(s => s.id !== st.id);
    try {
      await subtasksApi.delete(task.id, st.id);
    } catch {
      subtasks = prev;
      addToast('Failed to delete subtask', 'error');
    }
  }

  // ── Create / Delete ────────────────────────────────────────────────

  async function handleCreate() {
    if (!title.trim()) return;
    const pid = Number(projectValue);
    if (!pid) {
      addToast('Select a project first', 'error');
      return;
    }
    creating = true;
    try {
      const created = await tasksStore.create({
        project_id: pid,
        title: title.trim(),
        priority,
        due_date: dueDate || undefined,
        description: description.trim() || undefined,
      });
      // Attach labels after creation using the returned task ID
      if (created && currentLabels.length > 0) {
        for (const label of currentLabels) {
          try {
            await tasksApi.addLabel(created.id, label.id);
          } catch {
            // Non-critical, label attachment can fail
          }
        }
        await tasksStore.fetchAll();
      }
      addToast('Task created', 'success');
      onclose?.();
    } catch {
      addToast('Failed to create task', 'error');
    } finally {
      creating = false;
    }
  }

  async function handleDelete() {
    if (mode !== 'edit' || !task) return;
    if (!confirm('Delete this task? This cannot be undone.')) return;
    const taskId = task.id;
    onclose?.();
    deleting = true;
    try {
      await deleteTask(taskId);
      addToast('Task deleted', 'success');
    } catch {
      addToast('Failed to delete task', 'error');
    } finally {
      deleting = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && mode === 'create') {
      e.preventDefault();
      handleCreate();
    }
  }

  const labelColors = [
    '#E8772E', '#EF5744', '#E2C541', '#5BBC6E',
    '#4AADCC', '#7B6FE8', '#D46AB3', '#A1A09A',
  ];

  const priorityColors = [
    'var(--priority-none)',
    'var(--priority-low)',
    'var(--priority-low)',
    'var(--priority-medium)',
    'var(--priority-high)',
    'var(--priority-urgent)',
  ];
</script>

<SlideOver {open} {onclose}>
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div onkeydown={handleKeydown} style="padding: 28px 28px 32px; display: flex; flex-direction: column; gap: 22px; overflow-y: auto; max-height: 100vh;">
    <!-- Header -->
    <div style="display: flex; align-items: center; justify-content: space-between;">
      <span style="font-size: 18px; font-weight: 600; letter-spacing: -0.02em; color: var(--text-primary);">{headerText}</span>
      <button
        aria-label="Close"
        onclick={onclose}
        style="width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background: none; border: none; color: var(--text-tertiary); cursor: pointer; border-radius: 6px; font-size: 18px; transition: color 150ms;"
      >&times;</button>
    </div>

    <!-- Done checkbox (edit mode only) -->
    {#if mode === 'edit' && task}
      <div style="display: flex; align-items: center; gap: 10px;">
        <Checkbox checked={task.done} onchange={handleDoneToggle} />
        <span style="font-size: 14px; color: {task.done ? 'var(--done)' : 'var(--text-secondary)'}; font-weight: 500;">
          {task.done ? 'Completed' : 'Mark as done'}
        </span>
      </div>
    {/if}

    <!-- Title -->
    <div style="display: flex; flex-direction: column; gap: 6px;">
      <!-- svelte-ignore a11y_label_has_associated_control -->
      <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Title</label>
      <Input placeholder="What needs to be done?" bind:value={title} bind:ref={titleRef} oninput={mode !== 'create' ? handleTitleInput : undefined} />
    </div>

    <!-- Project + Priority row -->
    <div style="display: flex; gap: 16px; align-items: flex-end;">
      <div style="flex: 1; display: flex; flex-direction: column; gap: 6px;">
        <!-- svelte-ignore a11y_label_has_associated_control -->
        <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Project</label>
        {#if creatingProject}
          <div style="display: flex; gap: 8px; align-items: center;">
            <Input placeholder="Project name..." bind:value={newProjectName} height={34} onkeydown={(e) => { if (e.key === 'Enter') handleCreateProject(); if (e.key === 'Escape') creatingProject = false; }} style="flex: 1;" />
            <Button variant="accent" size="sm" loading={newProjectLoading} onclick={handleCreateProject}>Create</Button>
          </div>
        {:else}
          <Dropdown
            options={projectOptions}
            value={projectValue}
            onchange={handleProjectChange}
            placeholder="Select project..."
            width={200}
          />
        {/if}
      </div>
      <div style="display: flex; flex-direction: column; gap: 6px;">
        <!-- svelte-ignore a11y_label_has_associated_control -->
        <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Priority</label>
        <div style="display: flex; align-items: center; gap: 5px; height: 34px;">
          {#each [1, 2, 3, 4, 5] as level (level)}
            <button
              type="button"
              aria-label="Priority {level}"
              onclick={() => handlePriorityChange(level)}
              style="width: 16px; height: 16px; border-radius: 50%; border: none; cursor: pointer; background: {level <= priority ? priorityColors[priority] : 'var(--border-default)'}; transition: all 150ms; transform: {level <= priority ? 'scale(1)' : 'scale(0.85)'};"
            ></button>
          {/each}
        </div>
      </div>
    </div>

    <!-- Due date -->
    <div style="display: flex; flex-direction: column; gap: 6px;">
      <!-- svelte-ignore a11y_label_has_associated_control -->
      <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Due date</label>
      <DatePicker value={dueDate} onchange={handleDateChange} />
    </div>

    <!-- Estimated minutes (proposal mode or create mode) -->
    {#if mode === 'proposal' || mode === 'create'}
      <div style="display: flex; flex-direction: column; gap: 6px;">
        <!-- svelte-ignore a11y_label_has_associated_control -->
        <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Estimated minutes</label>
        <Input placeholder="e.g. 30" type="number" bind:value={estimatedMinutes} oninput={mode !== 'create' ? handleEstimatedMinutesInput : undefined} height={34} style="width: 120px;" />
      </div>
    {/if}

    <!-- Labels -->
    <div style="display: flex; flex-direction: column; gap: 6px;">
      <!-- svelte-ignore a11y_label_has_associated_control -->
      <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Labels</label>
      <div style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center;">
        {#if mode === 'proposal'}
          {#each proposalLabelNames as name (name)}
            <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
            <span
              onclick={() => removeProposalLabel(name)}
              style="display: inline-flex; align-items: center; gap: 4px; height: 24px; padding: 0 9px; font-size: 12.5px; font-weight: 500; color: var(--text-secondary); background: var(--bg-elevated); border-radius: 9999px; cursor: pointer;"
            >
              {name}
              <span style="font-size: 10px; opacity: 0.6;">&times;</span>
            </span>
          {/each}
        {:else}
          {#each currentLabels as label (label.id)}
            <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
            <span
              onclick={() => removeLabel(label)}
              style="display: inline-flex; align-items: center; gap: 4px; height: 24px; padding: 0 9px; font-size: 12.5px; font-weight: 500; color: {label.hex_color || 'var(--text-secondary)'}; background: {label.hex_color ? label.hex_color + '20' : 'var(--bg-elevated)'}; border-radius: 9999px; cursor: pointer;"
            >
              {label.title}
              <span style="font-size: 10px; opacity: 0.6;">&times;</span>
            </span>
          {/each}
        {/if}

        <div style="position: relative;">
          <button
            type="button"
            onclick={() => {
              showLabelPicker = !showLabelPicker;
              if (showLabelPicker && labelsStore.labels.length === 0) {
                labelsStore.fetchAll();
              }
            }}
            style="height: 24px; padding: 0 9px; font-size: 12.5px; font-weight: 500; color: var(--text-tertiary); background: var(--bg-elevated); border: 1px dashed var(--border-default); border-radius: 9999px; cursor: pointer; font-family: var(--font-sans);"
          >+ Add</button>

          {#if showLabelPicker}
            <div style="position: absolute; top: calc(100% + 4px); left: 0; z-index: 300; background: var(--bg-elevated); border: 1px solid var(--border-strong); border-radius: 8px; box-shadow: var(--shadow-lg); padding: 4px; min-width: 180px; max-height: 260px; overflow-y: auto; animation: fadeIn 100ms ease-out;">
              {#if labelsStore.loading}
                <div style="padding: 10px 12px; font-size: 13px; color: var(--text-tertiary);">Loading...</div>
              {:else}
                {#if availableLabels.length > 0}
                  {#each availableLabels as label (label.id)}
                    <button
                      type="button"
                      onclick={() => addLabel(label)}
                      style="width: 100%; padding: 6px 10px; font-size: 13px; color: {label.hex_color || 'var(--text-secondary)'}; background: transparent; border: none; border-radius: 6px; cursor: pointer; text-align: left; font-family: var(--font-sans); display: flex; align-items: center; gap: 8px;"
                    >
                      <span style="width: 8px; height: 8px; border-radius: 50%; background: {label.hex_color || 'var(--text-tertiary)'}; flex-shrink: 0;"></span>
                      {label.title}
                    </button>
                  {/each}
                {:else}
                  <div style="padding: 10px 12px; font-size: 13px; color: var(--text-tertiary);">No labels available</div>
                {/if}

                <!-- Divider + Create Label -->
                <div style="border-top: 1px solid var(--border-default); margin: 4px 0;"></div>
                {#if creatingLabel}
                  <!-- svelte-ignore a11y_no_static_element_interactions -->
                  <div style="padding: 6px 8px; display: flex; flex-direction: column; gap: 6px;" onkeydown={(e) => { if (e.key === 'Escape') { creatingLabel = false; } }}>
                    <input
                      type="text"
                      placeholder="Label name..."
                      bind:value={newLabelTitle}
                      onkeydown={(e) => { if (e.key === 'Enter') handleCreateLabel(); }}
                      style="width: 100%; height: 28px; padding: 0 8px; font-size: 13px; font-family: var(--font-sans); color: var(--text-primary); background: var(--bg-surface); border: 1px solid var(--border-default); border-radius: 6px; outline: none; box-sizing: border-box;"
                    />
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                      <div style="display: flex; gap: 4px; align-items: center;">
                        {#each labelColors as color (color)}
                          <button
                            type="button"
                            aria-label="Color {color}"
                            onclick={() => { newLabelColor = color; }}
                            style="width: 20px; height: 20px; border-radius: 50%; background: {color}; border: 2px solid {newLabelColor === color ? 'var(--text-primary)' : 'transparent'}; cursor: pointer; padding: 0; transition: all 150ms; transform: {newLabelColor === color ? 'scale(1.15)' : 'scale(1)'};"
                          ></button>
                        {/each}
                      </div>
                      <Button variant="accent" size="sm" loading={newLabelLoading} onclick={handleCreateLabel}>Create</Button>
                    </div>
                  </div>
                {:else}
                  <button
                    type="button"
                    onclick={() => { creatingLabel = true; }}
                    style="width: 100%; padding: 6px 10px; font-size: 13px; color: var(--text-tertiary); background: transparent; border: none; border-radius: 6px; cursor: pointer; text-align: left; font-family: var(--font-sans);"
                  >+ Create Label</button>
                {/if}
              {/if}
            </div>
          {/if}
        </div>
      </div>
    </div>

    <!-- Attachments (edit mode only) -->
    {#if mode === 'edit' && task}
      <div style="display: flex; flex-direction: column; gap: 6px;">
        <!-- svelte-ignore a11y_label_has_associated_control -->
        <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Attachments</label>

        {#if attachmentsLoading}
          <div style="font-size: 13px; color: var(--text-tertiary);">Loading...</div>
        {:else}
          <!-- Image previews -->
          {#if attachments.some(a => a.file.mime.startsWith('image/'))}
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
              {#each attachments.filter(a => a.file.mime.startsWith('image/')) as att (att.id)}
                <div style="position: relative; border-radius: 6px; overflow: hidden; background: var(--bg-elevated);">
                  <a href={attachmentsApi.downloadUrl(task.id, att.id)} target="_blank" rel="noopener noreferrer">
                    <img
                      src={attachmentsApi.previewUrl(task.id, att.id, 'md')}
                      alt={att.file.name}
                      style="display: block; max-width: 200px; max-height: 150px; object-fit: cover; border-radius: 6px;"
                    />
                  </a>
                  <div style="display: flex; align-items: center; gap: 4px; padding: 4px 6px; font-size: 12px;">
                    <span style="color: var(--text-secondary); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title={att.file.name}>{att.file.name}</span>
                    <span style="color: var(--text-tertiary); flex-shrink: 0;">{formatFileSize(att.file.size)}</span>
                    <button
                      type="button"
                      onclick={() => handleDeleteAttachment(att)}
                      aria-label="Delete attachment"
                      style="width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; background: none; border: none; color: var(--text-tertiary); cursor: pointer; border-radius: 4px; font-size: 13px; flex-shrink: 0;"
                    >&times;</button>
                  </div>
                </div>
              {/each}
            </div>
          {/if}

          <!-- Non-image attachment list -->
          {#if attachments.some(a => !a.file.mime.startsWith('image/'))}
            <div style="display: flex; flex-direction: column; gap: 4px;">
              {#each attachments.filter(a => !a.file.mime.startsWith('image/')) as att (att.id)}
                <div style="display: flex; align-items: center; gap: 8px; padding: 6px 8px; background: var(--bg-elevated); border-radius: 6px; font-size: 13px;">
                  <span>{getFileIcon(att.file.mime)}</span>
                  <a
                    href={attachmentsApi.downloadUrl(task.id, att.id)}
                    style="color: var(--text-primary); text-decoration: none; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
                    title={att.file.name}
                  >{att.file.name}</a>
                  <span style="color: var(--text-tertiary); font-size: 12px; flex-shrink: 0;">{formatFileSize(att.file.size)}</span>
                  <button
                    type="button"
                    onclick={() => handleDeleteAttachment(att)}
                    aria-label="Delete attachment"
                    style="width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; background: none; border: none; color: var(--text-tertiary); cursor: pointer; border-radius: 4px; font-size: 14px; flex-shrink: 0;"
                  >&times;</button>
                </div>
              {/each}
            </div>
          {/if}

          <!-- Drop zone -->
          <div
            ondragover={(e) => { e.preventDefault(); dragOver = true; }}
            ondragleave={() => { dragOver = false; }}
            ondrop={handleDrop}
            onclick={() => fileInputRef?.click()}
            role="button"
            tabindex="0"
            onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef?.click(); }}
            style="display: flex; align-items: center; justify-content: center; gap: 6px; padding: 12px; border: 1.5px dashed {dragOver ? 'var(--accent)' : 'var(--border-default)'}; border-radius: 8px; cursor: pointer; font-size: 13px; color: var(--text-tertiary); background: {dragOver ? 'var(--accent-ghost)' : 'transparent'}; transition: all 150ms;"
          >
            {#if uploading}
              <span>Uploading...</span>
            {:else}
              <span>Drop files here or click to upload</span>
            {/if}
          </div>

          <input
            type="file"
            multiple
            bind:this={fileInputRef}
            onchange={(e) => handleFileUpload(e.currentTarget.files)}
            style="display: none;"
          />
        {/if}
      </div>
    {/if}

    <!-- Subtasks (edit mode only) -->
    {#if mode === 'edit' && task}
      <div style="display: flex; flex-direction: column; gap: 6px;">
        <!-- svelte-ignore a11y_label_has_associated_control -->
        <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Subtasks</label>

        {#if subtasksLoading}
          <div style="font-size: 13px; color: var(--text-tertiary);">Loading...</div>
        {:else}
          {#if subtasks.length > 0}
            <div style="display: flex; flex-direction: column; gap: 2px;">
              {#each subtasks as st (st.id)}
                <div style="display: flex; align-items: center; gap: 8px; padding: 5px 8px; background: var(--bg-elevated); border-radius: 6px; font-size: 13px;">
                  <Checkbox checked={st.done} onchange={() => toggleSubtask(st)} />
                  <span style="flex: 1; color: {st.done ? 'var(--text-tertiary)' : 'var(--text-primary)'}; text-decoration: {st.done ? 'line-through' : 'none'}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    {st.title}
                  </span>
                  <button
                    type="button"
                    onclick={() => deleteSubtask(st)}
                    aria-label="Delete subtask"
                    style="width: 22px; height: 22px; display: flex; align-items: center; justify-content: center; background: none; border: none; color: var(--text-tertiary); cursor: pointer; border-radius: 4px; font-size: 14px; flex-shrink: 0; opacity: 0.6; transition: opacity 150ms;"
                  >&times;</button>
                </div>
              {/each}
            </div>
          {/if}

          <!-- Add subtask input -->
          <div style="display: flex; gap: 8px; align-items: center;">
            <Input
              placeholder="Add subtask..."
              bind:value={newSubtaskTitle}
              height={32}
              onkeydown={(e) => { if (e.key === 'Enter') handleAddSubtask(); }}
              style="flex: 1;"
            />
            <Button variant="ghost" size="sm" loading={addingSubtask} onclick={handleAddSubtask}>Add</Button>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Description -->
    <div style="display: flex; flex-direction: column; gap: 6px;">
      <!-- svelte-ignore a11y_label_has_associated_control -->
      <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Description</label>
      <Textarea placeholder="Add details..." bind:value={description} rows={4} oninput={mode !== 'create' ? handleDescriptionInput : undefined} />
    </div>

    <!-- Actions -->
    <div style="display: flex; align-items: center; gap: 12px; margin-top: 4px;">
      {#if mode === 'create'}
        <Button variant="accent" loading={creating} onclick={handleCreate}>Create Task</Button>
        <span style="font-size: 12px; color: var(--text-tertiary); display: flex; align-items: center; gap: 4px;">
          <Kbd>{navigator?.platform?.includes('Mac') ? '⌘' : 'Ctrl'}+Enter</Kbd>
        </span>
      {:else if mode === 'edit'}
        <Button variant="danger" size="sm" loading={deleting} onclick={handleDelete}>Delete Task</Button>
      {/if}
    </div>

    <!-- Timestamps (edit mode) -->
    {#if mode === 'edit' && task}
      <div style="margin-top: 8px; font-size: 12px; color: var(--text-tertiary); display: flex; flex-direction: column; gap: 4px;">
        <span>Created: {new Date(task.created).toLocaleString()}</span>
        <span>Updated: {new Date(task.updated).toLocaleString()}</span>
      </div>
    {/if}
  </div>
</SlideOver>
