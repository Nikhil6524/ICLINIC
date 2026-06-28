import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../features/auth/context/AuthContext";

/**
 * Layout wrapper for auth pages (login/register).
 * Redirects to dashboard if already authenticated (and profile is complete).
 * Redirects to complete-profile if authenticated but profile is incomplete.
 */
export function AuthLayout() {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="loading-screen">
        <span>Loading...</span>
      </div>
    );
  }

  if (isAuthenticated) {
    // If patient hasn't completed profile, send to profile form
    if (user && !user.profile_completed && user.role === "PATIENT") {
      return <Navigate to="/complete-profile" replace />;
    }
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <main className="auth-layout">
      <div className="auth-container">
        <Outlet />
      </div>
    </main>
  );
}
