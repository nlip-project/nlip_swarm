import React from 'react';
import { View, Image, TouchableOpacity, StyleSheet, Alert, Linking, Platform } from 'react-native';
import Markdown from 'react-native-markdown-display';
import { Ionicons } from '@expo/vector-icons';
import { ThemedText } from '@/components/themed-text';
import { formatFileSize } from './utils';

type Message = {
  id: string;
  text?: string;
  imageUri?: string | null;
  fileUri?: string | null;
  fileName?: string | null;
  fileSize?: number | null;
  fileType?: string | null;
  timestamp: number;
  sender: 'me' | 'other';
};

function MessageRow({ item, c }: { item: Message; c: any }) {
  return (
    <View
      style={[
        styles.messageRow,
        item.sender === 'me' ? styles.rowMe : styles.rowOther,
      ]}
    >
      {item.sender === 'other' ? (
        <View style={[styles.avatar, { borderColor: c.icon, backgroundColor: c.background }]}> 
          <Ionicons name="person" size={18} color={c.icon} />
        </View>
      ) : null}

      <View
        style={[
          styles.bubble,
          {
            backgroundColor: item.sender === 'me' ? c.messageMeBg : c.messageOtherBg,
            borderColor: c.icon,
            borderWidth: 1,
          },
        ]}
      >
        {item.text ? (
          <Markdown
            style={{
              body: {
                color: item.sender === 'me' ? c.messageMeText : c.messageOtherText,
                fontSize: 16,
                lineHeight: 20,
                margin: 0,
                padding: 0,
              },
              paragraph: {
                marginTop: 0,
                marginBottom: 0,
              },
              text: {
                marginTop: 0,
                marginBottom: 0,
              },
              code_inline: {
                backgroundColor: item.sender === 'me' ? '#e6f2ff' : '#f3f3f3',
                paddingHorizontal: 6,
                paddingVertical: 0,
                borderRadius: 6,
                fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
              },
            }}
            rules={{
              fence: (node: any) => {
                const code = node.content || '';
                return (
                  <View key={node.key} style={{ marginVertical: 6 }}>
                    <ThemedText
                      style={[
                        styles.codeBlock,
                        { color: item.sender === 'me' ? c.messageMeText : c.messageOtherText, backgroundColor: item.sender === 'me' ? '#0b2f4a' : '#f3f3f3' },
                      ]}
                    >
                      {code}
                    </ThemedText>
                  </View>
                );
              },
            }}
          >
            {item.text}
          </Markdown>
        ) : null}

        {item.imageUri ? (
          <Image source={{ uri: item.imageUri }} style={styles.bubbleImage} />
        ) : null}

        {item.fileUri ? (
          <TouchableOpacity
            style={styles.fileAttachment}
            onPress={() => {
              void Linking.openURL(item.fileUri!).catch((err) => {
                console.error('Failed to open file:', err);
                Alert.alert('Error', 'Could not open file');
              });
            }}
          >
            <Ionicons
              name="document"
              size={24}
              color={item.sender === 'me' ? c.messageMeText : c.messageOtherText}
            />
            <View style={styles.fileInfo}>
              <ThemedText style={[styles.fileName, { color: item.sender === 'me' ? c.messageMeText : c.messageOtherText }]}>
                {item.fileName || 'Unknown file'}
              </ThemedText>
              {item.fileSize !== null && item.fileSize !== undefined ? (
                <ThemedText style={[styles.fileSize, { color: item.sender === 'me' ? c.messageMeText : c.messageOtherText }]}> 
                  {formatFileSize(item.fileSize)}
                </ThemedText>
              ) : null}
            </View>
          </TouchableOpacity>
        ) : null}
      </View>

      {item.sender === 'me' ? (
        <View style={[styles.avatar, { borderColor: c.icon, backgroundColor: c.background }]}> 
          <Ionicons name="person" size={18} color={c.icon} />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  messageRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 8,
  },
  rowMe: {
    alignSelf: 'flex-end',
  },
  rowOther: {
    alignSelf: 'flex-start',
  },
  avatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  bubble: {
    maxWidth: '80%',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginVertical: 4,
  },
  bubbleText: {
    fontSize: 16,
  },
  bubbleImage: {
    width: 160,
    height: 120,
    borderRadius: 8,
    marginTop: 6,
  },
  fileAttachment: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 8,
  },
  fileInfo: {
    flex: 1,
  },
  fileName: {
    fontSize: 14,
    fontWeight: '600',
  },
  fileSize: {
    fontSize: 12,
    marginTop: 2,
  },
  codeBlock: {
    fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }),
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    fontSize: 14,
    lineHeight: 18,
    overflow: 'hidden',
  },
});

export default MessageRow;
