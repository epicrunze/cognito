<script lang="ts">
  import { tasksStore, projectsStore } from '$lib/stores.svelte';
  import { addToast } from '$lib/stores/toast.svelte';
  import SlideOver from '$components/ui/SlideOver.svelte';
  import Input from '$components/ui/Input.svelte';
  import Textarea from '$components/ui/Textarea.svelte';
  import Button from '$components/ui/Button.svelte';
  import Dropdown from '$components/ui/Dropdown.svelte';
  import Kbd from '$components/ui/Kbd.svelte';

  let {
    open = false,
    onclose,
    defaultProjectId,
  }: {
    open: boolean;
    onclose?: () => void;
    defaultProjectId?: number;
  } = $props();

  let title = $state('');
  let description = $state('');
  let priority = $state(3);
  let dueDate = $state('');
  let projectValue = $state('');
  let creating = $state(false);
  let titleRef = $state<HTMLInputElement | undefined>(undefined);

  const projectOptions = $derived(
    projectsStore.projects.map(p => ({ value: String(p.id), label: p.title }))
  );

  // Reset form & set defaults when panel opens
  $effect(() => {
    if (open) {
      title = '';
      description = '';
      priority = 3;
      dueDate = '';
      const pid = defaultProjectId ?? projectsStore.projects[0]?.id;
      projectValue = pid ? String(pid) : '';
      creating = false;
      // Focus title after transition
      setTimeout(() => titleRef?.focus(), 50);
    }
  });

  async function handleCreate() {
    if (!title.trim()) return;
    const pid = Number(projectValue);
    if (!pid) {
      addToast('Select a project first', 'error');
      return;
    }
    creating = true;
    try {
      await tasksStore.create({
        project_id: pid,
        title: title.trim(),
        priority,
        due_date: dueDate || undefined,
        description: description.trim() || undefined,
      });
      addToast('Task created', 'success');
      onclose?.();
    } catch {
      addToast('Failed to create task', 'error');
    } finally {
      creating = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleCreate();
    }
  }

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
  <div onkeydown={handleKeydown} style="padding: 28px 28px 32px; display: flex; flex-direction: column; gap: 22px;">
    <!-- Header -->
    <div style="display: flex; align-items: center; justify-content: space-between;">
      <span style="font-size: 18px; font-weight: 600; letter-spacing: -0.02em; color: var(--text-primary);">New Task</span>
      <button
        aria-label="Close"
        onclick={onclose}
        style="width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; background: none; border: none; color: var(--text-tertiary); cursor: pointer; border-radius: 6px; font-size: 18px; transition: color 150ms;"
      >&times;</button>
    </div>

    <!-- Title -->
    <div style="display: flex; flex-direction: column; gap: 6px;">
      <!-- svelte-ignore a11y_label_has_associated_control -->
      <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Title</label>
      <Input placeholder="What needs to be done?" bind:value={title} bind:ref={titleRef} />
    </div>

    <!-- Project + Priority row -->
    <div style="display: flex; gap: 16px; align-items: flex-end;">
      <div style="flex: 1; display: flex; flex-direction: column; gap: 6px;">
        <!-- svelte-ignore a11y_label_has_associated_control -->
        <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Project</label>
        <Dropdown
          options={projectOptions}
          value={projectValue}
          onchange={(v) => projectValue = v}
          placeholder="Select project..."
          width={200}
        />
      </div>
      <div style="display: flex; flex-direction: column; gap: 6px;">
        <!-- svelte-ignore a11y_label_has_associated_control -->
        <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Priority</label>
        <div style="display: flex; align-items: center; gap: 5px; height: 34px;">
          {#each [1, 2, 3, 4, 5] as level (level)}
            <button
              type="button"
              aria-label="Priority {level}"
              onclick={() => priority = level}
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
      <Input placeholder="YYYY-MM-DD" bind:value={dueDate} />
    </div>

    <!-- Description -->
    <div style="display: flex; flex-direction: column; gap: 6px;">
      <!-- svelte-ignore a11y_label_has_associated_control -->
      <label style="font-size: 13px; font-weight: 500; color: var(--text-secondary);">Description</label>
      <Textarea placeholder="Add details..." bind:value={description} rows={4} />
    </div>

    <!-- Actions -->
    <div style="display: flex; align-items: center; gap: 12px; margin-top: 4px;">
      <Button variant="accent" loading={creating} onclick={handleCreate}>Create Task</Button>
      <span style="font-size: 12px; color: var(--text-tertiary); display: flex; align-items: center; gap: 4px;">
        <Kbd>{navigator?.platform?.includes('Mac') ? '⌘' : 'Ctrl'}+Enter</Kbd>
      </span>
    </div>
  </div>
</SlideOver>
