let _query = $state('');
let _timer: ReturnType<typeof setTimeout> | null = null;

export const searchStore = {
  get query() {
    return _query;
  },

  /** Update query immediately (e.g. when clearing) */
  setImmediate(q: string) {
    if (_timer) clearTimeout(_timer);
    _query = q;
  },

  /** Update query with 300ms debounce */
  set(q: string) {
    if (_timer) clearTimeout(_timer);
    _timer = setTimeout(() => {
      _query = q;
    }, 300);
  },
};
