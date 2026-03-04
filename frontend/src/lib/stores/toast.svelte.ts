export type ToastItem = {
  id: string;
  message: string;
  variant: 'success' | 'error' | 'info';
  duration: number;
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
) {
  const id = crypto.randomUUID();
  _toasts = [..._toasts, { id, message, variant, duration }];
  setTimeout(() => removeToast(id), duration);
}
