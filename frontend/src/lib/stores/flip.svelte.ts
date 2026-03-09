import { tick } from 'svelte';

const elements = new Map<number | string, HTMLElement>();

/** Resolves when cards register after a view switch */
let pendingResolve: (() => void) | null = null;
let pendingTimer: ReturnType<typeof setTimeout> | null = null;
/** How many elements we expect to see (0 = not waiting) */
let waitingForRegistrations = false;

export const flipStore = {
	get elementCount() {
		return elements.size;
	},

	register(id: number | string, el: HTMLElement) {
		elements.set(id, el);
		// If we're waiting for cards to appear and some have now registered,
		// use a microtask to batch registrations that happen in the same frame
		if (waitingForRegistrations && pendingResolve) {
			// Debounce: reset timer each time a new card registers
			if (pendingTimer) clearTimeout(pendingTimer);
			pendingTimer = setTimeout(() => {
				if (pendingResolve) {
					pendingResolve();
					pendingResolve = null;
				}
				waitingForRegistrations = false;
				pendingTimer = null;
			}, 50); // 50ms after last registration — all cards from this render are in
		}
	},

	unregister(id: number | string) {
		elements.delete(id);
	},

	capturePositions(): Map<number | string, DOMRect> {
		const positions = new Map<number | string, DOMRect>();
		for (const [id, el] of elements) {
			positions.set(id, el.getBoundingClientRect());
		}
		return positions;
	},

	/**
	 * Wait for cards to register in the FLIP store after a view switch.
	 * Resolves when cards stop registering (50ms debounce) or after maxWait.
	 */
	waitForCards(maxWait = 3000): Promise<void> {
		return new Promise((resolve) => {
			waitingForRegistrations = true;

			// Cancel any stale pending state
			if (pendingTimer) clearTimeout(pendingTimer);

			pendingResolve = resolve;

			// If cards already exist, kick off the debounce
			// (the register() callback will reset this timer as more cards arrive)
			if (elements.size > 0) {
				pendingTimer = setTimeout(() => {
					if (pendingResolve) { pendingResolve(); pendingResolve = null; }
					waitingForRegistrations = false;
					pendingTimer = null;
				}, 50);
			}

			// Safety: max wait timeout
			setTimeout(() => {
				if (pendingResolve) { pendingResolve(); pendingResolve = null; }
				waitingForRegistrations = false;
				if (pendingTimer) { clearTimeout(pendingTimer); pendingTimer = null; }
			}, maxWait);
		});
	},

	/**
	 * Play FLIP animation: animate registered elements from old positions to current.
	 * Cards not in oldPositions fade in. Cards that didn't move are skipped.
	 */
	play(oldPositions: Map<number | string, DOMRect>, options?: { duration?: number; stagger?: number }) {
		const { duration = 550, stagger = 25 } = options ?? {};
		const easing = 'cubic-bezier(0.4, 0, 0.2, 1)';

		let i = 0;
		for (const [id, el] of elements) {
			const oldRect = oldPositions.get(id);
			if (!oldRect) {
				// New card — fade in
				el.animate(
					[{ opacity: 0, transform: 'scale(0.95)' }, { opacity: 1, transform: 'scale(1)' }],
					{ duration, delay: i * stagger, easing, fill: 'backwards' },
				);
				i++;
				continue;
			}
			const newRect = el.getBoundingClientRect();
			const dx = oldRect.left - newRect.left;
			const dy = oldRect.top - newRect.top;

			if (Math.abs(dx) < 1 && Math.abs(dy) < 1) continue;

			el.animate(
				[
					{ transform: `translate(${dx}px, ${dy}px)` },
					{ transform: 'translate(0, 0)' },
				],
				{ duration, easing, delay: i * stagger, fill: 'backwards' },
			);
			i++;
		}
	},

	/** Return all registered element entries for direct animation access */
	getAllElements(): IterableIterator<[number | string, HTMLElement]> {
		return elements.entries();
	},

	/** Remove all registered elements */
	clearAll() {
		elements.clear();
		this.cancelWait();
	},

	/** Cancel any pending wait */
	cancelWait() {
		if (pendingTimer) {
			clearTimeout(pendingTimer);
			pendingTimer = null;
		}
		if (pendingResolve) {
			pendingResolve();
			pendingResolve = null;
		}
		waitingForRegistrations = false;
	},
};

/** Svelte action — registers element with the FLIP store */
export function flipElement(node: HTMLElement, id: number | string) {
	flipStore.register(id, node);
	return {
		update(newId: number | string) {
			flipStore.unregister(id);
			id = newId;
			flipStore.register(id, node);
		},
		destroy() {
			flipStore.unregister(id);
		},
	};
}
