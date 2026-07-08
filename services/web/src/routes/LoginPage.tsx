import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styles from './LoginPage.module.css';

export function LoginPage() {
  const { login } = useAuth();

  return (
    <div className={styles.page}>
      <div className={styles.brandPanel}>
        <div className={styles.brandRow}>
          <div className={styles.mark}>अवधान</div>
          <div className={styles.wordmark}>Avadhana</div>
        </div>
        <div className={styles.tagline}>Time is the one currency you can never earn back.</div>
        <div className={styles.bullets}>
          <div className={styles.bullet}>
            <span className={styles.dot} />
            <span>At most 3 focus slots, ever.</span>
          </div>
          <div className={styles.bullet}>
            <span className={styles.dot} />
            <span>A 90-day minimum commitment lock — not a deadline to finish, just the earliest checkpoint.</span>
          </div>
          <div className={styles.bullet}>
            <span className={styles.dot} />
            <span>Only committed members get a voice.</span>
          </div>
        </div>
      </div>

      <div className={styles.formPanel}>
        <div className={styles.formCol}>
          <div className={styles.tabs}>
            <div className={styles.tabActive}>Log in</div>
            <Link to="/signup" className={styles.tab}>
              Sign up
            </Link>
          </div>

          <div className={styles.formBody}>
            <h1 className={styles.heading}>Welcome back</h1>
            <p className={styles.subheading}>Your slots and clocks are exactly as you left them.</p>

            <div className={styles.fields}>
              <div className={styles.field}>
                <div className={styles.fieldLabel}>Email</div>
                <input
                  className={styles.input}
                  type="email"
                  defaultValue="ravi.menon@example.com"
                  autoComplete="off"
                />
              </div>
              <div className={styles.field}>
                <div className={styles.fieldLabel}>Password</div>
                <input className={styles.input} type="password" defaultValue="password123" autoComplete="off" />
              </div>
            </div>

            <button className={styles.submitBtn} onClick={() => login()}>
              Log in
            </button>
            <div className={styles.forgot}>Forgot password?</div>
          </div>
        </div>
      </div>
    </div>
  );
}
