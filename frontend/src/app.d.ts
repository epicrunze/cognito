// See https://svelte.dev/docs/kit/types#app.d.ts

interface ViewTransition {
	finished: Promise<void>;
	ready: Promise<void>;
	updateCallbackDone: Promise<void>;
}

interface Document {
	startViewTransition?(callback: () => Promise<void> | void): ViewTransition;
}
