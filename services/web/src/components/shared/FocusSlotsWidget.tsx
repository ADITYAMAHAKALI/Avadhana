import styles from './FocusSlotsWidget.module.css';

export function FocusSlotsWidget({ used, total }: { used: number; total: number }) {
  const slots = Array.from({ length: total }, (_, i) => i < used);
  const openCount = total - used;

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={styles.label}>Focus slots</span>
        <span className={styles.count}>
          {used} / {total}
        </span>
      </div>
      <div className={styles.slots}>
        {slots.map((occupied, i) =>
          occupied ? (
            <div key={i} className={styles.slotFilled}>
              <span className={styles.slotDot} />
            </div>
          ) : (
            <div key={i} className={styles.slotOpen}>
              +
            </div>
          ),
        )}
      </div>
      <div className={styles.hint}>
        {openCount > 0
          ? `${openCount} slot${openCount > 1 ? 's' : ''} open. Spending it locks you in for a `
          : 'All three slots are spent. '}
        {openCount > 0 && <em>minimum</em>}
        {openCount > 0 ? ' of 90 days — not a deadline to finish, just the earliest you can step back.' : 'No fourth slot exists.'}
      </div>
    </div>
  );
}
