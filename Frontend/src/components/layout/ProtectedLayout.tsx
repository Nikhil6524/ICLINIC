import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../../features/auth/context/AuthContext";

export function ProtectedLayout() {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div className="loading-screen"><span>Loading...</span></div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // ADMIN/FRONT_DESK users go to admin dashboard
  if (
    user &&
    (user.role === "ADMIN" || user.role === "FRONT_DESK") &&
    location.pathname === "/dashboard"
  ) {
    return <Navigate to="/admin" replace />;
  }

  // PATIENT: incomplete profile → force complete-profile
  if (
    user &&
    !user.profile_completed &&
    user.role === "PATIENT" &&
    location.pathname !== "/complete-profile"
  ) {
    return <Navigate to="/complete-profile" replace />;
  }

  // Completed profile → block /complete-profile
  if (user?.profile_completed && location.pathname === "/complete-profile") {
    return <Navigate to="/dashboard" replace />;
  }

  // Block non-admin from /admin
  if (
    location.pathname === "/admin" &&
    user?.role !== "ADMIN" &&
    user?.role !== "FRONT_DESK"
  ) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <main className="app-layout">
      <Outlet />
    </main>
  );
}
