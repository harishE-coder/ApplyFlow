import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/utils/cn';

export function BrandedLoader({ size = 'md', label = 'Loading ApplyFlow ATS...' }) {
  const sizeMap = {
    sm: 'w-8 h-8 border-2',
    md: 'w-12 h-12 border-3',
    lg: 'w-16 h-16 border-4',
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 select-none">
      <div className="relative flex items-center justify-center">
        {/* Outer Navy Squircle Base */}
        <div className="w-14 h-14 rounded-2xl bg-[#081226] flex items-center justify-center shadow-xl border border-[#1E2E4E]">
          {/* Rotating Bright Blue / Orange Ring */}
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 1.1, ease: 'linear' }}
            className={cn(
              'rounded-full border-t-[#0D6EFD] border-r-[#FF8A00] border-b-transparent border-l-transparent',
              sizeMap[size] || sizeMap.md
            )}
          />
        </div>
      </div>

      {label && (
        <p className="mt-4 text-small font-semibold text-[#081226] tracking-tight animate-pulse">
          {label}
        </p>
      )}
    </div>
  );
}

export default BrandedLoader;
