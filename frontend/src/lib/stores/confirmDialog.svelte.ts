type ConfirmRequest = {
  id: string;
  title: string;
  message: string;
  confirmLabel?: string;
  destructive?: boolean;
  resolve: (confirmed: boolean) => void;
};

let _request = $state<ConfirmRequest | null>(null);

export const confirmDialogState = {
  get request() { return _request; },
};

export function showConfirmDialog(opts: {
  title: string;
  message: string;
  confirmLabel?: string;
  destructive?: boolean;
}): Promise<boolean> {
  return new Promise((resolve) => {
    _request = { id: crypto.randomUUID(), ...opts, resolve };
  });
}

export function resolveDialog(confirmed: boolean) {
  _request?.resolve(confirmed);
  _request = null;
}
