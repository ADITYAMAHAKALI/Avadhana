import type { KeyboardEvent } from 'react';

/**
 * Keyboard handler for elements that use `role="button"` instead of a real
 * `<button>` (typically because they contain nested interactive children,
 * which would make a real `<button>` invalid HTML). Triggers `onActivate`
 * on Enter or Space, matching native button keyboard behavior, and prevents
 * the default scroll-on-Space.
 *
 * Usage: <div role="button" tabIndex={0} onClick={fn} onKeyDown={onActivateKeyDown(fn)} />
 */
export function onActivateKeyDown(onActivate: () => void) {
  return (event: KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ' || event.key === 'Spacebar') {
      event.preventDefault();
      onActivate();
    }
  };
}
