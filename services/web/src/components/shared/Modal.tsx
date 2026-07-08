import type { ReactNode } from 'react';
import styles from './Modal.module.css';

export function Modal({ children, onClose }: { children: ReactNode; onClose?: () => void }) {
  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.panel} onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>
  );
}
