let _chromeFaded = $state(false);

export const transitionStore = {
	get chromeFaded() { return _chromeFaded; },
	fadeOut() { _chromeFaded = true; },
	fadeIn() { _chromeFaded = false; },
};
