import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "../../features/auth/context/AuthContext";
import { AuthLayout } from "../../components/layout/AuthLayout";
import { ProtectedLayout } from "../../components/layout/ProtectedLayout";
import { LoginForm } from "../../features/auth/components/LoginForm";
import { RegisterForm } from "../../features/auth/components/RegisterForm";
import { Dashboard } from "../../features/dashboard/components/Dashboard";
import { ChatPage } from "../../features/chat/components/ChatPage";
import { CompleteProfile } from "../../features/profile/components/CompleteProfile";
import { AdminDashboard } from "../../features/admin/components/AdminDashboard";

export function AppRouter() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public auth routes */}
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginForm />} />
            <Route path="/register" element={<RegisterForm />} />
          </Route>

          {/* Protected routes */}
          <Route element={<ProtectedLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/complete-profile" element={<CompleteProfile />} />
            <Route path="/admin" element={<AdminDashboard />} />
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
