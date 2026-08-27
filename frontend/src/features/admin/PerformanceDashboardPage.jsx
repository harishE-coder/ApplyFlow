import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  Zap,
  Database,
  Cpu,
  RefreshCw,
  Server,
  Layers,
  CheckCircle2,
  HardDrive,
} from 'lucide-react';
import { KPICard } from '@/components/ui/KPICard';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import api from '@/services/api';

export function PerformanceDashboardPage() {
  const { success: toastSuccess, error: toastError } = useToast();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [lastChecked, setLastChecked] = useState(null);
  const [pingLatency, setPingLatency] = useState(null);

  const fetchPerformanceStats = async () => {
    setLoading(true);
    const start = performance.now();
    try {
      const res = await api.get('/dashboard/performance', { cache: false });
      const duration = Math.round(performance.now() - start);
      setPingLatency(duration);
      setStats(res.data);
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err) {
      toastError('Telemetry Error', 'Failed to fetch performance stats');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPerformanceStats();
  }, []);

  const handleClearCache = () => {
    api.invalidateCache();
    toastSuccess('Cache Purged', 'In-memory frontend response cache cleared.');
    fetchPerformanceStats();
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto p-4 md:p-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/40 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary border border-primary/20">
              <Zap className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground">
                Architecture & Performance Diagnostics
              </h1>
              <p className="text-sm text-muted-foreground mt-0.5">
                Real-time API response profiling, query latency, and database health metrics.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearCache}
            className="flex items-center gap-2"
          >
            <Layers className="w-4 h-4 text-amber-500" />
            Purge Frontend Cache
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={fetchPerformanceStats}
            isLoading={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Run Diagnostics
          </Button>
        </div>
      </div>

      {/* KPI Overview Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <KPICard
          title="Round-Trip Latency"
          value={pingLatency !== null ? `${pingLatency} ms` : 'Measuring...'}
          change={pingLatency && pingLatency < 400 ? 'Sub-second' : 'Normal'}
          changeType="positive"
          icon={Activity}
          subtitle={`Last checked: ${lastChecked || 'Just now'}`}
        />

        <KPICard
          title="Database Pool"
          value={stats?.database_connected ? 'Healthy' : 'Connecting'}
          change="SSL Active"
          changeType="positive"
          icon={Database}
          subtitle={stats?.db_engine || 'Asyncpg Driver'}
        />

        <KPICard
          title="Indexed Resumes"
          value={stats?.total_resumes?.toLocaleString() || '0'}
          change="Compound B-Tree"
          changeType="positive"
          icon={HardDrive}
          subtitle="Client + Date indexes"
        />

        <KPICard
          title="Applications Tracked"
          value={stats?.total_applications?.toLocaleString() || '0'}
          change="Indexed Status"
          changeType="positive"
          icon={Cpu}
          subtitle="Pipeline stages"
        />
      </div>

      {/* Architecture Highlights & Optimizations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-6 rounded-2xl bg-card border border-border shadow-sm space-y-4"
        >
          <div className="flex items-center gap-2 text-foreground font-semibold text-base border-b border-border/40 pb-3">
            <Server className="w-5 h-5 text-primary" />
            Active Backend Optimizations
          </div>

          <ul className="space-y-3 text-sm">
            <li className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
              <div>
                <strong className="text-foreground">Consolidated Home Endpoints:</strong>{' '}
                <span className="text-muted-foreground">
                  Overview, team metrics, client cards, and attendance bundled into <code>/dashboard/admin/home</code>.
                </span>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
              <div>
                <strong className="text-foreground">Parallel Query Execution:</strong>{' '}
                <span className="text-muted-foreground">
                  Database queries execute concurrently via <code>asyncio.gather</code>, eliminating sequential wait times.
                </span>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
              <div>
                <strong className="text-foreground">Compound Database Indexes:</strong>{' '}
                <span className="text-muted-foreground">
                  Multi-column indexes on <code>(client_id, resume_date)</code> and <code>(employee_id, applied_date)</code>.
                </span>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
              <div>
                <strong className="text-foreground">Lazy Google Drive Loading:</strong>{' '}
                <span className="text-muted-foreground">
                  Google Apps Script is never invoked during list or search loading.
                </span>
              </div>
            </li>
          </ul>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="p-6 rounded-2xl bg-card border border-border shadow-sm space-y-4"
        >
          <div className="flex items-center gap-2 text-foreground font-semibold text-base border-b border-border/40 pb-3">
            <Layers className="w-5 h-5 text-primary" />
            Frontend Caching & Bundling Architecture
          </div>

          <ul className="space-y-3 text-sm">
            <li className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
              <div>
                <strong className="text-foreground">In-Memory SWR Caching:</strong>{' '}
                <span className="text-muted-foreground">
                  25-second TTL in-memory cache in <code>api.js</code> prevents redundant network calls on navigation.
                </span>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
              <div>
                <strong className="text-foreground">Inflight Request Deduplication:</strong>{' '}
                <span className="text-muted-foreground">
                  Identical concurrent GET requests automatically merge into a single network promise.
                </span>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
              <div>
                <strong className="text-foreground">Route-Based Code Splitting:</strong>{' '}
                <span className="text-muted-foreground">
                  All 14 pages lazy-loaded on demand via <code>React.lazy</code> & <code>Suspense</code>.
                </span>
              </div>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
              <div>
                <strong className="text-foreground">Vendor Chunk Splitting:</strong>{' '}
                <span className="text-muted-foreground">
                  React, Recharts, and Lucide split into dedicated cached vendor bundles.
                </span>
              </div>
            </li>
          </ul>
        </motion.div>
      </div>
    </div>
  );
}
