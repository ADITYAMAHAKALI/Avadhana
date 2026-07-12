import { useCallback, useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { currentUserPort } from '../../data';
import { subscribeFocusSlotsRefresh } from '../../data/focusSlotsRefresh';
import type { CommittedProblemSummary, User } from '../../types/domain';
import { useAuth } from '../../context/AuthContext';
import { FocusSlotsWidget } from '../shared/FocusSlotsWidget';
import styles from './Sidebar.module.css';

const ROLE_LABEL: Record<CommittedProblemSummary['role'], string> = {
  thinker: 'Thinker',
  actor: 'Actor',
  backer: 'Backer',
};

// Note: "Problem workspace", "Problem graph", and "Coordinator & moderation"
// are intentionally not fixed sidebar links — they're per-problem pages
// (routes are /problems/:problemId, /graph/:problemId, /coordinator/:problemId
// in App.tsx) with no single sensible destination from a persistent nav
// item. Real navigation into a specific problem happens from "Your focus"
// (committed problems, DashboardPage) or "Discover problems", and from
// within a problem's own page (ProblemPage links to that problem's Graph
// and Coordinator views). See issue #74.
const NAV_ITEMS = [
  { to: '/dashboard', label: 'Your focus' },
  { to: '/discover', label: 'Discover problems' },
  { to: '/problems/new', label: '+ Propose a problem' },
  { to: '/profile', label: 'Your record' },
  { to: '/marketplace', label: 'Marketplace' },
];

interface SidebarProps {
  /** Whether the mobile drawer is open. Ignored above the tablet breakpoint, where the sidebar is always visible. */
  isOpen: boolean;
  /** Closes the mobile drawer — called on nav click, Escape, or backdrop click. */
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const { logout } = useAuth();
  const [user, setUser] = useState<User | null>(null);
  const [slots, setSlots] = useState({ used: 0, total: 3 });
  const [committed, setCommitted] = useState<CommittedProblemSummary[]>([]);

  const refresh = useCallback(() => {
    currentUserPort.getCurrentUser().then(setUser);
    currentUserPort.getFocusSlotCount().then(setSlots);
    currentUserPort.getCommittedProblems().then(setCommitted);
  }, []);

  useEffect(() => {
    refresh();
    return subscribeFocusSlotsRefresh(refresh);
  }, [refresh]);

  // Escape-to-close only matters for the mobile drawer; a no-op listener
  // above the tablet breakpoint (where isOpen is never toggled) is harmless
  // but skipped anyway to avoid a stray global listener.
  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  return (
    <>
      {isOpen && <div className={styles.backdrop} onClick={onClose} aria-hidden="true" />}
      <aside className={`${styles.sidebar} ${isOpen ? styles.sidebarOpen : ''}`}>
        <div className={styles.brandRow}>
          <div className={styles.mark}>अवधान</div>
          <div className={styles.wordmark}>Avadhana</div>
        </div>
        <div className={styles.tagline}>Time is the point</div>

        <nav className={styles.nav}>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onClose}
              className={({ isActive }) => `${styles.navbtn} ${isActive ? styles.navbtnActive : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <FocusSlotsWidget used={slots.used} total={slots.total} />

        {user && (
          <div className={styles.userRow}>
            <div className={styles.avatar} style={{ background: user.avatarColor }}>
              {user.initials}
            </div>
            <div className={styles.userInfo}>
              <div className={styles.userName}>{user.name}</div>
              <div className={styles.userMeta}>
                rep {user.reputation}
                {committed[0] ? ` · ${ROLE_LABEL[committed[0].role]}` : ''}
              </div>
            </div>
            <div className={styles.signOut} onClick={logout}>
              Sign out
            </div>
          </div>
        )}
      </aside>
    </>
  );
}
