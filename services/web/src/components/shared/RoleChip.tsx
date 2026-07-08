import type { Role } from '../../types/domain';
import styles from './RoleChip.module.css';

const ROLE_LABEL: Record<Role, string> = {
  thinker: 'Thinker',
  actor: 'Actor',
  backer: 'Backer',
};

const ROLE_CLASS: Record<Role, string> = {
  thinker: styles.thinker,
  actor: styles.actor,
  backer: styles.backer,
};

export function RoleChip({ role, prefix }: { role: Role; prefix?: string }) {
  return (
    <span className={`${styles.chip} ${ROLE_CLASS[role]}`}>
      <span className={styles.dot} />
      {prefix ? `${prefix}: ` : ''}
      {ROLE_LABEL[role]}
    </span>
  );
}
