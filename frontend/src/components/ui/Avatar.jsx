import React from 'react';
import { getInitials, cn } from '@/utils/cn';

export function Avatar({
  name = '',
  src,
  size = 'md', // 'xs' (24px) | 'sm' (32px) | 'md' (40px) | 'lg' (48px) | 'xl' (56px)
  className,
  status, // 'online' | 'offline' | 'busy'
  variant = 'blue', // 'blue' | 'navy' | 'orange' | 'gray'
}) {
  const sizeMap = {
    xs: 'w-6 h-6 text-[10px]',
    sm: 'w-8 h-8 text-[12px]',
    md: 'w-10 h-10 text-[14px]',
    lg: 'w-12 h-12 text-[16px]',
    xl: 'w-14 h-14 text-[18px]',
  };

  const variantMap = {
    blue: 'bg-[#EFF6FF] text-[#2563EB] border-[#BFDBFE]',
    navy: 'bg-[#081226] text-white border-[#1E2E4E]',
    orange: 'bg-[#FFF7ED] text-[#F97316] border-[#FFEDD5]',
    gray: 'bg-[#F1F5F9] text-[#475569] border-[#E2E8F0]',
    purple: 'bg-[#FAF5FF] text-[#9333EA] border-[#E9D5FF]',
  };

  const statusDot = {
    online: 'bg-[#16A34A] ring-white',
    offline: 'bg-[#94A3B8] ring-white',
    busy: 'bg-[#EF4444] ring-white',
  };

  const initials = getInitials(name);

  return (
    <div className="relative inline-flex shrink-0">
      {src ? (
        <img
          src={src}
          alt={name}
          className={cn(
            'rounded-full object-cover border border-[#E2E8F0] shadow-2xs select-none',
            sizeMap[size],
            className
          )}
        />
      ) : (
        <div
          className={cn(
            'rounded-full flex items-center justify-center font-bold tracking-tight border shadow-2xs select-none',
            sizeMap[size],
            variantMap[variant],
            className
          )}
        >
          {initials}
        </div>
      )}

      {status && (
        <span
          className={cn(
            'absolute bottom-0 right-0 block rounded-full ring-2',
            size === 'xs' || size === 'sm' ? 'w-2 h-2 ring-1' : 'w-2.5 h-2.5',
            statusDot[status]
          )}
        />
      )}
    </div>
  );
}

export default Avatar;
