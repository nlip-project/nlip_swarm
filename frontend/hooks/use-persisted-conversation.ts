import { useCallback, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import type { ConversationSummary } from '@/types/chat';

type RouterLike = {
  replace: (path: any) => void;
};

export function usePersistedConversation(router: RouterLike) {
  const [currentConversation, setCurrentConversation] = useState<ConversationSummary | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const storedUser = await AsyncStorage.getItem('user');
        if (mounted && !storedUser) {
          try {
            router.replace('/login');
          } catch {
            // ignore navigation errors
          }
          return;
        }
        if (!mounted) return;
        const storedConversation = await AsyncStorage.getItem('current_conversation');
        if (!storedConversation) return;
        try {
          const parsed = JSON.parse(storedConversation);
          if (parsed && parsed.id) {
            setCurrentConversation({ id: parsed.id, title: parsed.title ?? null });
            return;
          }
        } catch {
          // fallthrough to treat stored string as ID
        }
        setCurrentConversation({ id: storedConversation, title: null });
      } catch (e) {
        console.warn('Failed to load persisted conversation', e);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [router]);

  const persistConversationSelection = useCallback(async (conversation: ConversationSummary | null) => {
    try {
      if (!conversation) {
        await AsyncStorage.removeItem('current_conversation');
        setCurrentConversation(null);
        return;
      }
      await AsyncStorage.setItem('current_conversation', JSON.stringify(conversation));
      setCurrentConversation(conversation);
    } catch (e) {
      console.warn('Failed to persist conversation selection', e);
      setCurrentConversation(conversation);
    }
  }, []);

  return {
    currentConversation,
    setCurrentConversation,
    persistConversationSelection,
  } as const;
}
