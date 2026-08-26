import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * Hook for managing real-time WebSocket connection to a chat room.
 * Supports auto-reconnect with exponential backoff, typing indicators,
 * real-time messages, read receipts, and online status.
 */
export function useChatWebSocket(roomId, { onMessage, onTyping, onReadReceipt, onPresence } = {}) {
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [typingUsers, setTypingUsers] = useState({});

  const connect = useCallback(() => {
    if (!roomId) return;

    // Clean existing
    if (wsRef.current) {
      wsRef.current.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host; // Vite proxy handles /ws -> http://localhost:8000
    const wsUrl = `${protocol}//${host}/ws/chat/${roomId}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'new_message') {
            if (onMessage) onMessage(data.message);
          } else if (data.type === 'typing') {
            setTypingUsers((prev) => {
              if (data.is_typing) {
                return { ...prev, [data.user_id]: data.user_name };
              } else {
                const next = { ...prev };
                delete next[data.user_id];
                return next;
              }
            });
            if (onTyping) onTyping(data);
          } else if (data.type === 'read_receipt') {
            if (onReadReceipt) onReadReceipt(data);
          } else if (data.type === 'presence') {
            if (data.online_users) {
              setOnlineUsers(data.online_users);
            }
            if (onPresence) onPresence(data);
          }
        } catch (err) {
          console.error('Error parsing WS message:', err);
        }
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        // Do not reconnect on intentional close (e.g. 4001, 4003)
        if (event.code !== 4001 && event.code !== 4003 && roomId) {
          const delay = Math.min(1000 * 2 ** reconnectAttemptsRef.current, 15000);
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };

      ws.onerror = () => {
        setIsConnected(false);
      };
    } catch (err) {
      console.error('WS Connection error:', err);
    }
  }, [roomId, onMessage, onTyping, onReadReceipt, onPresence]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
      setTypingUsers({});
    };
  }, [roomId, connect]);

  // Send helpers
  const sendMessage = useCallback((text) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', text }));
      return true;
    }
    return false;
  }, []);

  const sendTyping = useCallback((isTyping) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'typing', is_typing: isTyping }));
    }
  }, []);

  const sendRead = useCallback((messageId) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'read', message_id: messageId }));
    }
  }, []);

  return {
    isConnected,
    onlineUsers,
    typingUsers,
    sendMessage,
    sendTyping,
    sendRead,
  };
}
