import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/utils/cn';

export function Tabs({
  tabs = [],
  activeTab,
  onChange,
  variant = 'pills', // 'pills' | 'underline'
  className,
}) {
  return (
    <div
      className={cn(
        'flex items-center',
        variant === 'pills' && 'bg-[#F1F5F9] p-1 rounded-xl gap-1',
        variant === 'underline' && 'border-b border-[#E2E8F0] gap-6',
        className
      )}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        const Icon = tab.icon;

        if (variant === 'pills') {
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onChange(tab.id)}
              className={cn(
                'relative px-3.5 py-1.5 text-small font-semibold rounded-lg transition-colors select-none flex items-center gap-2 cursor-pointer',
                isActive ? 'text-[#081226]' : 'text-[#64748B] hover:text-[#081226]'
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="active-tab-pill"
                  className="absolute inset-0 bg-white rounded-lg shadow-xs"
                  transition={{ type: 'spring', stiffness: 450, damping: 35 }}
                />
              )}
              <span className="relative z-10 flex items-center gap-2">
                {Icon && <Icon className="w-4 h-4" />}
                {tab.label}
                {tab.badge !== undefined && (
                  <span
                    className={cn(
                      'px-1.5 py-0.2 rounded-full text-[11px] font-bold',
                      isActive ? 'bg-[#2563EB]/10 text-[#2563EB]' : 'bg-[#E2E8F0] text-[#64748B]'
                    )}
                  >
                    {tab.badge}
                  </span>
                )}
              </span>
            </button>
          );
        }

        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={cn(
              'relative pb-3 text-small font-semibold transition-colors flex items-center gap-2 cursor-pointer',
              isActive ? 'text-[#2563EB]' : 'text-[#64748B] hover:text-[#081226]'
            )}
          >
            {Icon && <Icon className="w-4 h-4" />}
            {tab.label}
            {tab.badge !== undefined && (
              <span
                className={cn(
                  'px-1.5 py-0.2 rounded-full text-[11px] font-bold',
                  isActive ? 'bg-[#2563EB]/10 text-[#2563EB]' : 'bg-[#F1F5F9] text-[#64748B]'
                )}
              >
                {tab.badge}
              </span>
            )}
            {isActive && (
              <motion.div
                layoutId="active-tab-underline"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#2563EB] rounded-full"
                transition={{ type: 'spring', stiffness: 450, damping: 35 }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}

export default Tabs;
