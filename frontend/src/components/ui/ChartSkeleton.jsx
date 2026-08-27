import React from 'react';
import { cn } from '@/utils/cn';

export function ChartSkeleton({ height = 'h-64', className, title, subtitle }) {
  return (
    <div
      className={cn(
        'bg-white p-6 rounded-2xl border border-[#E2E8F0] shadow-card space-y-4 animate-pulse',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          {title ? (
            <div className="text-h3 font-bold text-[#081226]">{title}</div>
          ) : (
            <div className="h-5 w-48 bg-[#F1F5F9] rounded-lg" />
          )}
          {subtitle ? (
            <div className="text-caption text-[#64748B]">{subtitle}</div>
          ) : (
            <div className="h-3 w-64 bg-[#F8FAFC] rounded-lg" />
          )}
        </div>
        <div className="h-4 w-20 bg-[#F1F5F9] rounded-full" />
      </div>

      <div className={cn('w-full rounded-xl bg-[#F8FAFC]/80 flex items-center justify-center', height)}>
        <div className="flex items-end gap-3 h-32 opacity-40">
          <div className="w-8 bg-[#CBD5E1] rounded-t h-16 animate-pulse" />
          <div className="w-8 bg-[#2563EB] rounded-t h-28 animate-pulse" />
          <div className="w-8 bg-[#CBD5E1] rounded-t h-20 animate-pulse" />
          <div className="w-8 bg-[#2563EB] rounded-t h-32 animate-pulse" />
          <div className="w-8 bg-[#CBD5E1] rounded-t h-12 animate-pulse" />
          <div className="w-8 bg-[#2563EB] rounded-t h-24 animate-pulse" />
        </div>
      </div>
    </div>
  );
}

export default ChartSkeleton;
