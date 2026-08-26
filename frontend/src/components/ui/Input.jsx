import React, { forwardRef } from 'react';
import { cn } from '@/utils/cn';

export const Input = forwardRef(({
  label,
  error,
  helperText,
  icon: Icon,
  iconRight: IconRight,
  className,
  containerClassName,
  type = 'text',
  disabled = false,
  required = false,
  id,
  ...props
}, ref) => {
  const inputId = id || (label ? `input-${label.toLowerCase().replace(/\s+/g, '-')}` : undefined);

  return (
    <div className={cn('w-full flex flex-col gap-1.5', containerClassName)}>
      {label && (
        <label
          htmlFor={inputId}
          className="text-small font-medium text-[#081226] flex items-center justify-between"
        >
          <span>
            {label} {required && <span className="text-[#EF4444]">*</span>}
          </span>
        </label>
      )}

      <div className="relative flex items-center w-full">
        {Icon && (
          <div className="absolute left-3.5 flex items-center pointer-events-none text-[#94A3B8]">
            <Icon className="w-5 h-5" />
          </div>
        )}

        <input
          ref={ref}
          id={inputId}
          type={type}
          disabled={disabled}
          required={required}
          className={cn(
            'w-full h-[48px] px-4 rounded-xl text-small bg-white text-[#081226] placeholder-[#94A3B8]',
            'border border-[#E2E8F0] shadow-xs transition-all duration-150',
            'hover:border-[#CBD5E1]',
            'focus:outline-none focus:border-[#2563EB] focus:ring-4 focus:ring-[#2563EB]/10',
            'disabled:bg-[#F8FAFC] disabled:text-[#94A3B8] disabled:cursor-not-allowed',
            Icon && 'pl-11',
            IconRight && 'pr-11',
            error && 'border-[#EF4444] focus:border-[#EF4444] focus:ring-[#EF4444]/10',
            className
          )}
          {...props}
        />

        {IconRight && (
          <div className="absolute right-3.5 flex items-center pointer-events-none text-[#94A3B8]">
            <IconRight className="w-5 h-5" />
          </div>
        )}
      </div>

      {error ? (
        <p className="text-caption font-medium text-[#EF4444] mt-0.5">{error}</p>
      ) : helperText ? (
        <p className="text-caption text-[#64748B] mt-0.5">{helperText}</p>
      ) : null}
    </div>
  );
});

Input.displayName = 'Input';
export default Input;
