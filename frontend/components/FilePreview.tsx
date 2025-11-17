import React from 'react';
import { View, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { ThemedText } from '@/components/themed-text';
import { formatFileSize } from './utils';

export default function FilePreview({ fileName, fileSize, onRemove, c }: { fileName: string; fileSize?: number | null; onRemove: () => void; c: any }) {
  return (
    <View style={[styles.filePreview, { backgroundColor: c.messageMeBg, borderColor: c.icon }]}> 
      <Ionicons name="document" size={32} color={c.messageMeText} />
      <View style={styles.fileInfo}>
        <ThemedText style={[styles.fileName, { color: c.messageMeText }]}>{fileName}</ThemedText>
        {fileSize !== null && fileSize !== undefined ? (
          <ThemedText style={[styles.fileSize, { color: c.messageMeText }]}>{formatFileSize(fileSize)}</ThemedText>
        ) : null}
      </View>
      <TouchableOpacity onPress={onRemove} accessibilityLabel="Remove file">
        <Ionicons name="close-circle" size={24} color={c.messageMeText} />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  filePreview: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    marginHorizontal: 12,
    marginBottom: 8,
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
});
