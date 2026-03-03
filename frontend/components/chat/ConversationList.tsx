import React from 'react';
import { FlatList, StyleSheet } from 'react-native';
import MessageRow from '@/components/MessageRow';
import { Colors } from '@/constants/theme';
import type { Message } from '@/types/chat';

type ThemeShape = typeof Colors.light;

interface ConversationListProps {
  messages: Message[];
  listRef: React.MutableRefObject<FlatList<Message> | null>;
  colors: ThemeShape;
  isWeb: boolean;
}

export function ConversationList({ messages, listRef, colors, isWeb }: ConversationListProps) {
  return (
    <FlatList
      ref={listRef}
      style={styles.list}
      data={messages}
      keyExtractor={(item) => item.id}
      inverted={!isWeb}
      nestedScrollEnabled
      keyboardShouldPersistTaps="handled"
      {...(!isWeb ? { maintainVisibleContentPosition: { minIndexForVisible: 0 } } : {})}
      contentContainerStyle={[
        styles.contentContainer,
        messages.length === 0 ? styles.emptyListContainer : undefined,
      ]}
      renderItem={({ item }) => <MessageRow item={item} c={colors} />}
    />
  );
}

const styles = StyleSheet.create({
  list: {
    flex: 1,
    paddingHorizontal: 12,
  },
  contentContainer: {
    flexGrow: 1,
  },
  emptyListContainer: {
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
