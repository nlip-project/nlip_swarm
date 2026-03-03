import React from 'react';
import { Image, StyleSheet, View } from 'react-native';
import FilePreview from '@/components/FilePreview';
import { Colors } from '@/constants/theme';

type ThemeShape = typeof Colors.light;

interface FileMeta {
  uri: string | null;
  name: string | null;
  size: number | null;
  type?: string | null;
}

interface SelectedAttachmentProps {
  imageUri?: string | null;
  file?: FileMeta;
  colors: ThemeShape;
  onRemoveFile: () => void;
}

export function SelectedAttachment({ imageUri, file, colors, onRemoveFile }: SelectedAttachmentProps) {
  if (!imageUri && !(file && file.uri && file.name)) {
    return null;
  }

  return (
    <View style={styles.wrapper}>
      {imageUri ? <Image source={{ uri: imageUri }} style={styles.preview} /> : null}
      {file && file.uri && file.name ? (
        <FilePreview
          fileName={file.name}
          fileSize={file.size}
          c={colors}
          onRemove={onRemoveFile}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    width: '100%',
    paddingHorizontal: 12,
  },
  preview: {
    width: 120,
    height: 90,
    borderRadius: 8,
    marginBottom: 8,
  },
});
