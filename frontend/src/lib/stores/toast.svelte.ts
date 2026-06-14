export type ToastAction = { label: string; onClick: () => void };

export type ToastItem = {
  id: string;
  message: string;
  variant: 'success' | 'error' | 'info';
  duration: number;
  /** When true, the toast carries the AI diamond — Cognito itself is speaking. */
  ai?: boolean;
  /** Optional inline action (undo / adjust). */
  action?: ToastAction;
};

export type ToastOptions = {
  ai?: boolean;
  action?: ToastAction;
};

let _toasts = $state<ToastItem[]>([]);

export const toasts = {
  get value() {
    return _toasts;
  },
};

export function removeToast(id: string) {
  _toasts = _toasts.filter((t) => t.id !== id);
}

export function addToast(
  message: string,
  variant: ToastItem['variant'] = 'info',
  duration = 4000,
  opts: ToastOptions = {},
) {
  const id = crypto.randomUUID();
  _toasts = [..._toasts, { id, message, variant, duration, ai: opts.ai, action: opts.action }];
  setTimeout(() => removeToast(id), duration);
  return id;
}
