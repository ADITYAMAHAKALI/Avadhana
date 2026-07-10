import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import styles from './Modal.module.css';

interface ModalProps {
  children: ReactNode;
  onClose?: () => void;
  /** Id of the element (usually the modal's heading) that labels this dialog for assistive tech, wired to aria-labelledby. */
  titleId?: string;
}

export function Modal({ children, onClose, titleId }: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  // Remember whatever had focus before the modal opened (the button that
  // triggered it, e.g. "Commit a slot" / "Review") so we can restore focus
  // there once the modal closes — otherwise keyboard/screen-reader focus is
  // silently dropped back to <body>.
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previouslyFocusedRef.current = document.activeElement as HTMLElement | null;

    // Minimal focus-management: move focus into the dialog on mount (to the
    // first focusable element if one exists, else the panel itself so
    // screen readers still announce entering the dialog). This is not a
    // full focus trap (Tab can still escape to the rest of the page) — see
    // issue #75 for scope notes.
    const panel = panelRef.current;
    const firstFocusable = panel?.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    (firstFocusable ?? panel)?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose?.();
      }
    }
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocusedRef.current?.focus();
    };
    // Intentionally mount/unmount-only: this sets up focus management once
    // when the dialog appears and tears it down once when it's removed.
    // Both call sites (ProblemPage, DashboardPage) only ever mount one Modal
    // instance per open/close cycle, so a stale onClose closure isn't a
    // practical concern here.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div
        className={styles.panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        ref={panelRef}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}
