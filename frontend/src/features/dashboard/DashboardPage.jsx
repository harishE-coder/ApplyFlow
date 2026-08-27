import React, { Profiler } from 'react';
import { useAuth } from '@/features/auth/AuthContext';
import { AdminDashboard } from './AdminDashboard';
import { EmployeeDashboard } from './EmployeeDashboard';
import { ClientDashboard } from './ClientDashboard';
import { BrandedLoader } from '@/components/ui/BrandedLoader';

function onRenderDashboard(
  id,
  phase,
  actualDuration,
  baseDuration,
  startTime,
  commitTime
) {
  if (import.meta.env?.DEV) {
    if (actualDuration > 100) {
      console.warn(`[React Profiler Alert] ${id} (${phase}) took ${actualDuration.toFixed(2)}ms (exceeds 100ms target)`);
    } else {
      console.debug(`[React Profiler] ${id} (${phase}): ${actualDuration.toFixed(2)}ms (base: ${baseDuration.toFixed(2)}ms)`);
    }
  }
}

export function DashboardPage() {
  const { user, isLoading } = useAuth();

  if (isLoading || !user) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <BrandedLoader size="lg" label="Initializing ApplyFlow ATS..." />
      </div>
    );
  }

  let dashboardContent = null;
  if (user.role === 'admin' || user.role === 'sub_admin') {
    dashboardContent = <AdminDashboard />;
  } else if (user.role === 'client') {
    dashboardContent = <ClientDashboard />;
  } else {
    dashboardContent = <EmployeeDashboard />;
  }

  return (
    <Profiler id={`Dashboard-${user.role}`} onRender={onRenderDashboard}>
      {dashboardContent}
    </Profiler>
  );
}

export default DashboardPage;
