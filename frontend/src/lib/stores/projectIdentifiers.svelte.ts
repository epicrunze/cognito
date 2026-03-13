// Project identifier overrides — persisted in localStorage
const STORAGE_KEY = 'cognito-project-identifiers';

function loadIdentifiers(): Record<string, string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveIdentifiers(identifiers: Record<string, string>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(identifiers));
}

let identifiers = $state<Record<string, string>>(loadIdentifiers());

export const projectIdentifierStore = {
  /** Get identifier: user override or first letter of title */
  get(projectId: number, title: string): string {
    return identifiers[String(projectId)] ?? title.charAt(0).toUpperCase();
  },

  /** Set a custom identifier (1-3 chars) */
  set(projectId: number, value: string) {
    const trimmed = value.trim().slice(0, 3).toUpperCase();
    if (!trimmed) return;
    identifiers = { ...identifiers, [String(projectId)]: trimmed };
    saveIdentifiers(identifiers);
  },

  /** Clear custom identifier (revert to auto-generated) */
  clear(projectId: number) {
    const { [String(projectId)]: _, ...rest } = identifiers;
    identifiers = rest;
    saveIdentifiers(identifiers);
  },

  /** Check if a project has a custom override */
  hasOverride(projectId: number): boolean {
    return String(projectId) in identifiers;
  },
};
