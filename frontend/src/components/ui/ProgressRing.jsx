import React from 'react';
import { cn } from '@/utils/cn';

export function ProgressRing({
  progress = 0, // 0 to 100
  size = 110,
  strokeWidth = 10,
  color = '#F97316', // Orange used for progress & targets
  trackColor = '#F1F5F9',
  label,
  valueText,
  className,
}) {
  // Visual ring caps at 100% (full circle), but display shows actual value including over-100%
  const visualProgress = Math.min(Math.max(progress, 0), 100);
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (visualProgress / 100) * circumference;

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Track circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={trackColor}
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Animated Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="none"
          className="transition-all duration-700 ease-out"
        />
      </svg>

      {/* Center Label */}
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center select-none">
        <span className="text-[20px] font-extrabold text-[#081226] tracking-tight leading-none">
          {valueText || `${Math.round(Math.max(progress, 0))}%`}
        </span>
        {label && (
          <span className="text-[11px] font-medium text-[#64748B] mt-0.5 leading-none">
            {label}
          </span>
        )}
      </div>
    </div>
  );
}

export default ProgressRing;
