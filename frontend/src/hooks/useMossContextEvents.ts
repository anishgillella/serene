import { useEffect, useState, useCallback } from 'react';
import { Room, RoomEvent } from 'livekit-client';

export interface MossMatch {
  text: string;
  score?: number;
  metadata?: Record<string, string>;
}

export interface MossContextEvent {
  query: string;
  matches: MossMatch[];
  time_taken_ms?: number;
  timestamp: number;
}

export function useMossContextEvents(room: Room | null) {
  const [events, setEvents] = useState<MossContextEvent[]>([]);
  const [latest, setLatest] = useState<MossContextEvent | null>(null);

  const handleData = useCallback((payload: Uint8Array) => {
    try {
      const parsed = JSON.parse(new TextDecoder().decode(payload));
      if (parsed.type !== 'moss_context' || !parsed.data) return;

      const data = parsed.data;
      const event: MossContextEvent = {
        query: data.query || '',
        matches: data.matches || [],
        time_taken_ms: data.time_taken_ms,
        timestamp: (data.timestamp || 0) * 1000,
      };

      setLatest(event);
      setEvents((prev) => [event, ...prev].slice(0, 20));
    } catch {
      // ignore non-JSON data packets
    }
  }, []);

  useEffect(() => {
    if (!room) return;

    const onData = (payload: Uint8Array) => handleData(payload);

    room.on(RoomEvent.DataReceived, onData);
    return () => {
      room.off(RoomEvent.DataReceived, onData);
    };
  }, [room, handleData]);

  const clear = useCallback(() => {
    setEvents([]);
    setLatest(null);
  }, []);

  return { events, latest, clear };
}
