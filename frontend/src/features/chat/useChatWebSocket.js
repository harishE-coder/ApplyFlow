import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * Production-grade hook for managing real-time WebSocket connection to a chat room.
 * Stores event callbacks in useRef to prevent reconnection storms on React re-renders.
 * Features exponential backoff with ±20% jitter and full message lifecycle support.
 */
export function useChatWebSocket(roomId, callbacks = {}) {
  const callbacksRef = useRef(callbacks);
  useEffect(() => {
    callbacksRef.current = callbacks;
  }, [callbacks]);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const isManuallyClosedRef = useRef(false);

  const [isConnected, setIsConnected] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [typingUsers, setTypingUsers] = useState({});

  useEffect(() => {
    if (!roomId) {
      setIsConnected(false);
      setOnlineUsers([]);
      setTypingUsers({});
      return;
    }

    isManuallyClosedRef.current = false;
    reconnectAttemptsRef.current = 0;

    function connect() {
      if (isManuallyClosedRef.current) return;

      // Close any previous socket cleanly
      if (wsRef.current) {
        try {
          wsRef.current.onclose = null;
          wsRef.current.onerror = null;
          wsRef.current.close();
        } catch {
          // ignore
        }
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
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
              callbacksRef.current.onMessage?.(data.message);
            } else if (data.type === 'message_status') {
              callbacksRef.current.onMessageStatus?.(data);
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
              callbacksRef.current.onTyping?.(data);
            } else if (data.type === 'read_receipt') {
              callbacksRef.current.onReadReceipt?.(data);
            } else if (data.type === 'presence') {
              if (data.online_users) {
                setOnlineUsers(data.online_users);
              }
              callbacksRef.current.onPresence?.(data);
            } else if (data.type === 'message_deleted') {
              callbacksRef.current.onMessageDeleted?.(data);
            }
          } catch (err) {
            console.error('Error parsing WS message:', err);
          }
        };

        ws.onclose = (event) => {
          setIsConnected(false);
          // Do not reconnect on intentional auth closure (4001, 4003) or unmount
          if (!isManuallyClosedRef.current && event.code !== 4001 && event.code !== 4003 && roomId) {
            const attempt = reconnectAttemptsRef.current;
            const baseDelay = Math.min(1000 * Math.pow(2, attempt), 30000);
            const jitter = (Math.random() * 0.4 - 0.2) * baseDelay; // ±20% jitter
            const delay = Math.max(500, Math.round(baseDelay + jitter));

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
    }

    connect();

    return () => {
      isManuallyClosedRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        try {
          wsRef.current.onclose = null;
          wsRef.current.onerror = null;
          wsRef.current.close();
        } catch {
          // ignore
        }
      }
      setTypingUsers({});
      setIsConnected(false);
    };
  }, [roomId]);

  // Send helpers
  const sendMessage = useCallback((text, clientId = null) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', text, client_id: clientId }));
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
