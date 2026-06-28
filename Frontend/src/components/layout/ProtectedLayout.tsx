import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../features/auth/context/AuthContext";

/**
 * Layout wrapper for authenticated pages.
 * Redirects to login if not authenticated.
 * Redirects PATIENT users with incomplete profiles to /complete-profile.
 */
export function ProtectedLayout() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="loading-screen">
        <span>Loading...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // If patient has not completed their profile, redirect to complete-profile
  if (
    user &&
    !user.profile_completed &&
    user.role === "PATIENT" &&
    location.pathname !== "/complete-profile"
  ) {
    return <Navigate to="/complete-profile" replace />;
  }

  // If profile IS completed, block access to /complete-profile
  if (user?.profile_completed && location.pathname === "/complete-profile") {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <main className="app-layout">
      <Outlet />
    </main>
  );
}
