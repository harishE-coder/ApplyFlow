import React from 'react';
import { Bell, CheckCircle2, UserCheck, Target, Info } from 'lucide-react';
import { formatRelativeTime, cn } from '@/utils/cn';

export function NotificationItem({
  notification,
  onMarkRead,
  onClick,
  className,
}) {
  const icons = {
    client_assigned: <UserCheck className="w-4 h-4 text-[#2563EB]" />,
    target_achieved: <Target className="w-4 h-4 text-[#F97316]" />,
    success: <CheckCircle2 className="w-4 h-4 text-[#16A34A]" />,
    info: <Info className="w-4 h-4 text-[#2563EB]" />,
  };

  const bgIcons = {
    client_assigned: 'bg-[#EFF6FF]',
    target_achieved: 'bg-[#FFF7ED]',
    success: 'bg-[#F0FDF4]',
    info: 'bg-[#EFF6FF]',
  };

  const isUnread = !notification.is_read;

  return (
    <div
      onClick={() => {
        if (isUnread && onMarkRead) onMarkRead(notification.id);
        if (onClick) onClick(notification);
      }}
      className={cn(
        'p-3.5 rounded-xl transition-all duration-120 flex items-start gap-3 cursor-pointer select-none',
        isUnread ? 'bg-[#EFF6FF]/60 hover:bg-[#EFF6FF]' : 'hover:bg-[#F8FAFC]',
        className
      )}
    >
      <div
        className={cn(
          'w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5',
          bgIcons[notification.type] || 'bg-[#F1F5F9]'
        )}
      >
        {icons[notification.type] || <Bell className="w-4 h-4 text-[#64748B]" />}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p className={cn('text-small truncate', isUnread ? 'font-bold text-[#081226]' : 'font-medium text-[#334155]')}>
            {notification.title}
          </p>
          <span className="text-[11px] text-[#94A3B8] shrink-0">
            {formatRelativeTime(notification.created_at)}
          </span>
        </div>

        <p className="text-caption text-[#64748B] mt-0.5 line-clamp-2 leading-relaxed">
          {notification.message}
        </p>
      </div>

      {isUnread && (
        <span className="w-2 h-2 rounded-full bg-[#2563EB] shrink-0 self-center" />
      )}
    </div>
  );
}

export default NotificationItem;
