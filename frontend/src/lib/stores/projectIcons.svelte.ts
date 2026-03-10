// Project icon (emoji) overrides — persisted in localStorage
const STORAGE_KEY = 'cognito-project-icons';

function loadIcons(): Record<string, string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveIcons(icons: Record<string, string>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(icons));
}

let icons = $state<Record<string, string>>(loadIcons());

// Curated emoji palette for the picker
export const ICON_EMOJIS = [
  '💼', '🏠', '❤️', '🏃', '📚', '🎓', '💻', '🎨',
  '🎵', '✈️', '🍳', '💰', '🌟', '✍️', '🌱', '🐾',
  '📖', '🎮', '🔬', '🧪', '🏗️', '🎯', '💡', '🔧',
  '📌', '🎬', '🏋️', '🧘', '📸', '🎧', '🛒', '🏡',
  '⚡', '🌍', '🎁', '📊', '🚀', '🧑‍💻', '📝', '☕',
];

// Keyword-based auto-detection
const KEYWORD_MAP: Record<string, string> = {
  'work': '💼', 'home': '🏠', 'health': '❤️', 'fitness': '🏃',
  'study': '📚', 'phd': '🎓', 'school': '🎓', 'code': '💻',
  'design': '🎨', 'music': '🎵', 'travel': '✈️', 'food': '🍳',
  'money': '💰', 'finance': '💰', 'personal': '🌟', 'writing': '✍️',
  'garden': '🌱', 'pet': '🐾', 'read': '📖', 'game': '🎮',
  'science': '🔬', 'build': '🏗️', 'photo': '📸', 'shop': '🛒',
};

// Emoji fallbacks (used when no keyword match and no override)
const FALLBACK_EMOJIS = ['📌', '📂', '📋', '🔷', '🔶', '⭐', '🎯', '💡'];

function autoEmoji(title: string): string {
  const lower = title.toLowerCase();
  for (const [key, emoji] of Object.entries(KEYWORD_MAP)) {
    if (lower.includes(key)) return emoji;
  }
  const hash = [...title].reduce((h, c) => h + c.charCodeAt(0), 0);
  return FALLBACK_EMOJIS[hash % FALLBACK_EMOJIS.length];
}

export const projectIconStore = {
  /** Get the icon for a project — user override > keyword match > fallback */
  get(projectId: number, title: string): string {
    return icons[String(projectId)] ?? autoEmoji(title);
  },

  /** Set a custom icon for a project */
  set(projectId: number, emoji: string) {
    icons = { ...icons, [String(projectId)]: emoji };
    saveIcons(icons);
  },

  /** Clear custom icon (revert to auto-detection) */
  clear(projectId: number) {
    const { [String(projectId)]: _, ...rest } = icons;
    icons = rest;
    saveIcons(icons);
  },

  /** Check if a project has a custom override */
  hasOverride(projectId: number): boolean {
    return String(projectId) in icons;
  },
};
