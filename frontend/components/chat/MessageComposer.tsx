import React from 'react';
import { StyleSheet, TextInput, TouchableOpacity, View } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { Colors } from '@/constants/theme';
import { getContrastingTextColor } from '@/lib/color';

type ThemeShape = typeof Colors.light;

type ThemeMode = 'light' | 'dark';

interface MessageComposerProps {
  text: string;
  onChangeText: (value: string) => void;
  onSend: () => void;
  onAttachPress: () => void;
  isSending: boolean;
  colors: ThemeShape;
  theme: ThemeMode;
}

export function MessageComposer({
  text,
  onChangeText,
  onSend,
  onAttachPress,
  isSending,
  colors,
  theme,
}: MessageComposerProps) {
  const sendTextColor = getContrastingTextColor(colors.tint, colors.buttonText, colors.text);

  return (
    <View
      style={[
        styles.inputRow,
        { backgroundColor: colors.background, borderColor: colors.icon },
      ]}
    >
      <TouchableOpacity
        style={[styles.plusButton, { borderColor: colors.icon }]}
        onPress={onAttachPress}
        accessibilityLabel="Attach image"
      >
        <ThemedText style={styles.plusText}>+</ThemedText>
      </TouchableOpacity>

      <TextInput
        value={text}
        onChangeText={onChangeText}
        placeholder="Message"
        style={[styles.textInput, { color: colors.text }]}
        keyboardAppearance={theme}
        placeholderTextColor={
          theme === 'dark' ? Colors.dark.icon : Colors.light.icon
        }
        returnKeyType="send"
        onSubmitEditing={onSend}
        blurOnSubmit={false}
      />

      <TouchableOpacity
        style={[styles.sendButton, { backgroundColor: colors.tint }]}
        onPress={onSend}
        accessibilityLabel="Send message"
      >
        <ThemedText style={[styles.sendButtonText, { color: sendTextColor }]}>
          {isSending ? '...' : 'Send'}
        </ThemedText>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'center',
    width: '94%',
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: 24,
    borderWidth: 1,
    marginBottom: 8,
  },
  plusButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  plusText: {
    fontSize: 22,
    lineHeight: 22,
  },
  textInput: {
    flex: 1,
    height: 40,
  },
  sendButton: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    marginLeft: 6,
    borderRadius: 16,
  },
  sendButtonText: {
    fontSize: 15,
    lineHeight: 18,
    fontWeight: '600',
  },
});
