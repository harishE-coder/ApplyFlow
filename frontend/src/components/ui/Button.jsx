import React, { forwardRef } from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { cn } from '@/utils/cn';

export const Button = forwardRef(({
  children,
  className,
  variant = 'primary', // 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'orange'
  size = 'md', // 'sm' (36px), 'md' (44px standard), 'lg' (48px), 'icon' (40px)
  isLoading = false,
  disabled = false,
  icon: Icon,
  iconPosition = 'left',
  type = 'button',
  onClick,
  ...props
}, ref) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium transition-all duration-120 rounded-xl cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2';

  const variants = {
    primary: 'bg-[#2563EB] text-white hover:bg-[#1D4ED8] active:bg-[#1E40AF] shadow-sm hover:shadow focus-visible:ring-[#2563EB]',
    secondary: 'bg-[#EFF6FF] text-[#2563EB] hover:bg-[#DBEAFE] active:bg-[#BFDBFE] border border-[#BFDBFE]/60 focus-visible:ring-[#2563EB]',
    outline: 'bg-white text-[#081226] border border-[#E2E8F0] hover:bg-[#F8FAFC] hover:border-[#CBD5E1] active:bg-[#F1F5F9] focus-visible:ring-[#2563EB] shadow-xs',
    ghost: 'bg-transparent text-[#475569] hover:bg-[#F1F5F9] hover:text-[#081226] active:bg-[#E2E8F0] focus-visible:ring-[#2563EB]',
    danger: 'bg-[#EF4444] text-white hover:bg-[#DC2626] active:bg-[#B91C1C] focus-visible:ring-[#EF4444] shadow-sm',
    orange: 'bg-[#F97316] text-white hover:bg-[#EA580C] active:bg-[#C2410C] focus-visible:ring-[#F97316] shadow-sm',
    dark: 'bg-[#081226] text-white hover:bg-[#101F3D] active:bg-[#040A17] border border-[#1E2E4E] focus-visible:ring-[#081226]',
  };

  const sizes = {
    sm: 'h-[36px] px-3.5 text-small gap-1.5 rounded-lg',
    md: 'h-[44px] px-4 text-small font-semibold gap-2 rounded-xl',
    lg: 'h-[48px] px-6 text-body font-semibold gap-2.5 rounded-xl',
    icon: 'h-[40px] w-[40px] p-0 rounded-xl',
  };

  return (
    <motion.button
      ref={ref}
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      whileTap={{ scale: disabled || isLoading ? 1 : 0.98 }}
      transition={{ duration: 0.1 }}
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin shrink-0" />
      ) : (
        <>
          {Icon && iconPosition === 'left' && <Icon className="w-4 h-4 shrink-0" />}
          {children}
          {Icon && iconPosition === 'right' && <Icon className="w-4 h-4 shrink-0" />}
        </>
      )}
    </motion.button>
  );
});

Button.displayName = 'Button';
export default Button;
