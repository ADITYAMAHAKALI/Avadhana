import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styles from './SignupPage.module.css';

export function SignupPage() {
  const { signup, isAuthenticating, authError, clearAuthError } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [location, setLocation] = useState('');
  const [password, setPassword] = useState('');

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    clearAuthError();
    try {
      await signup({ name, email, password, location });
      navigate('/dashboard', { replace: true });
    } catch {
      // authError is already set by the context; nothing else to do here.
    }
  }

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
            <Link to="/login" className={styles.tab}>
              Log in
            </Link>
            <div className={styles.tabActive}>Sign up</div>
          </div>

          <form className={styles.formBody} onSubmit={handleSubmit}>
            <h1 className={styles.heading}>Create your account</h1>
            <p className={styles.subheading}>Three slots. Choose deliberately.</p>

            <div className={styles.fields}>
              <div className={styles.field}>
                <div className={styles.fieldLabel}>Full name</div>
                <input
                  className={styles.input}
                  type="text"
                  placeholder="Your name"
                  autoComplete="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
              <div className={styles.field}>
                <div className={styles.fieldLabel}>Email</div>
                <input
                  className={styles.input}
                  type="email"
                  placeholder="you@example.com"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className={styles.field}>
                <div className={styles.fieldLabel}>Location</div>
                <input
                  className={styles.input}
                  type="text"
                  placeholder="City, state"
                  autoComplete="off"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  required
                />
              </div>
              <div className={styles.field}>
                <div className={styles.fieldLabel}>Password</div>
                <input
                  className={styles.input}
                  type="password"
                  placeholder="Create a password"
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            {authError && <div className={styles.errorBanner}>{authError}</div>}

            <button type="submit" className={styles.submitBtn} disabled={isAuthenticating}>
              {isAuthenticating ? 'Creating account…' : 'Create account'}
            </button>
            <div className={styles.finePrint}>
              By continuing you agree that abandoning a commitment before its 90-day minimum is recorded on your
              profile.
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
