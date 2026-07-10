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

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Your focus' },
  { to: '/discover', label: 'Discover problems' },
  { to: '/problems/new', label: '+ Propose a problem' },
  { to: '/problems/p-groundwater', label: 'Problem workspace' },
  { to: '/graph/p-groundwater', label: 'Problem graph' },
  { to: '/profile', label: 'Your record' },
  { to: '/coordinator/p-groundwater', label: 'Coordinator & moderation' },
  { to: '/marketplace', label: 'Marketplace' },
];

export function Sidebar() {
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

  return (
    <aside className={styles.sidebar}>
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
  );
}
