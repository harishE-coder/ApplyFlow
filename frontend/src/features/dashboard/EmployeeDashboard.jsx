import React, { useState, useEffect, useCallback, useMemo, useRef, Suspense, lazy } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Upload,
  Briefcase,
  Target,
  Clock,
  CheckCircle2,
  TrendingUp,
  Sparkles,
  Layers,
  ChevronRight,
  RefreshCw,
  Plus,
  Play,
  Square,
  Filter,
  Check,
  Mail,
  Calendar,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { KPICard } from '@/components/ui/KPICard';
import { ProgressRing } from '@/components/ui/ProgressRing';
import { BrandedLoader } from '@/components/ui/BrandedLoader';
import { UploadDropzone } from '@/components/ui/UploadDropzone';
import { DateFilter } from '@/components/ui/DateFilter';
import { ChartSkeleton } from '@/components/ui/ChartSkeleton';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/features/auth/AuthContext';
import api from '@/services/api';
import { formatDate, formatRelativeTime, cn } from '@/utils/cn';

const EmployeeCharts = lazy(() => import('./charts/EmployeeCharts'));

export function EmployeeDashboard() {
  const { user, bootstrapData, consumeBootstrapDashboard } = useAuth();
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();

  const [initialData] = useState(() => {
    if (consumeBootstrapDashboard) {
      return consumeBootstrapDashboard();
    }
    return bootstrapData?.dashboard || null;
  });

  const [loading, setLoading] = useState(() => !initialData);
  const [data, setData] = useState(() => initialData?.dashboard || (initialData?.today_uploads !== undefined ? initialData : null));
  const [assignedClients, setAssignedClients] = useState(() => initialData?.assigned_clients || []);
  const [selectedClientId, setSelectedClientId] = useState('');
  const [dateRange, setDateRange] = useState('today');
  const [customDate, setCustomDate] = useState(new Date().toISOString().split('T')[0]);

  // Attendance & Live Timer State
  const [attendance, setAttendance] = useState(null);
  const [attendanceLoading, setAttendanceLoading] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Fetch employee dashboard data
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (selectedClientId) params.client_id = selectedClientId;
      if (dateRange === 'custom') {
        params.custom_date = customDate;
        params.date_range = customDate;
      } else if (dateRange) {
        params.date_range = dateRange;
      }

      const results = await Promise.allSettled([
        api.get('/dashboard/employee/home', { params }),
        api.get('/attendance/status'),
      ]);

      if (results[0].status === 'fulfilled') {
        const home = results[0].value.data;
        if (home?.dashboard) {
          setData(home.dashboard);
        } else if (home && typeof home === 'object') {
          setData(home);
        }
        if (Array.isArray(home?.assigned_clients)) {
          setAssignedClients(home.assigned_clients);
        } else if (Array.isArray(home?.dashboard?.assigned_clients)) {
          setAssignedClients(home.dashboard.assigned_clients);
        }
      } else {
        const status = results[0].reason?.response?.status;
        const detail = results[0].reason?.response?.data?.detail || results[0].reason?.message || 'Failed to load recruiter telemetry';
        console.error('Recruiter Dashboard Telemetry Error:', results[0].reason);
        if (status !== 401) {
          toastError('Dashboard Error', detail);
        }
      }

      if (results[1].status === 'fulfilled') {
        setAttendance(results[1].value.data);
      }
    } catch (err) {
      if (err.response?.status !== 401) {
        toastError('Dashboard Error', err.response?.data?.detail || err.message || 'Failed to load recruiter telemetry');
      }
    } finally {
      setLoading(false);
    }
  }, [selectedClientId, dateRange, customDate, toastError]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Real-time listener with stable ref to prevent re-attaching
  const fetchDataRef = useRef(fetchData);
  fetchDataRef.current = fetchData;

  useEffect(() => {
    const handleRefreshEvent = () => {
      fetchDataRef.current();
    };
    window.addEventListener('resume-uploaded', handleRefreshEvent);
    window.addEventListener('application-created', handleRefreshEvent);
    window.addEventListener('application-updated', handleRefreshEvent);
    window.addEventListener('email-processed', handleRefreshEvent);
    window.addEventListener('focus', handleRefreshEvent);

    return () => {
      window.removeEventListener('resume-uploaded', handleRefreshEvent);
      window.removeEventListener('application-created', handleRefreshEvent);
      window.removeEventListener('application-updated', handleRefreshEvent);
      window.removeEventListener('email-processed', handleRefreshEvent);
      window.removeEventListener('focus', handleRefreshEvent);
    };
  }, []);

  // Live timer for active attendance session
  useEffect(() => {
    let interval = null;
    if (attendance?.is_active && attendance?.check_in) {
      const startTime = new Date(attendance.check_in).getTime();
      const updateTimer = () => {
        const now = Date.now();
        const diff = Math.max(0, Math.floor((now - startTime) / 1000));
        setElapsedSeconds(diff);
      };
      updateTimer();
      interval = setInterval(updateTimer, 1000);
    } else {
      setElapsedSeconds(0);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [attendance]);

  const formatTimer = useCallback((seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }, []);

  // Toggle Attendance
  const handleToggleAttendance = useCallback(async () => {
    setAttendanceLoading(true);
    try {
      if (attendance?.is_active) {
        const res = await api.post('/attendance/check-out');
        setAttendance(res.data);
        success('Shift Completed', `Total working hours logged: ${res.data.total_hours || 0} hrs`);
      } else {
        const res = await api.post('/attendance/check-in');
        setAttendance(res.data);
        success('Shift Started', 'Daily attendance session activated.');
      }
    } catch (err) {
      toastError('Attendance error', err.response?.data?.detail || 'Failed to update attendance');
    } finally {
      setAttendanceLoading(false);
    }
  }, [attendance, success, toastError]);

  const handleDropResumes = useCallback((files) => {
    navigate('/upload', { state: { initialFiles: files, client_id: selectedClientId } });
  }, [navigate, selectedClientId]);

  const todayUploads = data?.today_uploads ?? 0;

  // Single Source of Truth: always use the backend-computed target_summary.
  const summary = useMemo(() => {
    return data?.target_summary ?? {
      target: 0,
      submitted: 0,
      remaining: 0,
      completion: 0,
    };
  }, [data?.target_summary]);

  const targetColor = useMemo(() => {
    const completion = summary.completion;
    if (completion >= 100) {
      return {
        hex: '#16A34A',
        badgeBg: 'bg-[#F0FDF4]',
        badgeText: 'text-[#16A34A]',
        badgeBorder: 'border-[#BBF7D0]',
        variant: 'success',
      };
    }
    if (completion > 50) {
      return {
        hex: '#F59E0B',
        badgeBg: 'bg-[#FFFBEB]',
        badgeText: 'text-[#D97706]',
        badgeBorder: 'border-[#FDE68A]',
        variant: 'orange',
      };
    }
    return {
      hex: '#EF4444',
      badgeBg: 'bg-[#FEF2F2]',
      badgeText: 'text-[#DC2626]',
      badgeBorder: 'border-[#FECACA]',
      variant: 'danger',
    };
  }, [summary.completion]);

  if (loading && !data) {
    return <BrandedLoader size="lg" label="Loading Recruiter Workspace..." />;
  }

  return (
    <div className="space-y-8">
      {/* Top Bar (Assigned Client filter & Date pills) */}
      <div className="bg-white p-5 rounded-2xl border border-[#E2E8F0] shadow-card space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-h2 font-extrabold text-[#081226] tracking-tight">
                Recruiter Workspace
              </h1>
              <span className="text-caption font-bold px-2.5 py-0.5 rounded-full bg-[#FFF7ED] text-[#FF8A00] border border-[#FFEDD5] flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5" />
                Active Recruiter
              </span>
            </div>
            <p className="text-small text-[#64748B] mt-0.5">
              Personalized candidate ingestion, client delivery queue, and target progress.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="md"
              icon={RefreshCw}
              onClick={fetchData}
              isLoading={loading}
              className="h-[44px]"
            />

            <Button
              variant="primary"
              size="md"
              icon={Plus}
              onClick={() => navigate('/upload')}
              className="h-[44px]"
            >
              Upload Resumes
            </Button>
          </div>
        </div>

        {/* Filters Row */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-4 pt-3 border-t border-[#F1F5F9] items-center">
          {/* Assigned Clients Selector */}
          <div className="sm:col-span-6">
            <label className="text-[11px] font-bold uppercase tracking-wider text-[#64748B] block mb-1">
              Assigned Service Client Filter
            </label>
            <select
              value={selectedClientId}
              onChange={(e) => setSelectedClientId(e.target.value)}
              className="w-full h-[44px] px-3.5 rounded-xl text-small font-medium bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] focus:outline-none focus:border-[#0D6EFD]"
            >
              <option value="">All Assigned Clients ({assignedClients.length})</option>
              {assignedClients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.company_name}
                </option>
              ))}
            </select>
          </div>

          {/* Global Date Filter */}
          <div className="sm:col-span-6">
            <label className="text-[11px] font-bold uppercase tracking-wider text-[#64748B] block mb-1">
              Global Date Filter
            </label>
            <DateFilter
              selectedPreset={dateRange}
              customDate={customDate}
              onFilterChange={({ preset, customDate: cDate }) => {
                setDateRange(preset);
                if (cDate) setCustomDate(cDate);
              }}
            />
          </div>
        </div>
      </div>

      {/* Employee Cards Strip (Today's Uploads, Applications Submitted, Daily Target, Completion %) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <KPICard
          title="Today's Uploads"
          value={todayUploads}
          subtitle="Resumes in pipeline"
          icon={Upload}
          variant="blue"
        />

        <KPICard
          title="Applications Submitted"
          value={summary.submitted}
          subtitle="Delivered to clients"
          icon={Briefcase}
          variant="default"
        />

        <KPICard
          title="Daily Target"
          value={`${summary.submitted} / ${summary.target}`}
          subtitle={`Target quota: ${summary.target} applications`}
          icon={Target}
          variant={targetColor.variant}
        />

        <KPICard
          title="Completion %"
          value={`${summary.completion}%`}
          subtitle={
            summary.completion >= 100
              ? '🎯 100% Target Met!'
              : `${summary.remaining} more submissions needed`
          }
          icon={TrendingUp}
          variant={targetColor.variant}
        />
      </div>

      {/* JOB OPENINGS TASK STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KPICard
          title="Active Job Openings"
          value={data?.active_jobs ?? 0}
          subtitle="Assigned recruitment tasks"
          icon={Briefcase}
          variant="blue"
        />
        <KPICard
          title="Completed Today"
          value={data?.completed_today_jobs ?? 0}
          subtitle="Tasks finished today"
          icon={CheckCircle2}
          variant="success"
        />
        <KPICard
          title="High Priority Jobs"
          value={data?.high_priority_jobs ?? 0}
          subtitle="Immediate submissions needed"
          icon={Target}
          variant="orange"
        />
      </div>

      {/* 70% Left / 30% Right Split Flagship Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* LEFT COLUMN: 70% (Col span 8) */}
        <div className="lg:col-span-8 space-y-8">
          {/* 1. Upload Hero (Biggest Component) */}
          <div className="bg-white rounded-3xl border border-[#E2E8F0] shadow-card p-6 sm:p-8">
            <div className="flex items-center justify-between gap-4 mb-6">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-[#0D6EFD] px-2.5 py-0.5 rounded-full bg-[#EFF6FF] border border-[#BFDBFE]">
                  Fast Ingestion Engine
                </span>
                <h3 className="text-h2 font-extrabold text-[#081226] tracking-tight mt-1.5">
                  Batch Resume Upload & Auto-Parse
                </h3>
                <p className="text-small text-[#64748B] mt-0.5">
                  Drop candidate PDF resumes here for automatic entity extraction and pre-commit duplicate checks.
                </p>
              </div>

              <Button
                variant="primary"
                size="md"
                icon={Upload}
                onClick={() => navigate('/upload')}
                className="hidden sm:inline-flex shrink-0"
              >
                Open Studio
              </Button>
            </div>

            <UploadDropzone onFilesSelected={handleDropResumes} />
          </div>

          {/* 2. Employee Charts (Lazy-Loaded Background Rendering) */}
          <Suspense fallback={<ChartSkeleton className="h-60" title="My 7-Day Performance Trends" />}>
            <EmployeeCharts weeklyTrend={data?.weekly_trend || []} />
          </Suspense>

          {/* 3. Active Job Requirements Matrix */}
          <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-card p-6">
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-[#F1F5F9]">
              <div>
                <h3 className="text-h3 font-bold text-[#081226]">Active Client Openings</h3>
                <p className="text-caption text-[#64748B] mt-0.5">
                  High-priority requirements with open candidate slots
                </p>
              </div>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/requirements')}
              >
                View all →
              </Button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {(data?.client_requirements || []).slice(0, 4).map((req, idx) => (
                <div
                  key={req.id || idx}
                  onClick={() => navigate(`/candidates?requirement_id=${req.id}`)}
                  className="p-4 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC]/50 hover:bg-[#EFF6FF]/40 hover:border-[#0D6EFD]/40 transition-all duration-120 cursor-pointer flex items-center justify-between group"
                >
                  <div className="min-w-0">
                    <p className="text-small font-bold text-[#081226] group-hover:text-[#0D6EFD] truncate">
                      {req.company} — {req.role}
                    </p>
                    <div className="flex items-center gap-2 mt-1 text-caption text-[#64748B]">
                      <span className="font-mono text-[11px] px-1.5 py-0.2 rounded bg-white border border-[#E2E8F0]">
                        {req.role_code}
                      </span>
                      <span>•</span>
                      <span>{req.resumes_count || 0} resumes</span>
                    </div>
                  </div>

                  <ChevronRight className="w-4 h-4 text-[#94A3B8] group-hover:text-[#0D6EFD] shrink-0 ml-2" />
                </div>
              ))}
            </div>
          </div>

          {/* 4. AI Email Intake & Candidate Interview Rounds */}
          <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-card p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#F1F5F9]">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#2563EB] px-2.5 py-0.5 rounded-full bg-[#EFF6FF] border border-[#BFDBFE]">
                    Groq AI Inbox
                  </span>
                  <h3 className="text-h3 font-bold text-[#081226]">AI Email Intake Telemetry</h3>
                </div>
                <p className="text-caption text-[#64748B] mt-0.5">
                  Recruiter positive response emails processed and upcoming interview rounds
                </p>
              </div>

              <Button
                variant="outline"
                size="sm"
                icon={Mail}
                onClick={() => navigate('/applications')}
                className="h-[36px] text-xs font-bold text-[#2563EB] border-[#BFDBFE] hover:bg-[#EFF6FF]"
              >
                Open Applications →
              </Button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-center">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748B]">Emails Processed</p>
                <p className="text-h2 font-black text-[#081226] mt-0.5">18</p>
              </div>
              <div className="p-3.5 rounded-xl bg-[#EFF6FF] border border-[#BFDBFE] text-center">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#2563EB]">New Applications</p>
                <p className="text-h2 font-black text-[#2563EB] mt-0.5">12</p>
              </div>
              <div className="p-3.5 rounded-xl bg-[#FFF7ED] border border-[#FFEDD5] text-center">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#F97316]">Pending Review</p>
                <p className="text-h2 font-black text-[#F97316] mt-0.5">0</p>
              </div>
              <div className="p-3.5 rounded-xl bg-[#F0FDF4] border border-[#BBF7D0] text-center">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#16A34A]">Upcoming Interviews</p>
                <p className="text-h2 font-black text-[#16A34A] mt-0.5">5</p>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: 30% (Col span 4) */}
        <div className="lg:col-span-4 space-y-6">
          {/* 1. Target Progress Ring Card (Locked Rule: Applications Submitted vs Target) */}
          <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-card p-6 text-center">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#F1F5F9]">
              <h4 className="text-small font-bold uppercase tracking-wider text-[#64748B]">
                Daily Target Quota
              </h4>
              <span className={cn('text-[11px] font-bold px-2 py-0.5 rounded-full border', targetColor.badgeBg, targetColor.badgeText, targetColor.badgeBorder)}>
                {summary.completion}%
              </span>
            </div>

            <div className="my-3 flex justify-center">
              <ProgressRing
                progress={summary.completion}
                size={130}
                strokeWidth={12}
                color={targetColor.hex}
                label="Target Met"
                valueText={`${summary.submitted}/${summary.target}`}
              />
            </div>

            <div className="mt-3 space-y-1">
              <p className="text-small font-bold text-[#081226]">
                Target: <span className="text-[#081226]">{summary.target}</span> • Submitted: <span className="text-[#0D6EFD]">{summary.submitted}</span>
              </p>
              <p className="text-caption text-[#64748B]">
                Remaining: <span className="font-bold" style={{ color: targetColor.hex }}>{summary.remaining}</span> • Completion: <span className="font-bold" style={{ color: targetColor.hex }}>{summary.completion}%</span>
              </p>
            </div>

            <div className="mt-5 pt-4 border-t border-[#F1F5F9]">
              <Button
                variant="primary"
                size="md"
                onClick={() => navigate('/upload')}
                className="w-full"
              >
                Upload Resumes to Progress Target →
              </Button>
            </div>
          </div>

          {/* 2. Attendance Widget with Live Timer */}
          <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-card p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#F1F5F9]">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-[#0D6EFD]" />
                <h4 className="text-small font-bold uppercase tracking-wider text-[#64748B]">
                  Shift Attendance
                </h4>
              </div>

              <span
                className={cn(
                  'text-caption font-bold px-2 py-0.5 rounded-full flex items-center gap-1.5',
                  attendance?.is_active
                    ? 'bg-[#F0FDF4] text-[#16A34A] border border-[#BBF7D0]'
                    : 'bg-[#F1F5F9] text-[#64748B] border border-[#E2E8F0]'
                )}
              >
                <span
                  className={cn(
                    'w-2 h-2 rounded-full',
                    attendance?.is_active ? 'bg-[#16A34A] animate-pulse' : 'bg-[#94A3B8]'
                  )}
                />
                {attendance?.is_active ? 'Checked In' : 'Checked Out'}
              </span>
            </div>

            {/* Live Timer Display */}
            {attendance?.is_active ? (
              <div className="p-4 rounded-xl bg-[#081226] text-white text-center space-y-1">
                <p className="text-caption font-bold uppercase tracking-widest text-[#94A3B8]">
                  Active Shift Duration
                </p>
                <p className="font-mono text-display font-bold text-[#FF8A00] tracking-wider">
                  {formatTimer(elapsedSeconds)}
                </p>
                <p className="text-caption text-[#94A3B8]">
                  Started at {attendance.check_in ? formatDate(attendance.check_in) : 'Today'}
                </p>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] text-center text-[#64748B] text-small">
                {attendance?.check_out ? (
                  <p>
                    Completed shift today. Logged{' '}
                    <span className="font-bold text-[#081226]">{attendance.total_hours} hrs</span>
                  </p>
                ) : (
                  <p>No active shift. Click below to start your workday.</p>
                )}
              </div>
            )}

            <Button
              variant={attendance?.is_active ? 'outline' : 'primary'}
              size="md"
              icon={attendance?.is_active ? Square : Play}
              isLoading={attendanceLoading}
              onClick={handleToggleAttendance}
              className="w-full h-[44px]"
            >
              {attendance?.is_active ? 'End Shift Session' : 'Start Daily Shift (Check In)'}
            </Button>
          </div>

          {/* 3. Recent Activity Feed */}
          <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-card p-6">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#F1F5F9]">
              <h4 className="text-small font-bold uppercase tracking-wider text-[#64748B]">
                Recent Activity
              </h4>
              <span className="text-caption text-[#64748B]">Personal log</span>
            </div>

            <div className="space-y-3">
              {(data?.recent_activity || [
                { id: '1', action: 'Uploaded 35 resumes', description: 'Batch ingestion for ABC Staffing', created_at: new Date().toISOString() },
                { id: '2', action: 'Submitted Rahul to TCS Java', description: 'Candidate delivered to client pipeline', created_at: new Date().toISOString() },
                { id: '3', action: 'Target Milestone', description: '50% of daily target reached', created_at: new Date().toISOString() },
              ]).map((act, idx) => (
                <div key={act.id || idx} className="p-3 rounded-xl bg-[#F8FAFC] border border-[#F1F5F9] flex items-start gap-2.5">
                  <div className="w-2 h-2 rounded-full bg-[#0D6EFD] mt-1.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-small font-bold text-[#081226] leading-tight">{act.action}</p>
                    <p className="text-caption text-[#64748B] mt-0.5">{act.description}</p>
                    <p className="text-[10px] text-[#94A3B8] mt-1">{formatRelativeTime(act.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default EmployeeDashboard;
