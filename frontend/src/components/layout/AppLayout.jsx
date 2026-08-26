import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { CommandPalette } from '@/components/ui/CommandPalette';
import { useAuth } from '@/features/auth/AuthContext';
import api from '@/services/api';

export function AppLayout() {
  const { user } = useAuth();
  const location = useLocation();
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadChatCount, setUnreadChatCount] = useState(0);

  // Auto close mobile sidebar when route changes
  useEffect(() => {
    setIsMobileSidebarOpen(false);
  }, [location.pathname]);

  // Fetch notifications & chat unread counts
  const fetchNotifications = async () => {
    try {
      const res = await api.get('/notifications');
      setNotifications(res.data.items || []);
      setUnreadCount(res.data.unread_count || 0);
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
    }
  };

  const fetchChatUnread = async () => {
    try {
      const res = await api.get('/chat/unread-count');
      setUnreadChatCount(res.data.total_unread || 0);
    } catch (err) {
      // Quiet fail if not logged in
    }
  };

  useEffect(() => {
    fetchNotifications();
    fetchChatUnread();
    const interval = setInterval(() => {
      fetchNotifications();
      fetchChatUnread();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  // Global ⌘K keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="flex min-h-screen bg-[#F6F8FB] text-[#081226] antialiased overflow-x-hidden">
      {/* Sidebar (Desktop Sticky + Mobile/Tablet Off-Canvas Drawer) */}
      <Sidebar
        unreadNotificationsCount={unreadCount}
        unreadChatCount={unreadChatCount}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen w-full lg:pr-6 pb-6">
        {/* Top Bar */}
        <TopBar
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
          unreadCount={unreadCount}
          notifications={notifications}
          onRefreshNotifications={fetchNotifications}
          onToggleMobileSidebar={() => setIsMobileSidebarOpen((prev) => !prev)}
        />

        {/* Page View Container (Responsive Padding) */}
        <main className="flex-1 px-3 sm:px-5 lg:px-6 pb-8 overflow-y-auto w-full max-w-full">
          <Outlet />
        </main>
      </div>

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        userRole={user?.role}
      />
    </div>
  );
}

export default AppLayout;
