import type { Tier } from '../../types/domain';
import styles from './TierChip.module.css';

const TIER_CLASS: Record<Tier, string> = {
  S: styles.tierS,
  A: styles.tierA,
  B: styles.tierB,
  C: styles.tierC,
  D: styles.tierD,
};

export function TierChip({ tier }: { tier: Tier }) {
  return <span className={`${styles.chip} ${TIER_CLASS[tier]}`}>{tier}</span>;
}
