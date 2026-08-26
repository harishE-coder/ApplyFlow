import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '@/features/auth/AuthContext';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { ToastProvider } from '@/components/ui/Toast';
import { AppLayout } from '@/components/layout/AppLayout';

// Pages
import { LoginPage } from '@/features/auth/LoginPage';
import { DashboardPage } from '@/features/dashboard/DashboardPage';
import { ResumesPage } from '@/features/resumes/ResumesPage';
import { UploadPage } from '@/features/resumes/UploadPage';
import { AIResponseInboxPage } from '@/features/applications/AIResponseInboxPage';
import { RequirementsPage } from '@/features/requirements/RequirementsPage';
import { ClientsPage } from '@/features/clients/ClientsPage';
import { RecruitersPage } from '@/features/dashboard/RecruitersPage';
import { SubAdminsPage } from '@/features/subadmins/SubAdminsPage';
import { TargetsPage } from '@/features/dashboard/TargetsPage';
import { ReportsPage } from '@/features/reports/ReportsPage';
import { NotificationsPage } from '@/features/notifications/NotificationsPage';
import { ChatPage } from '@/features/chat/ChatPage';

function ProtectedRoute({ children, allowedRoles }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen w-full flex flex-col items-center justify-center bg-[#F6F8FB]">
        <div className="w-12 h-12 rounded-2xl bg-[#081226] flex items-center justify-center shadow-xl animate-pulse">
          <div className="w-6 h-6 border-3 border-[#2563EB] border-t-transparent rounded-full animate-spin" />
        </div>
        <p className="mt-4 text-small font-semibold text-[#081226]">Loading ApplyFlow ATS...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function PublicRoute({ children }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ToastProvider>
          <AuthProvider>
            <Routes>
              {/* Public Login Route */}
              <Route
                path="/login"
                element={
                  <PublicRoute>
                    <LoginPage />
                  </PublicRoute>
                }
              />

              {/* Protected ATS Workspace Routes */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route
                  path="upload"
                  element={
                    <ProtectedRoute allowedRoles={['employee']}>
                      <UploadPage />
                    </ProtectedRoute>
                  }
                />
                <Route path="candidates" element={<ResumesPage />} />
                <Route path="applications" element={<AIResponseInboxPage />} />
                <Route path="ai-inbox" element={<AIResponseInboxPage />} />
                <Route path="chats" element={<ChatPage />} />
                <Route path="requirements" element={<RequirementsPage />} />
                <Route path="clients" element={<ClientsPage />} />
                <Route
                  path="sub-admins"
                  element={
                    <ProtectedRoute allowedRoles={['admin']}>
                      <SubAdminsPage />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="recruiters"
                  element={
                    <ProtectedRoute allowedRoles={['admin', 'sub_admin']}>
                      <RecruitersPage />
                    </ProtectedRoute>
                  }
                />
                <Route path="targets" element={<TargetsPage />} />
                <Route path="reports" element={<ReportsPage />} />
                <Route path="notifications" element={<NotificationsPage />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Route>
            </Routes>
          </AuthProvider>
        </ToastProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
