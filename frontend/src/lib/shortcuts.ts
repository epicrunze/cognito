export type ShortcutHandler = () => void;

class ShortcutManager {
  private handlers: Map<string, ShortcutHandler> = new Map();

  register(key: string, handler: ShortcutHandler): void {
    this.handlers.set(key, handler);
  }

  unregister(key: string): void {
    this.handlers.delete(key);
  }

  handleKeydown = (event: KeyboardEvent): void => {
    const target = event.target as Element;
    if (
      target instanceof HTMLInputElement ||
      target instanceof HTMLTextAreaElement ||
      target.hasAttribute('contenteditable')
    ) {
      return;
    }

    const handler = this.handlers.get(event.key);
    if (handler) {
      event.preventDefault();
      handler();
    }
  };
}

export const shortcuts = new ShortcutManager();

// Pre-register placeholders; concrete handlers wired in layout
shortcuts.register('n', () => {});
shortcuts.register('/', () => {});
shortcuts.register('Escape', () => {});
