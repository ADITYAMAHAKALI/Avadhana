/**
 * Tiny pub/sub so the sidebar's FocusSlotsWidget (a single persistent
 * instance, mounted once by AppShell — it doesn't remount on route changes)
 * can be told to refetch after a commitment is created elsewhere in the
 * tree (CommitModal, several routes away). Deliberately not React context:
 * this is a one-shot "please refetch" signal, not shared state.
 */
type Listener = () => void;

const listeners = new Set<Listener>();

export function subscribeFocusSlotsRefresh(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function notifyFocusSlotsChanged(): void {
  for (const listener of listeners) listener();
}
