import { Navigate, Route, Routes } from 'react-router-dom';
import type { ReactNode } from 'react';
import { AppShell } from './components/layout/AppShell';
import { useAuth } from './context/AuthContext';
import { CoordinatorPage } from './routes/CoordinatorPage';
import { DashboardPage } from './routes/DashboardPage';
import { DiscoverPage } from './routes/DiscoverPage';
import { GraphPage } from './routes/GraphPage';
import { LoginPage } from './routes/LoginPage';
import { NewProblemPage } from './routes/NewProblemPage';
import { ProblemPage } from './routes/ProblemPage';
import { ProfilePage } from './routes/ProfilePage';
import { SignupPage } from './routes/SignupPage';

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
      <Route path="/signup" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <SignupPage />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <AppShell>
              <Routes>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/discover" element={<DiscoverPage />} />
                <Route path="/problems/new" element={<NewProblemPage />} />
                <Route path="/problems/:problemId" element={<ProblemPage />} />
                <Route path="/graph/:problemId" element={<GraphPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/coordinator/:problemId" element={<CoordinatorPage />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </AppShell>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
