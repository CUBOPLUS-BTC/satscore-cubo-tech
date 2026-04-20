import { animate, stagger, inView, scroll, spring } from 'motion';
import type { AnimationOptions } from 'motion';

/**
 * Svelte action: animate an element on mount.
 *
 * Usage: <div use:animateIn={{ y: [20, 0], opacity: [0, 1] }}>
 */
export function animateIn(
	node: HTMLElement,
	params: {
		y?: [number, number];
		x?: [number, number];
		opacity?: [number, number];
		scale?: [number, number];
		duration?: number;
		delay?: number;
		ease?: AnimationOptions['ease'];
	} = {}
) {
	const {
		y,
		x,
		opacity = [0, 1],
		scale,
		duration = 0.5,
		delay = 0,
		ease = [0.25, 0.1, 0.25, 1],
	} = params;

	const keyframes: Record<string, [number, number]> = {};
	if (opacity) keyframes.opacity = opacity;
	if (y) keyframes.y = y;
	if (x) keyframes.x = x;
	if (scale) keyframes.scale = scale;

	animate(node, keyframes as any, { duration, delay, ease });
}

/**
 * Svelte action: reveal element when it enters viewport.
 *
 * Usage: <div use:inViewReveal>
 */
export function inViewReveal(
	node: HTMLElement,
	params: {
		y?: number;
		duration?: number;
		once?: boolean;
		margin?: string;
	} = {}
) {
	const { y = 30, duration = 0.6, once = true, margin = '-60px' } = params;

	node.style.opacity = '0';
	node.style.transform = `translateY(${y}px)`;

	const stop = inView(
		node,
		() => {
			animate(
				node,
				{ opacity: [0, 1], y: [y, 0] } as any,
				{ duration, ease: [0.25, 0.1, 0.25, 1] }
			);
		},
		{ margin: margin as any, amount: 0.2 }
	);

	return {
		destroy() {
			stop();
		},
	};
}

/**
 * Svelte action: stagger children on mount.
 *
 * Usage: <div use:staggerChildren={{ selector: ':scope > *' }}>
 */
export function staggerChildren(
	node: HTMLElement,
	params: {
		selector?: string;
		y?: number;
		duration?: number;
		delay?: number;
		staggerDelay?: number;
	} = {}
) {
	const {
		selector = ':scope > *',
		y = 20,
		duration = 0.4,
		delay = 0,
		staggerDelay = 0.06,
	} = params;

	const children = node.querySelectorAll(selector);
	if (children.length === 0) return;

	children.forEach((child) => {
		(child as HTMLElement).style.opacity = '0';
	});

	animate(
		children as unknown as Element[],
		{ opacity: [0, 1], y: [y, 0] } as any,
		{
			duration,
			delay: stagger(staggerDelay, { startDelay: delay }),
			ease: [0.25, 0.1, 0.25, 1],
		}
	);
}

/**
 * Svelte action: reveal stagger children when they enter viewport.
 *
 * Usage: <div use:inViewStagger>
 */
export function inViewStagger(
	node: HTMLElement,
	params: {
		selector?: string;
		y?: number;
		duration?: number;
		staggerDelay?: number;
		margin?: string;
	} = {}
) {
	const {
		selector = ':scope > *',
		y = 24,
		duration = 0.45,
		staggerDelay = 0.07,
		margin = '-40px',
	} = params;

	const children = node.querySelectorAll(selector);
	children.forEach((child) => {
		(child as HTMLElement).style.opacity = '0';
	});

	const stop = inView(
		node,
		() => {
			animate(
				children as unknown as Element[],
				{ opacity: [0, 1], y: [y, 0] } as any,
				{
					duration,
					delay: stagger(staggerDelay),
					ease: [0.25, 0.1, 0.25, 1],
				}
			);
		},
		{ margin: margin as any, amount: 0.1 }
	);

	return {
		destroy() {
			stop();
		},
	};
}

/**
 * Svelte action: spring-based hover scale.
 *
 * Usage: <div use:springHover={{ scale: 1.03 }}>
 */
export function springHover(
	node: HTMLElement,
	params: { scale?: number; stiffness?: number; damping?: number } = {}
) {
	const { scale: targetScale = 1.03, stiffness = 300, damping = 20 } = params;

	function onEnter() {
		animate(node, { scale: targetScale }, { type: spring, stiffness, damping } as any);
	}

	function onLeave() {
		animate(node, { scale: 1 }, { type: spring, stiffness, damping } as any);
	}

	node.addEventListener('mouseenter', onEnter);
	node.addEventListener('mouseleave', onLeave);

	return {
		destroy() {
			node.removeEventListener('mouseenter', onEnter);
			node.removeEventListener('mouseleave', onLeave);
		},
	};
}

/**
 * Svelte action: press feedback (scale down on press, spring back on release).
 *
 * Usage: <button use:pressScale>
 */
export function pressScale(
	node: HTMLElement,
	params: { scale?: number } = {}
) {
	const { scale: pressedScale = 0.96 } = params;

	function onDown() {
		animate(node, { scale: pressedScale }, { duration: 0.1 });
	}

	function onUp() {
		animate(node, { scale: 1 }, { type: spring, stiffness: 400, damping: 15 } as any);
	}

	node.addEventListener('pointerdown', onDown);
	node.addEventListener('pointerup', onUp);
	node.addEventListener('pointerleave', onUp);

	return {
		destroy() {
			node.removeEventListener('pointerdown', onDown);
			node.removeEventListener('pointerup', onUp);
			node.removeEventListener('pointerleave', onUp);
		},
	};
}

export { animate, stagger, inView, scroll, spring };
