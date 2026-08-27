import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';
import { cn } from '@/utils/cn';

const ToastContext = createContext(null);

function formatToastMessage(msg) {
  if (!msg) return '';
  if (typeof msg === 'string') return msg;
  if (Array.isArray(msg)) {
    return msg
      .map((item) => {
        if (typeof item === 'string') return item;
        if (item && item.msg) {
          const loc = item.loc ? `${item.loc.filter((l) => l !== 'body').join('.')}: ` : '';
          return `${loc}${item.msg}`;
        }
        return JSON.stringify(item);
      })
      .join('; ');
  }
  if (typeof msg === 'object') {
    if (msg.msg) return msg.msg;
    if (msg.detail) return formatToastMessage(msg.detail);
    if (msg.message) return msg.message;
    return JSON.stringify(msg);
  }
  return String(msg);
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(({ title, message, type = 'info', duration = 4000 }) => {
    const formattedTitle = formatToastMessage(title);
    const formattedMessage = formatToastMessage(message);
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, title: formattedTitle, message: formattedMessage, type }]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }
    return id;
  }, [removeToast]);

  const success = useCallback((title, message) => addToast({ title, message, type: 'success' }), [addToast]);
  const error = useCallback((title, message) => addToast({ title, message, type: 'error' }), [addToast]);
  const warning = useCallback((title, message) => addToast({ title, message, type: 'warning' }), [addToast]);
  const info = useCallback((title, message) => addToast({ title, message, type: 'info' }), [addToast]);

  const value = useMemo(
    () => ({ addToast, removeToast, success, error, warning, info }),
    [addToast, removeToast, success, error, warning, info]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2.5 pointer-events-none max-w-sm w-full">
        <AnimatePresence>
          {toasts.map((toast) => (
            <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

function ToastItem({ toast, onClose }) {
  const icons = {
    success: <CheckCircle2 className="w-5 h-5 text-[#16A34A] shrink-0" />,
    error: <AlertCircle className="w-5 h-5 text-[#EF4444] shrink-0" />,
    warning: <AlertTriangle className="w-5 h-5 text-[#F59E0B] shrink-0" />,
    info: <Info className="w-5 h-5 text-[#2563EB] shrink-0" />,
  };

  const borderColors = {
    success: 'border-l-4 border-l-[#16A34A]',
    error: 'border-l-4 border-l-[#EF4444]',
    warning: 'border-l-4 border-l-[#F59E0B]',
    info: 'border-l-4 border-l-[#2563EB]',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.15 } }}
      className={cn(
        'pointer-events-auto bg-white rounded-xl shadow-2xl border border-[#E2E8F0] p-4 flex items-start justify-between gap-3 overflow-hidden',
        borderColors[toast.type]
      )}
    >
      <div className="flex items-start gap-3">
        {icons[toast.type]}
        <div>
          {toast.title && <h5 className="text-small font-semibold text-[#081226] leading-tight">{toast.title}</h5>}
          {toast.message && <p className="text-caption text-[#64748B] mt-0.5 leading-relaxed">{toast.message}</p>}
        </div>
      </div>

      <button
        type="button"
        onClick={onClose}
        className="p-1 text-[#94A3B8] hover:text-[#081226] rounded-md transition-colors"
      >
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  );
}

export default ToastProvider;
