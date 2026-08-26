import React, { useState, useEffect, useCallback } from 'react';
import { ChatRoomList } from './ChatRoomList';
import { ChatWindow } from './ChatWindow';
import { useChatWebSocket } from './useChatWebSocket';
import { useToast } from '@/components/ui/Toast';
import api from '@/services/api';
import { cn } from '@/utils/cn';

export function ChatPage() {
  const { error: toastError, success: toastSuccess } = useToast();
  const [rooms, setRooms] = useState([]);
  const [activeRoomId, setActiveRoomId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingRooms, setLoadingRooms] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [isMobileViewingChat, setIsMobileViewingChat] = useState(false);

  // Fetch all accessible rooms
  const fetchRooms = useCallback(async () => {
    try {
      const res = await api.get('/chat/rooms');
      const items = res.data.items || [];
      setRooms(items);
      if (items.length > 0 && !activeRoomId && window.innerWidth >= 768) {
        setActiveRoomId(items[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch chat rooms:', err);
    } finally {
      setLoadingRooms(false);
    }
  }, [activeRoomId]);

  useEffect(() => {
    fetchRooms();
  }, [fetchRooms]);

  // Fetch messages when active room changes
  const fetchMessages = useCallback(async (roomId) => {
    if (!roomId) return;
    setLoadingMessages(true);
    try {
      const res = await api.get(`/chat/rooms/${roomId}/messages?limit=50`);
      setMessages(res.data.items || []);

      // Mark read if there are messages
      const msgs = res.data.items || [];
      if (msgs.length > 0) {
        const lastMsg = msgs[msgs.length - 1];
        api.patch(`/chat/rooms/${roomId}/read`, { message_id: lastMsg.id }).catch(() => {});
        // Update local room unread count to 0
        setRooms((prev) =>
          prev.map((r) => (r.id === roomId ? { ...r, unread_count: 0 } : r))
        );
      }
    } catch (err) {
      console.error('Failed to fetch messages:', err);
      toastError('Failed to load messages');
    } finally {
      setLoadingMessages(false);
    }
  }, [toastError]);

  useEffect(() => {
    if (activeRoomId) {
      fetchMessages(activeRoomId);
    }
  }, [activeRoomId, fetchMessages]);

  // Handle incoming real-time WS message
  const handleIncomingMessage = useCallback(
    (newMsg) => {
      if (newMsg.room_id === activeRoomId) {
        setMessages((prev) => {
          if (prev.some((m) => m.id === newMsg.id)) return prev;
          return [...prev, newMsg];
        });
        api.patch(`/chat/rooms/${activeRoomId}/read`, { message_id: newMsg.id }).catch(() => {});
      }

      setRooms((prev) =>
        prev.map((r) => {
          if (r.id === newMsg.room_id) {
            return {
              ...r,
              last_message: newMsg.message,
              last_message_sender: newMsg.sender.name,
              last_message_at: newMsg.created_at,
              unread_count: r.id === activeRoomId ? 0 : r.unread_count + 1,
            };
          }
          return r;
        })
      );
    },
    [activeRoomId]
  );

  // Real-time WebSocket hook
  const {
    onlineUsers,
    typingUsers,
    sendTyping: wsSendTyping,
  } = useChatWebSocket(activeRoomId, {
    onMessage: handleIncomingMessage,
  });

  // Action handlers
  const handleSendMessage = async (text) => {
    if (!activeRoomId || !text.trim()) return;
    try {
      const res = await api.post(`/chat/rooms/${activeRoomId}/messages`, { message: text.trim() });
      const savedMsg = res.data;
      setMessages((prev) => {
        if (prev.some((m) => m.id === savedMsg.id)) return prev;
        return [...prev, savedMsg];
      });
      setRooms((prev) =>
        prev.map((r) =>
          r.id === activeRoomId
            ? {
                ...r,
                last_message: savedMsg.message,
                last_message_sender: savedMsg.sender.name,
                last_message_at: savedMsg.created_at,
              }
            : r
        )
      );
    } catch (err) {
      console.error('Failed to send message:', err);
      toastError('Failed to send message');
    }
  };

  const handleUploadAttachment = async (file) => {
    if (!activeRoomId || !file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await api.post(`/chat/rooms/${activeRoomId}/attachment`, formData);
      const savedMsg = res.data;
      setMessages((prev) => [...prev, savedMsg]);
      toastSuccess('Attachment uploaded and sent');
    } catch (err) {
      console.error('Failed to upload attachment:', err);
      toastError('Failed to upload file');
    }
  };

  const handleShareResume = async (resumeId) => {
    if (!activeRoomId || !resumeId) return;
    try {
      const res = await api.post(`/chat/rooms/${activeRoomId}/share-resume`, { resume_id: resumeId });
      const savedMsg = res.data;
      setMessages((prev) => [...prev, savedMsg]);
      toastSuccess('Resume shared to chat');
    } catch (err) {
      console.error('Failed to share resume:', err);
      toastError('Failed to share resume');
    }
  };

  const handleDeleteMessage = async (messageId) => {
    try {
      await api.delete(`/chat/messages/${messageId}`);
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, is_deleted: true, message: '[Message deleted]' } : m))
      );
      toastSuccess('Message deleted');
    } catch (err) {
      console.error('Failed to delete message:', err);
      toastError('Failed to delete message');
    }
  };

  const handleSelectRoom = (roomId) => {
    setActiveRoomId(roomId);
    setIsMobileViewingChat(true);
  };

  const activeRoom = rooms.find((r) => r.id === activeRoomId) || null;

  return (
    <div className="h-[calc(100vh-100px)] sm:h-[calc(100vh-130px)] min-h-[480px] flex rounded-2xl sm:rounded-3xl overflow-hidden border border-[#CBD5E1] shadow-xl bg-white relative">
      {/* Left Panel: Service Client Rooms */}
      <div
        className={cn(
          'w-full md:w-[320px] lg:w-[350px] shrink-0 h-full',
          isMobileViewingChat ? 'hidden md:flex' : 'flex'
        )}
      >
        <ChatRoomList
          rooms={rooms}
          activeRoomId={activeRoomId}
          onSelectRoom={handleSelectRoom}
          loading={loadingRooms}
        />
      </div>

      {/* Right Panel: Conversation Canvas (WhatsApp Mobile Style) */}
      <div
        className={cn(
          'flex-1 h-full min-w-0',
          !isMobileViewingChat ? 'hidden md:flex' : 'flex'
        )}
      >
        <ChatWindow
          room={activeRoom}
          messages={messages}
          onlineUsers={onlineUsers}
          typingUsers={typingUsers}
          onSendMessage={handleSendMessage}
          onUploadAttachment={handleUploadAttachment}
          onShareResume={handleShareResume}
          onDeleteMessage={handleDeleteMessage}
          onTypingChange={wsSendTyping}
          loadingMessages={loadingMessages}
          onBackMobile={() => setIsMobileViewingChat(false)}
        />
      </div>
    </div>
  );
}

export default ChatPage;
