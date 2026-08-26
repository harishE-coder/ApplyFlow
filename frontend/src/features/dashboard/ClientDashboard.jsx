import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  Briefcase,
  CheckCircle2,
  TrendingUp,
  Building2,
  Users,
  ChevronDown,
  RefreshCw,
  Search,
  Filter,
  Check,
  Award,
  Sparkles,
  Layers,
  ArrowRight,
  Clock,
  Send,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts';
import { KPICard } from '@/components/ui/KPICard';
import { BrandedLoader } from '@/components/ui/BrandedLoader';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/features/auth/AuthContext';
import api from '@/services/api';
import { cn } from '@/utils/cn';

export function ClientDashboard() {
  const { user } = useAuth();
  const { error: toastError } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Hiring Company Filter State
  const [selectedHiringCompany, setSelectedHiringCompany] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedCards, setExpandedCards] = useState({});

  const fetchClientDashboard = async () => {
    setLoading(true);
    try {
      const res = await api.get('/dashboard/client');
      setData(res.data);
    } catch (err) {
      toastError('Dashboard Error', 'Failed to load client portal telemetry');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClientDashboard();
  }, []);

  // Real-time listener for resume uploads to update client portal metrics instantly
  useEffect(() => {
    const handleUploadEvent = () => {
      fetchClientDashboard();
    };
    window.addEventListener('resume-uploaded', handleUploadEvent);
    return () => window.removeEventListener('resume-uploaded', handleUploadEvent);
  }, []);

  const toggleCard = (id) => {
    setExpandedCards((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Filter timeline items by Hiring Company & search
  const filteredTimeline = useMemo(() => {
    if (!data?.application_timeline) return [];
    return data.application_timeline.filter((item) => {
      const matchCompany =
        selectedHiringCompany === 'all' ||
        item.hiring_company?.toLowerCase() === selectedHiringCompany.toLowerCase();
      const matchSearch =
        !searchQuery ||
        item.candidate_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.hiring_company?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.role?.toLowerCase().includes(searchQuery.toLowerCase());
      return matchCompany && matchSearch;
    });
  }, [data, selectedHiringCompany, searchQuery]);

  const progressData = useMemo(() => {
    if (!data?.application_progress) {
      return [
        { stage: 'Applied', count: 179, color: '#2563EB' },
        { stage: 'Interview', count: 24, color: '#F97316' },
        { stage: 'Offer', count: 6, color: '#10B981' },
        { stage: 'Joined', count: 2, color: '#9333EA' },
      ];
    }
    const colors = ['#2563EB', '#F97316', '#10B981', '#9333EA'];
    return data.application_progress.map((item, idx) => ({
      stage: item.stage,
      count: item.count,
      color: colors[idx % colors.length],
    }));
  }, [data]);

  const getRoundBadgeColor = (roundStr = '') => {
    const r = roundStr.toLowerCase();
    if (r.includes('offer')) return 'bg-[#F0FDF4] text-[#16A34A] border-[#BBF7D0]';
    if (r.includes('tech') || r.includes('coding')) return 'bg-[#EFF6FF] text-[#2563EB] border-[#BFDBFE]';
    if (r.includes('hr') || r.includes('discussion')) return 'bg-[#FAF5FF] text-[#9333EA] border-[#E9D5FF]';
    if (r.includes('shortlist') || r.includes('round 1') || r.includes('round 2')) return 'bg-[#FFF7ED] text-[#F97316] border-[#FFEDD5]';
    if (r.includes('reject')) return 'bg-[#FEF2F2] text-[#EF4444] border-[#FECACA]';
    return 'bg-[#F8FAFC] text-[#081226] border-[#E2E8F0]';
  };

  if (loading && !data) {
    return <BrandedLoader size="lg" label="Loading Client Talent Dashboard..." />;
  }

  const clientName = data?.company_name || user?.name || 'ABC Staffing';

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12 select-none">
      {/* 1. Header (Clean Customer View - No internal Service Client dropdown) */}
      <div className="bg-white p-6 rounded-3xl border border-[#E2E8F0] shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-h2 font-extrabold text-[#081226] tracking-tight">
              {clientName} Dashboard
            </h1>
            <span className="text-caption font-bold px-2.5 py-0.5 rounded-full bg-[#EFF6FF] text-[#2563EB] border border-[#BFDBFE] flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-[#F97316]" />
              Dedicated Service Portal
            </span>
          </div>
          <p className="text-small text-[#64748B] mt-1">
            Real-time candidate submissions and interview progress for your organization.
          </p>
        </div>

        <Button
          variant="outline"
          size="md"
          icon={RefreshCw}
          onClick={fetchClientDashboard}
          isLoading={loading}
          className="h-[44px] font-bold text-xs"
        >
          Refresh Data
        </Button>
      </div>

      {/* 2. Top 4 Locked KPI Cards (Applied, Today's Uploads, Interview Updates, Offers) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <KPICard
          title="Applied"
          value={data?.applied_count ?? 179}
          subtitle="All resumes uploaded"
          icon={FileText}
          variant="blue"
        />

        <KPICard
          title="Today's Uploads"
          value={data?.today_uploads ?? 12}
          subtitle="Uploaded today"
          icon={Clock}
          variant="default"
        />

        <KPICard
          title="Interview Updates"
          value={data?.interview_updates ?? 24}
          subtitle="Interview emails received"
          icon={TrendingUp}
          variant="orange"
        />

        <KPICard
          title="Offers"
          value={data?.offers_count ?? 6}
          subtitle="Offer emails received"
          icon={Award}
          variant="success"
        />
      </div>

      {/* 3. Application Progress Chart & Live Stats Breakdown */}
      <div className="bg-white p-6 sm:p-7 rounded-3xl border border-[#E2E8F0] shadow-card space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#F1F5F9]">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#2563EB] px-2.5 py-0.5 rounded-full bg-[#EFF6FF] border border-[#BFDBFE]">
                Recruitment Funnel
              </span>
              <h3 className="text-h3 font-bold text-[#081226]">
                Application Progress
              </h3>
            </div>
            <p className="text-caption text-[#64748B] mt-0.5">
              Candidate volume at each stage for your service account ({clientName}).
            </p>
          </div>

          <div className="flex items-center gap-4 text-caption font-semibold">
            <span className="flex items-center gap-1.5 text-[#2563EB]">
              <span className="w-2.5 h-2.5 rounded-full bg-[#2563EB]" /> Applied ({data?.applied_count ?? 179})
            </span>
            <span className="flex items-center gap-1.5 text-[#F97316]">
              <span className="w-2.5 h-2.5 rounded-full bg-[#F97316]" /> Interview ({data?.interview_updates ?? 24})
            </span>
            <span className="flex items-center gap-1.5 text-[#10B981]">
              <span className="w-2.5 h-2.5 rounded-full bg-[#10B981]" /> Offer ({data?.offers_count ?? 6})
            </span>
            <span className="flex items-center gap-1.5 text-[#9333EA]">
              <span className="w-2.5 h-2.5 rounded-full bg-[#9333EA]" /> Joined (2)
            </span>
          </div>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={progressData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
              <XAxis dataKey="stage" stroke="#94A3B8" fontSize={13} fontWeight={600} />
              <YAxis stroke="#94A3B8" fontSize={12} />
              <Tooltip
                formatter={(val) => [`${val} Candidates`, 'Candidate Volume']}
                contentStyle={{
                  backgroundColor: '#081226',
                  borderRadius: '12px',
                  border: '1px solid #1E2E4E',
                  color: '#FFF',
                }}
              />
              <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                {progressData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 4. Application Timeline & Hiring Company Filter */}
      <div className="space-y-4">
        {/* Filters Header: Hiring Company Filter + Candidate Search */}
        <div className="bg-white p-5 rounded-3xl border border-[#E2E8F0] shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-h3 font-bold text-[#081226]">Application Timeline</h3>
            <p className="text-caption text-[#64748B] mt-0.5">
              Live candidate progression stages across hiring companies.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-3">
            {/* Search */}
            <div className="relative w-full sm:w-60">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#94A3B8]" />
              <input
                type="text"
                placeholder="Search candidate, role..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 h-[40px] rounded-xl text-small bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] focus:outline-none focus:border-[#2563EB]"
              />
            </div>

            {/* Hiring Company Filter (Renamed from Target Company) */}
            <div className="w-full sm:w-auto">
              <select
                value={selectedHiringCompany}
                onChange={(e) => setSelectedHiringCompany(e.target.value)}
                className="w-full sm:w-auto h-[40px] px-3.5 rounded-xl text-small font-medium bg-[#F8FAFC] text-[#081226] border border-[#E2E8F0] focus:outline-none focus:border-[#2563EB]"
              >
                <option value="all">All Hiring Companies</option>
                {(data?.hiring_companies || ['TCS', 'Infosys', 'Amazon', 'Deloitte', 'Google']).map((hc) => (
                  <option key={hc} value={hc}>
                    {hc}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Timeline Cards Feed */}
        <div className="space-y-4">
          {filteredTimeline.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-3xl border border-[#E2E8F0] space-y-3">
              <Users className="w-10 h-10 text-[#2563EB] mx-auto" />
              <h4 className="text-h3 font-bold text-[#081226]">No candidates match this filter</h4>
              <p className="text-small text-[#64748B]">Try selecting "All Hiring Companies" or adjusting your search.</p>
            </div>
          ) : (
            filteredTimeline.map((item) => {
              const isExpanded = !!expandedCards[item.id];

              return (
                <motion.div
                  key={item.id}
                  layout
                  className="bg-white rounded-3xl border border-[#E2E8F0] hover:border-[#CBD5E1] shadow-card transition-all overflow-hidden"
                >
                  {/* Card Header */}
                  <div
                    onClick={() => toggleCard(item.id)}
                    className="p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer hover:bg-[#F8FAFC]/50 transition-colors"
                  >
                    <div className="flex items-center gap-4 min-w-0">
                      <Avatar name={item.candidate_name} size="lg" variant="blue" />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2.5 flex-wrap">
                          <h3 className="text-h3 font-extrabold text-[#081226] truncate">
                            {item.candidate_name}
                          </h3>
                          <span className={cn('px-2.5 py-0.5 rounded-lg border text-caption font-extrabold truncate', getRoundBadgeColor(item.round))}>
                            {item.round}
                          </span>
                        </div>
                        <p className="text-small text-[#64748B] mt-0.5">
                          <strong className="text-[#081226]">{item.hiring_company}</strong> · {item.role}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                      <span className="text-caption font-semibold text-[#64748B]">
                        Applied {item.applied_date}
                      </span>
                      <div className="w-8 h-8 rounded-full bg-[#F1F5F9] flex items-center justify-center text-[#64748B]">
                        <ChevronDown className={cn('w-4 h-4 transition-transform', isExpanded ? 'rotate-180' : '')} />
                      </div>
                    </div>
                  </div>

                  {/* Expandable Step-by-step Progression Milestones */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="px-6 pb-6 pt-2 border-t border-[#F1F5F9] bg-[#FAFAFA]"
                      >
                        <p className="text-[11px] font-bold uppercase tracking-wider text-[#64748B] mb-4">
                          Candidate Progression Milestones
                        </p>

                        <div className="relative pl-6 space-y-4 before:content-[''] before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#E2E8F0]">
                          {(item.events && item.events.length > 0 ? item.events : [
                            { stage: 'Application Submitted', round: 'Submitted', date: '23 Aug' },
                            { stage: 'Round 1 Cleared', round: 'Round 1', date: '24 Aug' },
                            { stage: 'Round 2 Scheduled', round: item.round, date: '25 Aug' },
                          ]).map((ev, eIdx) => {
                            const isLatest = eIdx === (item.events?.length ? item.events.length - 1 : 2);

                            return (
                              <div key={eIdx} className="relative space-y-1">
                                <div
                                  className={cn(
                                    'absolute -left-6 top-1 w-4 h-4 rounded-full border-2 border-white',
                                    isLatest
                                      ? 'bg-[#2563EB] ring-2 ring-[#2563EB]/20'
                                      : 'bg-[#10B981] ring-2 ring-[#10B981]/20'
                                  )}
                                />
                                <div className="flex items-center gap-2">
                                  <p className="text-small font-extrabold text-[#081226]">
                                    {isLatest ? `● ${ev.stage || ev.round}` : `✓ ${ev.stage || ev.round}`}
                                  </p>
                                  <span className="text-[11px] text-[#64748B] font-medium">({ev.date})</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

export default ClientDashboard;
