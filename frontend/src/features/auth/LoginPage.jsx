import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import {
  Lock,
  Mail,
  ArrowRight,
  CheckCircle2,
  ShieldCheck,
  Zap,
  Users,
  Building2,
  Briefcase,
} from 'lucide-react';
import { ApplyFlowLogo } from '@/assets/logo/ApplyFlowLogo';
import { LoginBrandIllustration } from '@/assets/illustrations/ATSIllustrations';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from './AuthContext';
import { useToast } from '@/components/ui/Toast';

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const { success, error: toastError } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [authError, setAuthError] = useState('');

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm({
    defaultValues: {
      email: 'harish@applyflow.com',
      password: 'harish123',
    },
  });

  const onSubmit = async (data) => {
    setIsLoading(true);
    setAuthError('');
    try {
      const user = await login(data.email, data.password);
      success('Welcome back', `Signed in as ${user.name} (${user.role})`);
      navigate('/dashboard');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Invalid email or password';
      setAuthError(msg);
      toastError('Authentication Failed', msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickFill = (email, password) => {
    setValue('email', email);
    setValue('password', password);
    setAuthError('');
  };

  const demoAccounts = [
    {
      role: 'Recruiter (Employee)',
      name: 'Harish',
      email: 'harish@applyflow.com',
      password: 'harish123',
      clients: 'ABC Staffing, Talent Hub',
      badge: 'Primary Recruiter',
      badgeColor: 'orange',
    },
    {
      role: 'Admin',
      name: 'Admin User',
      email: 'admin@applyflow.com',
      password: 'admin123',
      clients: 'All Clients & Operations',
      badge: 'Full Access',
      badgeColor: 'blue',
    },
    {
      role: 'Client Portal',
      name: 'John Doe',
      email: 'john@abcstaffing.com',
      password: 'client123',
      clients: 'ABC Staffing Account',
      badge: 'Client Reviewer',
      badgeColor: 'gray',
    },
  ];

  return (
    <div className="min-h-screen w-full flex bg-[#F6F8FB]">
      {/* LEFT 40%: Branding Showcase */}
      <div className="hidden lg:flex lg:w-[42%] bg-[#081226] p-12 flex-col justify-between relative overflow-hidden border-r border-[#1E2E4E]">
        {/* Ambient background glow */}
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-[#2563EB]/15 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-[#F97316]/10 blur-3xl pointer-events-none" />

        {/* Brand Header */}
        <div className="relative z-10">
          <ApplyFlowLogo variant="dark" />
        </div>

        {/* Middle Visual & Value Prop */}
        <div className="relative z-10 my-auto py-8">
          <div className="mb-8">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#2563EB]/20 border border-[#2563EB]/30 text-caption font-semibold text-[#60A5FA] mb-4">
              <Zap className="w-3.5 h-3.5 text-[#F97316]" />
              Commercial ATS v3.0 Architecture
            </span>

            <h1 className="text-display font-extrabold text-white tracking-tight leading-tight">
              Recruitment operations at scale.
            </h1>

            <p className="text-body text-[#94A3B8] mt-3 max-w-md leading-relaxed">
              Precision candidate parsing, live pipeline orchestration, client delivery tracking, and performance targets in one unified workspace.
            </p>
          </div>

          <div className="my-6">
            <LoginBrandIllustration className="w-full max-w-[380px]" />
          </div>

          {/* Key Feature Bullets */}
          <div className="space-y-3 pt-4 border-t border-[#1E2E4E]">
            <div className="flex items-center gap-3 text-small text-[#CBD5E1]">
              <CheckCircle2 className="w-4 h-4 text-[#16A34A] shrink-0" />
              <span>Multi-client candidate isolation and permission scoping</span>
            </div>
            <div className="flex items-center gap-3 text-small text-[#CBD5E1]">
              <CheckCircle2 className="w-4 h-4 text-[#16A34A] shrink-0" />
              <span>Instant batch resume ingestion & duplicate detection</span>
            </div>
            <div className="flex items-center gap-3 text-small text-[#CBD5E1]">
              <CheckCircle2 className="w-4 h-4 text-[#16A34A] shrink-0" />
              <span>Permanent split-view candidate review & one-click submit</span>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="relative z-10 flex items-center justify-between text-caption text-[#64748B] pt-4 border-t border-[#101F3D]">
          <span>ApplyFlow Careers ATS</span>
          <span>Enterprise v3.0</span>
        </div>
      </div>

      {/* RIGHT 60%: High-Precision Login Form */}
      <div className="flex-1 flex flex-col justify-center items-center p-6 sm:p-12 md:p-16 lg:p-20 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="w-full max-w-[480px] bg-white rounded-3xl border border-[#E2E8F0] shadow-card p-8 sm:p-10"
        >
          {/* Mobile Logo */}
          <div className="lg:hidden mb-8">
            <ApplyFlowLogo variant="light" />
          </div>

          <div className="mb-8">
            <h2 className="text-h1 font-extrabold text-[#081226] tracking-tight">
              Sign in to workspace
            </h2>
            <p className="text-small text-[#64748B] mt-1.5">
              Enter your corporate credentials to access candidate pipelines.
            </p>
          </div>

          {authError && (
            <div className="mb-6 p-4 rounded-xl bg-[#FEF2F2] border border-[#FECACA] text-[#EF4444] text-small font-medium flex items-center gap-2.5">
              <ShieldCheck className="w-5 h-5 shrink-0" />
              <span>{authError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <Input
              label="Work Email Address"
              type="email"
              placeholder="name@company.com"
              icon={Mail}
              required
              error={errors.email?.message}
              {...register('email', {
                required: 'Work email is required',
                pattern: {
                  value: /^\S+@\S+$/i,
                  message: 'Invalid email address',
                },
              })}
            />

            <Input
              label="Password"
              type="password"
              placeholder="••••••••••••"
              icon={Lock}
              required
              error={errors.password?.message}
              {...register('password', {
                required: 'Password is required',
                minLength: {
                  value: 6,
                  message: 'Password must be at least 6 characters',
                },
              })}
            />

            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                size="lg"
                isLoading={isLoading}
                icon={ArrowRight}
                iconPosition="right"
                className="w-full h-[48px] text-body"
              >
                Sign In to ApplyFlow
              </Button>
            </div>
          </form>

          {/* 1-Click Demo Roles Switcher */}
          <div className="mt-8 pt-6 border-t border-[#F1F5F9]">
            <p className="text-caption font-bold uppercase tracking-wider text-[#64748B] mb-3 text-center">
              Quick Switch Demo Roles
            </p>

            <div className="space-y-2">
              {demoAccounts.map((account) => (
                <button
                  key={account.email}
                  type="button"
                  onClick={() => handleQuickFill(account.email, account.password)}
                  className="w-full p-3 rounded-xl border border-[#E2E8F0] hover:border-[#2563EB] hover:bg-[#EFF6FF]/40 text-left transition-all duration-120 flex items-center justify-between group cursor-pointer"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-small font-bold text-[#081226] group-hover:text-[#2563EB]">
                        {account.role}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                          account.badgeColor === 'orange'
                            ? 'bg-[#FFF7ED] text-[#F97316] border border-[#FFEDD5]'
                            : account.badgeColor === 'blue'
                            ? 'bg-[#EFF6FF] text-[#2563EB] border border-[#BFDBFE]'
                            : 'bg-[#F1F5F9] text-[#64748B] border border-[#E2E8F0]'
                        }`}
                      >
                        {account.badge}
                      </span>
                    </div>
                    <p className="text-caption text-[#64748B] mt-0.5 truncate">
                      {account.email} • {account.clients}
                    </p>
                  </div>

                  <span className="text-caption font-semibold text-[#2563EB] opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-2">
                    Use →
                  </span>
                </button>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

export default LoginPage;
