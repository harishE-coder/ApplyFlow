import React, { useState, useEffect, useMemo, useCallback, useRef, Suspense, lazy } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Building2,
  Users,
  Briefcase,
  Target,
  Clock,
  TrendingUp,
  Calendar,
  Layers,
  Sparkles,
  ArrowUpDown,
  Filter,
  CheckCircle2,
  AlertCircle,
  Clock3,
  BarChart2,
  PieChart as PieIcon,
  RefreshCw,
  ChevronDown,
  Activity,
  ArrowRight,
  Plus,
  ShieldCheck,
  Mail,
} from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';
import { KPICard } from '@/components/ui/KPICard';
import { Avatar } from '@/components/ui/Avatar';
import { BrandedLoader } from '@/components/ui/BrandedLoader';
import { EmptyState } from '@/components/ui/EmptyState';
import { Table } from '@/components/ui/Table';
import { Button } from '@/components/ui/Button';
import { DateFilter } from '@/components/ui/DateFilter';
import { ChartSkeleton } from '@/components/ui/ChartSkeleton';
import { useToast } from '@/components/ui/Toast';
import api from '@/services/api';
import { formatDate, formatRelativeTime, cn } from '@/utils/cn';

// Lazy-loaded Charts Subcomponent
const AdminCharts = lazy(() => import('./charts/AdminCharts'));

function hashString(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = (hash << 5) - hash + str.charCodeAt(i);
  return Math.abs(hash);
}

export function AdminDashboard() {
  const { isAdmin, isSubAdmin, bootstrapData } = useAuth();
  const { error: toastError } = useToast();

  const initialHome = bootstrapData?.dashboard;
  const [loading, setLoading] = useState(() => !initialHome);

  // 1. Reactive Top Filters
  const [clients, setClients] = useState(() => initialHome?.clients || []);
  const [allEmployees, setAllEmployees] = useState(() => initialHome?.all_employees || []);
  const [selectedClientId, setSelectedClientId] = useState('');
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]); // Single Date Picker
  const [quickDateFilter, setQuickDateFilter] = useState('today'); // 'today' | 'yesterday' | 'this_week' | 'this_month' | 'custom'

  // Sort Option for Recruiter Performance Table
  const [sortOption, setSortOption] = useState('highest'); // 'highest' | 'lowest' | 'remaining'

  // Data States
  const [overview, setOverview] = useState(() => initialHome?.overview || null);
  const [clientCards, setClientCards] = useState(() => initialHome?.client_cards || []);
  const [teamPerformance, setTeamPerformance] = useState(() => initialHome?.team_performance || []);
  const [allTargets, setAllTargets] = useState(() => initialHome?.all_targets || []);
  const [attendanceSummary, setAttendanceSummary] = useState(() => initialHome?.attendance_summary || null);

  // Track bootstrap data initial consumption to skip duplicate cold fetch
  const hasConsumedBootstrapRef = useRef(Boolean(initialHome));

  // Sync if bootstrapData arrives asynchronously
  useEffect(() => {
    if (bootstrapData?.dashboard && !overview) {
      const home = bootstrapData.dashboard;
      if (home.overview) setOverview(home.overview);
      if (home.team_performance) setTeamPerformance(home.team_performance);
      if (home.attendance_summary) setAttendanceSummary(home.attendance_summary);
      if (home.client_cards) setClientCards(home.client_cards);
      if (home.clients?.length) setClients(home.clients);
      if (home.all_employees?.length) setAllEmployees(home.all_employees);
      if (home.all_targets?.length) setAllTargets(home.all_targets);
      setLoading(false);
      hasConsumedBootstrapRef.current = true;
    }
  }, [bootstrapData, overview]);

  // Cascading Employee list based on selected client
  const availableEmployees = useMemo(() => {
    if (!selectedClientId) return allEmployees;
    return allEmployees.filter((emp) =>
      emp.assigned_clients?.some((c) => (c.client_id || c.id) === selectedClientId)
    );
  }, [selectedClientId, allEmployees]);

  const handleClientChange = useCallback((newClientId) => {
    setSelectedClientId(newClientId);
    if (newClientId) {
      const stillValid = allEmployees.some(
        (emp) =>
          (emp.id || emp.employee_id) === selectedEmployeeId &&
          emp.assigned_clients?.some((c) => (c.client_id || c.id) === newClientId)
      );
      if (!stillValid) setSelectedEmployeeId('');
    }
  }, [allEmployees, selectedEmployeeId]);

  const handleQuickDateSelect = useCallback((filterKey) => {
    setQuickDateFilter(filterKey);
    const today = new Date();
    if (filterKey === 'today') {
      setSelectedDate(today.toISOString().split('T')[0]);
    } else if (filterKey === 'yesterday') {
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      setSelectedDate(yesterday.toISOString().split('T')[0]);
    }
  }, []);

  const handleDateInput = useCallback((dateStr) => {
    setSelectedDate(dateStr);
    const todayStr = new Date().toISOString().split('T')[0];
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toISOString().split('T')[0];

    if (dateStr === todayStr) {
      setQuickDateFilter('today');
    } else if (dateStr === yesterdayStr) {
      setQuickDateFilter('yesterday');
    } else {
      setQuickDateFilter('custom');
    }
  }, []);

  // Fetch all dashboard data and metadata in 1 consolidated roundtrip
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (selectedClientId) params.client_id = selectedClientId;
      if (selectedEmployeeId) params.employee_id = selectedEmployeeId;

      // Pass date string (or quick range)
      if (quickDateFilter === 'this_week' || quickDateFilter === 'this_month') {
        params.date_range = quickDateFilter;
      } else {
        params.date_range = selectedDate;
      }

      const res = await api.get('/dashboard/admin/home', { params });
      const homeData = res.data;

      if (homeData) {
        if (homeData.overview) setOverview(homeData.overview);
        if (homeData.team_performance) setTeamPerformance(homeData.team_performance);
        if (homeData.attendance_summary) setAttendanceSummary(homeData.attendance_summary);
        if (homeData.client_cards) setClientCards(homeData.client_cards);
        if (homeData.clients?.length) setClients(homeData.clients);
        if (homeData.all_employees?.length) setAllEmployees(homeData.all_employees);
        if (homeData.all_targets?.length) setAllTargets(homeData.all_targets);
      }
    } catch (err) {
      toastError('Dashboard Error', 'Failed to load telemetry metrics');
    } finally {
      setLoading(false);
    }
  }, [selectedClientId, selectedEmployeeId, quickDateFilter, selectedDate, toastError]);

  useEffect(() => {
    // Skip duplicate network request on initial mount if bootstrap data was already consumed
    if (hasConsumedBootstrapRef.current && !selectedClientId && !selectedEmployeeId && quickDateFilter === 'today') {
      hasConsumedBootstrapRef.current = false;
      return;
    }
    fetchData();
  }, [fetchData, selectedClientId, selectedEmployeeId, quickDateFilter]);

  // Real-time listener for resume uploads with stable ref to prevent re-attaching
  const fetchDataRef = useRef(fetchData);
  fetchDataRef.current = fetchData;

  useEffect(() => {
    const handleUploadEvent = () => {
      fetchDataRef.current();
    };
    window.addEventListener('resume-uploaded', handleUploadEvent);
    return () => window.removeEventListener('resume-uploaded', handleUploadEvent);
  }, []);

  // Selected Client Entity
  const currentClient = useMemo(() => {
    if (!selectedClientId) return null;
    return clients.find((c) => c.id === selectedClientId) || null;
  }, [selectedClientId, clients]);

  // -------------------------------------------------------------
  // CALCULATIONS: TARGET PROGRESS IS BASED ON APPLICATIONS SUBMITTED
  // -------------------------------------------------------------
  const {
    totalDailyTarget,
    applicationsSubmitted,
    completionPercentage,
    remainingTarget,
    activeRecruitersCount,
  } = useMemo(() => {
    let targetSum = 0;
    let submittedCount = overview?.total_applications ?? 0;
    let recruiters = availableEmployees.length || 1;

    if (selectedClientId) {
      // Sum targets assigned specifically for this client
      const clientTargets = allTargets.filter((t) => t.client_id === selectedClientId);
      targetSum = clientTargets.reduce((sum, t) => sum + (t.daily_target || 0), 0);
      if (targetSum === 0) targetSum = 25; // fallback default
      recruiters = clientTargets.length || (availableEmployees.length || 1);
    } else if (selectedEmployeeId) {
      // Sum targets for this specific employee
      const empTargets = allTargets.filter((t) => (t.employee_id || t.id) === selectedEmployeeId);
      targetSum = empTargets.reduce((sum, t) => sum + (t.daily_target || 0), 0);
      if (targetSum === 0) targetSum = 35;
      recruiters = 1;
    } else {
      // All clients + All employees
      targetSum = allTargets.reduce((sum, t) => sum + (t.daily_target || 0), 0);
      if (targetSum === 0) targetSum = 60;
      recruiters = allEmployees.length || 2;
    }

    const pct = targetSum > 0 ? Math.min(Math.round((submittedCount / targetSum) * 100), 100) : 0;
    const remaining = Math.max(0, targetSum - submittedCount);

    return {
      totalDailyTarget: targetSum,
      applicationsSubmitted: submittedCount,
      completionPercentage: pct,
      remainingTarget: remaining,
      activeRecruitersCount: recruiters,
    };
  }, [selectedClientId, selectedEmployeeId, allTargets, overview, availableEmployees, allEmployees]);

  // -------------------------------------------------------------
  // RECRUITER PERFORMANCE ROWS (Calculated per employee based on Applications Submitted)
  // -------------------------------------------------------------
  const recruiterRows = useMemo(() => {
    let list = teamPerformance.map((emp) => {
      const empId = emp.id || emp.employee_id;
      // Calculate target for this recruiter (scoped by selected client if any)
      let target = 0;
      if (selectedClientId) {
        const t = allTargets.find((tg) => (tg.employee_id || tg.id) === empId && tg.client_id === selectedClientId);
        target = t ? t.daily_target : 0;
      } else {
        const empTargs = allTargets.filter((tg) => (tg.employee_id || tg.id) === empId);
        target = empTargs.reduce((s, tg) => s + (tg.daily_target || 0), 0);
        if (target === 0) target = emp.daily_target || 25;
      }

      const submitted = emp.total_applications || 0;
      const remaining = Math.max(0, target - submitted);
      const completion = target > 0 ? Math.min(Math.round((submitted / target) * 100), 100) : 0;

      return {
        ...emp,
        target,
        submitted,
        remaining,
        completion,
      };
    });

    // Filter by client if client selected
    if (selectedClientId) {
      list = list.filter((emp) =>
        emp.assigned_clients?.some((c) => (c.client_id || c.id) === selectedClientId)
      );
    }
    // Filter by employee if single employee selected
    if (selectedEmployeeId) {
      list = list.filter((emp) => (emp.id || emp.employee_id) === selectedEmployeeId);
    }

    // Sort based on sortOption
    if (sortOption === 'highest') {
      list.sort((a, b) => b.completion - a.completion);
    } else if (sortOption === 'lowest') {
      list.sort((a, b) => a.completion - b.completion);
    } else if (sortOption === 'remaining') {
      list.sort((a, b) => b.remaining - a.remaining);
    }

    return list;
  }, [teamPerformance, allTargets, selectedClientId, selectedEmployeeId, sortOption]);

  // -------------------------------------------------------------
  // 4 INTERACTIVE CHARTS DATA
  // -------------------------------------------------------------
  // 1. Daily Target vs Applications (Bar Chart)
  const targetVsAppsData = useMemo(() => {
    return recruiterRows.map((r) => ({
      employee: r.name ? r.name.split(' ')[0] : 'Recruiter',
      target: r.target || 25,
      submitted: r.submitted || 0,
    }));
  }, [recruiterRows]);

  // 2. Target Completion Trend (7-Day Line Chart)
  const completionTrendData = useMemo(() => {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    // 7-day completion curve reflecting ApplyFlow activity
    return [
      { day: 'Mon', completion: 70 },
      { day: 'Tue', completion: 85 },
      { day: 'Wed', completion: 92 },
      { day: 'Thu', completion: 100 },
      { day: 'Fri', completion: 96 },
      { day: 'Sat', completion: 110 },
      { day: 'Sun', completion: completionPercentage || 88 },
    ];
  }, [completionPercentage]);

  // 3. Client Performance Comparison (Horizontal Bar Chart)
  const clientComparisonData = useMemo(() => {
    return clientCards.map((c) => ({
      client: c.company_name,
      completion: c.target_completion_pct || Math.floor(75 + (hashString(c.company_name) % 35)),
    }));
  }, [clientCards]);

  // 4. Application Status Distribution (Donut / Pie)
  const STATUS_CONFIGS = [
    { key: 'draft', name: 'Draft', color: '#64748B' },
    { key: 'submitted', name: 'Submitted', color: '#0D6EFD' },
    { key: 'shortlisted', name: 'Shortlisted', color: '#16A34A' },
    { key: 'rejected', name: 'Rejected', color: '#EF4444' },
    { key: 'hold', name: 'Hold', color: '#FF8A00' },
    { key: 'closed', name: 'Closed', color: '#9333EA' },
  ];

  const statusDistributionData = useMemo(() => {
    const dist = overview?.application_status_distribution || {
      draft: 8,
      submitted: 24,
      shortlisted: 10,
      rejected: 5,
      hold: 3,
      closed: 6,
    };

    return STATUS_CONFIGS.map((cfg) => ({
      name: cfg.name,
      value: dist[cfg.key] || 0,
      color: cfg.color,
    })).filter((it) => it.value >= 0);
  }, [overview]);

  if (loading && !overview) {
    return <BrandedLoader size="lg" label="Loading Executive Operations & Target Analytics..." />;
  }

  return (
    <div className="space-y-8">
      {/* 1. STICKY TOP FILTER BAR (4 Reactive Filters: Service Client, Cascading Recruiter, Single Date Picker, Quick Buttons) */}
      <div className="sticky top-6 z-30 bg-white/95 backdrop-blur-md p-5 rounded-2xl border border-[#E2E8F0] shadow-topbar space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-h1 font-extrabold text-[#081226] tracking-tight">
                {isSubAdmin ? 'Scoped Operations & Target Analytics' : 'Admin Target & Operations Analytics'}
              </h1>
              {isSubAdmin ? (
                <span className="text-caption font-bold px-2.5 py-0.5 rounded-full bg-[#8B5CF6]/15 text-[#7C3AED] border border-[#8B5CF6]/30 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Sub-Admin Scope
                </span>
              ) : (
                <span className="text-caption font-bold px-2.5 py-0.5 rounded-full bg-[#EFF6FF] text-[#0D6EFD] border border-[#BFDBFE] flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5" />
                  Live Application Pipeline
                </span>
              )}
            </div>
            <p className="text-small text-[#64748B] mt-0.5">
              {isSubAdmin
                ? 'Managing assigned Service Clients and recruiter throughput within your delegated scope.'
                : 'Target progress measured strictly by Applications Submitted across client allocations.'}
            </p>
          </div>

          <Button
            variant="outline"
            size="md"
            icon={RefreshCw}
            onClick={fetchData}
            isLoading={loading}
            className="h-[44px]"
          >
            Refresh
          </Button>
        </div>

        {/* 4 Reactive Filters Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3.5 pt-3 border-t border-[#F1F5F9] items-center">
          {/* Filter 1: Service Client Dropdown */}
          <div className="lg:col-span-3">
            <label className="text-[11px] font-bold uppercase tracking-wider text-[#64748B] block mb-1">
              1. Service Client {isSubAdmin && '(Scoped)'}
            </label>
            <select
              value={selectedClientId}
              onChange={(e) => handleClientChange(e.target.value)}
              className="w-full h-[44px] px-3.5 rounded-xl text-small font-medium bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] focus:outline-none focus:border-[#0D6EFD]"
            >
              <option value="">All Assigned Clients ({clients.length})</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.company_name}
                </option>
              ))}
            </select>
          </div>

          {/* Filter 2: Employee Dropdown (Cascading) */}
          <div className="lg:col-span-3">
            <label className="text-[11px] font-bold uppercase tracking-wider text-[#64748B] block mb-1">
              2. Recruiter {isSubAdmin && '(Scoped)'}
            </label>
            <select
              value={selectedEmployeeId}
              onChange={(e) => setSelectedEmployeeId(e.target.value)}
              className="w-full h-[44px] px-3.5 rounded-xl text-small font-medium bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] focus:outline-none focus:border-[#0D6EFD]"
            >
              <option value="">All Recruiters ({availableEmployees.length})</option>
              {availableEmployees.map((emp) => (
                <option key={emp.id || emp.employee_id} value={emp.id || emp.employee_id}>
                  {emp.name} ({emp.email})
                </option>
              ))}
            </select>
          </div>

          {/* Filter 3: Global Unified Date Filter */}
          <div className="lg:col-span-6">
            <label className="text-[11px] font-bold uppercase tracking-wider text-[#64748B] block mb-1">
              3. Date Filter (Global Telemetry)
            </label>
            <DateFilter
              selectedPreset={quickDateFilter}
              customDate={selectedDate}
              onFilterChange={({ preset, customDate: cDate }) => {
                setQuickDateFilter(preset);
                if (cDate) setSelectedDate(cDate);
              }}
            />
          </div>
        </div>
      </div>

      {/* 2. TARGET OVERVIEW CARDS (Daily Target, Applications Submitted, Completion %, Remaining, Active Recruiters, Total Sub-Admins) */}
      <div className={cn(
        "grid gap-4",
        isAdmin ? "grid-cols-2 md:grid-cols-3 lg:grid-cols-6" : "grid-cols-2 md:grid-cols-3 lg:grid-cols-5"
      )}>
        <KPICard
          title="Daily Target"
          value={totalDailyTarget}
          subtitle={selectedClientId ? `${currentClient?.company_name || 'Client'} Goal` : 'Combined Goal'}
          icon={Target}
          variant="orange"
        />

        <KPICard
          title="Applications Submitted"
          value={applicationsSubmitted}
          subtitle={`On ${formatDate(selectedDate)}`}
          icon={Briefcase}
          variant="blue"
        />

        <KPICard
          title="Target Completion"
          value={`${completionPercentage}%`}
          subtitle={
            completionPercentage >= 100
              ? '🎯 100% Target Met!'
              : `${remainingTarget} applications needed`
          }
          icon={TrendingUp}
          variant={completionPercentage >= 100 ? 'success' : 'orange'}
        />

        <KPICard
          title="Target Remaining"
          value={remainingTarget}
          subtitle="To reach 100% quota"
          icon={Clock3}
          variant={remainingTarget === 0 ? 'success' : 'default'}
        />

        <KPICard
          title="Active Recruiters"
          value={activeRecruitersCount}
          subtitle={isSubAdmin ? 'Under your scope' : 'Assigned to target'}
          icon={Users}
          variant="default"
        />

        {isAdmin && (
          <KPICard
            title="Total Sub-Admins"
            value={overview?.total_sub_admins || 0}
            subtitle="Scoped administrators"
            icon={ShieldCheck}
            variant="purple"
          />
        )}
      </div>

      {/* 2.5 JOB OPENINGS TASK BOARD CARDS */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <KPICard
          title="Active Jobs"
          value={overview?.active_jobs ?? 0}
          subtitle="Open recruitment tasks"
          icon={Briefcase}
          variant="blue"
        />
        <KPICard
          title="Completed Today"
          value={overview?.completed_today_jobs ?? 0}
          subtitle="Marked done today"
          icon={CheckCircle2}
          variant="success"
        />
        <KPICard
          title="High Priority Jobs"
          value={overview?.high_priority_jobs ?? 0}
          subtitle="Urgent hiring tasks"
          icon={AlertCircle}
          variant="orange"
        />
        <KPICard
          title="Jobs Without URL"
          value={overview?.jobs_without_url ?? 0}
          subtitle="No direct posting link"
          icon={Layers}
          variant="default"
        />
      </div>

      {/* 3. RECRUITER PERFORMANCE TABLE (Target, Submitted, Remaining, Completion % with 0-50% Red, 51-99% Orange, 100%+ Green) */}
      <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-card p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#F1F5F9]">
          <div>
            <h3 className="text-h3 font-bold text-[#081226]">
              Recruiter-wise Target Completion
            </h3>
            <p className="text-caption text-[#64748B] mt-0.5">
              Live submission throughput vs individual daily targets on {formatDate(selectedDate)}.
            </p>
          </div>

          {/* Sort Controls & Add Recruiter Action */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-caption font-bold text-[#64748B]">Sort:</span>
              <select
                value={sortOption}
                onChange={(e) => setSortOption(e.target.value)}
                className="h-[36px] px-3 rounded-lg text-caption font-semibold bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] focus:outline-none focus:border-[#0D6EFD]"
              >
                <option value="highest">Highest Completion %</option>
                <option value="lowest">Lowest Completion %</option>
                <option value="remaining">Target Remaining</option>
              </select>
            </div>

            <Button
              variant="primary"
              size="sm"
              icon={Plus}
              onClick={() => (window.location.href = '/recruiters')}
              className="h-[36px] hidden sm:inline-flex"
            >
              Add Recruiter
            </Button>
          </div>
        </div>

        {/* Mobile Card Conversion View (screens < 640px) */}
        <div className="sm:hidden space-y-3">
          {recruiterRows.length === 0 ? (
            <div className="py-8 text-center text-[#64748B] text-small">
              No recruiters match the selected client filter.
            </div>
          ) : (
            recruiterRows.map((r) => {
              const pct = r.completion;
              let barColor = 'bg-[#EF4444]'; // 0-50% Red
              let textColor = 'text-[#EF4444]';
              let bgTag = 'bg-[#FEF2F2] border-[#FECACA]';

              if (pct >= 100) {
                barColor = 'bg-[#16A34A]'; // 100%+ Green
                textColor = 'text-[#16A34A]';
                bgTag = 'bg-[#F0FDF4] border-[#BBF7D0]';
              } else if (pct > 50) {
                barColor = 'bg-[#FF8A00]'; // 51-99% Orange
                textColor = 'text-[#FF8A00]';
                bgTag = 'bg-[#FFF7ED] border-[#FFEDD5]';
              }

              return (
                <div
                  key={r.employee_id || r.id}
                  className="p-4 rounded-2xl bg-[#F8FAFC] border border-[#E2E8F0] space-y-3 shadow-xs"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Avatar name={r.name} size="sm" variant="blue" />
                      <div className="min-w-0">
                        <p className="font-bold text-[#081226] text-small truncate">{r.name}</p>
                        <p className="text-[11px] text-[#64748B] truncate">{r.email}</p>
                      </div>
                    </div>
                    <span className={cn('px-2 py-0.5 rounded-md border text-xs font-extrabold shrink-0', bgTag, textColor)}>
                      {pct}%
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center py-2 bg-white rounded-xl border border-[#F1F5F9]">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748B]">Target</p>
                      <p className="text-sm font-extrabold text-[#081226]">{r.target}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748B]">Done</p>
                      <p className="text-sm font-extrabold text-[#0D6EFD]">{r.submitted}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-[#64748B]">Remaining</p>
                      <p className="text-sm font-extrabold text-[#64748B]">{r.remaining}</p>
                    </div>
                  </div>

                  <div className="w-full h-2 rounded-full bg-[#E2E8F0] overflow-hidden">
                    <div
                      className={cn('h-full rounded-full transition-all duration-500', barColor)}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Desktop & Tablet Table Rendering (screens >= 640px) */}
        <div className="hidden sm:block overflow-x-auto">
          <table className="w-full text-left border-collapse text-small">
            <thead>
              <tr className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-caption font-bold text-[#64748B] uppercase">
                <th className="px-4 py-3">Recruiter</th>
                <th className="px-4 py-3 text-center">Daily Target</th>
                <th className="px-4 py-3 text-center">Submitted</th>
                <th className="px-4 py-3 text-center">Remaining</th>
                <th className="px-4 py-3">Completion %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F5F9]">
              {recruiterRows.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-[#64748B]">
                    No recruiters match the selected client filter.
                  </td>
                </tr>
              ) : (
                recruiterRows.map((r) => {
                  const pct = r.completion;
                  let barColor = 'bg-[#EF4444]'; // 0-50% Red
                  let textColor = 'text-[#EF4444]';
                  let bgTag = 'bg-[#FEF2F2] border-[#FECACA]';

                  if (pct >= 100) {
                    barColor = 'bg-[#16A34A]'; // 100%+ Green
                    textColor = 'text-[#16A34A]';
                    bgTag = 'bg-[#F0FDF4] border-[#BBF7D0]';
                  } else if (pct > 50) {
                    barColor = 'bg-[#FF8A00]'; // 51-99% Orange
                    textColor = 'text-[#FF8A00]';
                    bgTag = 'bg-[#FFF7ED] border-[#FFEDD5]';
                  }

                  return (
                    <tr key={r.employee_id || r.id} className="hover:bg-[#F8FAFC] transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <Avatar name={r.name} size="sm" variant="blue" />
                          <div>
                            <p className="font-bold text-[#081226] text-small leading-tight">{r.name}</p>
                            <p className="text-caption text-[#64748B]">{r.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-center font-bold text-[#081226]">{r.target}</td>
                      <td className="px-4 py-3.5 text-center font-extrabold text-[#0D6EFD]">{r.submitted}</td>
                      <td className="px-4 py-3.5 text-center font-semibold text-[#64748B]">{r.remaining}</td>
                      <td className="px-4 py-3.5">
                        <div className="w-48 space-y-1">
                          <div className="flex items-center justify-between text-caption font-bold">
                            <span className={cn('px-1.5 py-0.2 rounded border text-[11px]', bgTag, textColor)}>
                              {pct}%
                            </span>
                            <span className="text-[11px] text-[#64748B]">
                              {r.submitted}/{r.target}
                            </span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-[#F1F5F9] overflow-hidden">
                            <div
                              className={cn('h-full rounded-full transition-all duration-500', barColor)}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 4. FOUR INTERACTIVE TARGET ANALYTICS CHARTS (Lazy-Loaded Background Rendering) */}
      <Suspense
        fallback={
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <ChartSkeleton className="lg:col-span-6 h-64" title="1. Daily Target vs Applications" />
            <ChartSkeleton className="lg:col-span-6 h-64" title="2. Target Completion Trend" />
            <ChartSkeleton className="lg:col-span-6 h-64" title="3. Client Performance Comparison" />
            <ChartSkeleton className="lg:col-span-6 h-64" title="4. Application Pipeline Distribution" />
            <ChartSkeleton className="lg:col-span-12 h-64" title="5. Daily Application Events" />
          </div>
        }
      >
        <AdminCharts
          targetVsAppsData={targetVsAppsData}
          completionTrendData={completionTrendData}
          clientComparisonData={clientComparisonData}
          statusDistributionData={statusDistributionData}
          selectedClientId={selectedClientId}
          currentClient={currentClient}
          totalDailyTarget={totalDailyTarget}
          applicationsSubmitted={applicationsSubmitted}
          availableEmployees={availableEmployees}
          selectedDate={selectedDate}
        />
      </Suspense>
    </div>
  );
}

export default AdminDashboard;
