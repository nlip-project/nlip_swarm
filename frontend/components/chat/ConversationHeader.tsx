import React from 'react';
import { StyleSheet, TouchableOpacity, View } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { Colors } from '@/constants/theme';
import type { ConversationSummary } from '@/types/chat';

type ThemeShape = typeof Colors.light;

interface ConversationHeaderProps {
  conversation: ConversationSummary | null;
  colors: ThemeShape;
  onToggle: () => void;
}

export function ConversationHeader({ conversation, colors, onToggle }: ConversationHeaderProps) {
  return (
    <View
      style={[
        styles.container,
        {
          borderColor: conversation ? colors.icon : 'transparent',
          borderBottomWidth: conversation ? StyleSheet.hairlineWidth : 0,
        },
      ]}
      accessibilityLabel={conversation ? 'Current conversation summary' : 'Conversation drawer'}
    >
      <TouchableOpacity
        onPress={onToggle}
        accessibilityLabel="Open conversation drawer"
        style={styles.hamburgerButton}
        activeOpacity={0.8}
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      >
        <View style={[styles.hamburgerLine, { backgroundColor: colors.icon }]} />
        <View style={[styles.hamburgerLine, { backgroundColor: colors.icon }]} />
        <View style={[styles.hamburgerLine, { backgroundColor: colors.icon }]} />
      </TouchableOpacity>
      <View style={styles.textWrapper}>
        {conversation ? (
          <>
            <ThemedText style={[styles.title, { color: colors.text }]}>
              {conversation.title?.trim() || 'Untitled conversation'}
            </ThemedText>
            <ThemedText style={[styles.subtitle, { color: colors.icon }]}>
              {`ID: ${conversation.id}`}
            </ThemedText>
          </>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    gap: 12,
  },
  hamburgerButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'transparent',
  },
  hamburgerLine: {
    width: 24,
    height: 3,
    borderRadius: 2,
    marginVertical: 2,
  },
  textWrapper: {
    flex: 1,
  },
  title: {
    fontSize: 18,
    fontWeight: '600',
  },
  subtitle: {
    fontSize: 12,
    marginTop: 4,
  },
});
