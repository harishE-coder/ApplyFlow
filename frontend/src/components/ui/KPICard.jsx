import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/utils/cn';

export function KPICard({
  title,
  value,
  subtitle,
  trend,
  trendLabel,
  icon: Icon,
  variant = 'default', // 'default' | 'blue' | 'orange' | 'success'
  className,
  action,
}) {
  const iconVariants = {
    default: 'bg-[#F1F5F9] text-[#475569]',
    blue: 'bg-[#EFF6FF] text-[#2563EB]',
    orange: 'bg-[#FFF7ED] text-[#F97316]',
    success: 'bg-[#F0FDF4] text-[#16A34A]',
  };

  const trendPositive = trend > 0;
  const trendNeutral = trend === 0;

  return (
    <div
      className={cn(
        'bg-white p-6 rounded-2xl border border-[#E2E8F0] shadow-card transition-all duration-150',
        'hover:shadow-card-hover hover:border-[#CBD5E1]',
        className
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="text-small font-medium text-[#64748B]">{title}</p>
          <p className="text-display font-extrabold text-[#081226] tracking-tight">{value}</p>
        </div>

        {Icon && (
          <div className={cn('p-3 rounded-xl shrink-0 transition-transform duration-150', iconVariants[variant])}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-[#F1F5F9] flex items-center justify-between">
        {trend !== undefined ? (
          <div className="flex items-center gap-1.5 text-small">
            <span
              className={cn(
                'inline-flex items-center gap-0.5 font-semibold px-1.5 py-0.5 rounded-md text-caption',
                trendPositive && 'bg-[#F0FDF4] text-[#16A34A]',
                !trendPositive && !trendNeutral && 'bg-[#FEF2F2] text-[#EF4444]',
                trendNeutral && 'bg-[#F1F5F9] text-[#64748B]'
              )}
            >
              {trendPositive && <TrendingUp className="w-3.5 h-3.5" />}
              {!trendPositive && !trendNeutral && <TrendingDown className="w-3.5 h-3.5" />}
              {trendNeutral && <Minus className="w-3.5 h-3.5" />}
              {Math.abs(trend)}%
            </span>
            <span className="text-[#64748B] text-caption">{trendLabel || 'vs yesterday'}</span>
          </div>
        ) : subtitle ? (
          <p className="text-caption font-medium text-[#64748B]">{subtitle}</p>
        ) : <div />}

        {action && <div>{action}</div>}
      </div>
    </div>
  );
}

export default KPICard;
