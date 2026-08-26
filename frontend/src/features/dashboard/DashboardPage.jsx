import React from 'react';
import { useAuth } from '@/features/auth/AuthContext';
import { AdminDashboard } from './AdminDashboard';
import { EmployeeDashboard } from './EmployeeDashboard';
import { ClientDashboard } from './ClientDashboard';
import { BrandedLoader } from '@/components/ui/BrandedLoader';

export function DashboardPage() {
  const { user, isLoading } = useAuth();

  if (isLoading || !user) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <BrandedLoader size="lg" label="Initializing ApplyFlow ATS..." />
      </div>
    );
  }

  if (user.role === 'admin' || user.role === 'sub_admin') {
    return <AdminDashboard />;
  }

  if (user.role === 'client') {
    return <ClientDashboard />;
  }

  // Default: Employee / Recruiter Dashboard
  return <EmployeeDashboard />;
}

export default DashboardPage;
