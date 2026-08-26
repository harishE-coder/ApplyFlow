import React from 'react';
import { cn } from '@/utils/cn';

export function Card({
  children,
  className,
  header,
  footer,
  action,
  title,
  subtitle,
  hoverable = false,
  onClick,
  ...props
}) {
  return (
    <div
      onClick={onClick}
      className={cn(
        'bg-white rounded-2xl border border-[#E2E8F0] shadow-card transition-all duration-150',
        hoverable && 'hover:shadow-card-hover hover:border-[#CBD5E1] cursor-pointer',
        className
      )}
      {...props}
    >
      {(title || header || action) && (
        <div className="px-6 pt-6 pb-4 flex items-center justify-between gap-4 border-b border-[#F1F5F9]">
          {header || (
            <div>
              {title && <h3 className="text-h3 font-semibold text-[#081226] tracking-tight">{title}</h3>}
              {subtitle && <p className="text-small text-[#64748B] mt-0.5">{subtitle}</p>}
            </div>
          )}
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}

      <div className={cn('p-6', (title || header) && 'pt-5')}>{children}</div>

      {footer && (
        <div className="px-6 py-4 bg-[#F8FAFC]/70 border-t border-[#F1F5F9] rounded-b-2xl flex items-center justify-between">
          {footer}
        </div>
      )}
    </div>
  );
}

export default Card;
