import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import styles from './AppShell.module.css';

export function AppShell({ children }: { children: ReactNode }) {
  const [isNavOpen, setIsNavOpen] = useState(false);
  const location = useLocation();

  // Route changes already close the drawer via each NavLink's onClick, but
  // this also covers navigation triggered from within a page (e.g. a
  // problem card link), not just the Sidebar's own links.
  useEffect(() => {
    setIsNavOpen(false);
  }, [location.pathname]);

  return (
    <div className={styles.shell}>
      <Sidebar isOpen={isNavOpen} onClose={() => setIsNavOpen(false)} />
      <div className={styles.mainColumn}>
        <div className={styles.mobileTopBar}>
          <button
            type="button"
            className={styles.navToggle}
            aria-label="Open navigation menu"
            aria-expanded={isNavOpen}
            onClick={() => setIsNavOpen(true)}
          >
            <span className={styles.navToggleBar} />
            <span className={styles.navToggleBar} />
            <span className={styles.navToggleBar} />
          </button>
          <div className={styles.mobileWordmark}>Avadhana</div>
        </div>
        <main className={`${styles.main} scrolly`}>{children}</main>
      </div>
    </div>
  );
}
