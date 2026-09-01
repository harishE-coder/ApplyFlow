/**
 * ApplyFlow Service Worker (v1.2.0)
 * Features:
 * - Service Worker Versioning & SkipWaiting
 * - Notification Collapse (tag: room-${roomId})
 * - Offline Unread Count Badges
 * - Actionable Notification Buttons (Reply, Open Chat)
 * - Deep Link Tab Focusing and Navigation on click
 */

const SW_VERSION = '1.2.0';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
  if (!event.data) {
    return;
  }

  try {
    const data = event.data.json();
    const roomId = data.room_id || data.room;
    const senderName = data.sender_name || 'ApplyFlow Chat';
    const preview = data.preview || data.body || 'You received a new message.';
    const unreadCount = data.unread_count || 1;

    let title = data.title;
    let body = preview;

    if (!title) {
      if (unreadCount > 1) {
        title = `${senderName} (${unreadCount} new messages)`;
        body = `${senderName} • ${unreadCount} unread messages\n${preview}`;
      } else {
        title = `New message from ${senderName}`;
        body = preview;
      }
    }

    const options = {
      body,
      icon: '/logo192.png',
      badge: '/badge.png',
      data: {
        room_id: roomId,
        url: roomId ? `/chats/${roomId}` : '/chats',
        sent_at: data.sent_at,
        unread_count: unreadCount,
        sw_version: SW_VERSION,
      },
      tag: roomId ? `room-${roomId}` : 'applyflow-chat',
      renotify: true,
      vibrate: [200, 100, 200],
      actions: [
        { action: 'reply', title: '💬 Reply' },
        { action: 'open', title: 'Open Chat' },
      ],
    };

    event.waitUntil(self.registration.showNotification(title, options));
  } catch (err) {
    console.error('[ServiceWorker] Failed to display push notification:', err);
  }
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const roomData = event.notification.data || {};
  let targetUrl = roomData.url || (roomData.room_id ? `/chats/${roomData.room_id}` : '/chats');

  // Handle action buttons
  if (event.action === 'reply' && roomData.room_id) {
    targetUrl = `/chats/${roomData.room_id}?reply=1`;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // 1. If an existing ApplyFlow tab is open, focus and navigate it
      for (const client of windowClients) {
        if ('focus' in client) {
          if ('navigate' in client) {
            client.navigate(targetUrl);
          }
          return client.focus();
        }
      }

      // 2. Otherwise open a new window
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});
