import React, { useMemo } from 'react';
import { ActivityIndicator, Image, StyleSheet, TouchableOpacity, View } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { Colors } from '@/constants/theme';
import { Ionicons } from '@expo/vector-icons';

type ThemeColors = typeof Colors.light;

interface AvatarPickerProps {
  uri: string | null;
  name: string;
  colors: ThemeColors;
  onPress: () => void;
  isProcessing?: boolean;
}

export function AvatarPicker({ uri, name, colors, onPress, isProcessing }: AvatarPickerProps) {
  const initials = useMemo(() => {
    return name
      .split(' ')
      .map((part) => part.trim().charAt(0))
      .filter(Boolean)
      .join('')
      .toUpperCase();
  }, [name]);

  return (
    <View style={styles.wrapper}>
      <TouchableOpacity
        style={[styles.avatar, { borderColor: colors.icon }]}
        onPress={onPress}
        accessibilityLabel="Change profile photo"
        activeOpacity={0.8}
      >
        {uri ? (
          <Image source={{ uri }} style={styles.avatarImage} />
        ) : initials ? (
          <ThemedText style={styles.avatarInitials}>{initials}</ThemedText>
        ) : (
          <Ionicons name="person" size={56} color={colors.icon} />
        )}
        {isProcessing ? (
          <View style={styles.processingOverlay}>
            <ActivityIndicator color="#fff" />
          </View>
        ) : null}
      </TouchableOpacity>
      <TouchableOpacity onPress={onPress} accessibilityRole="button">
        <ThemedText type="link">Change Photo</ThemedText>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'center',
    gap: 12,
  },
  avatar: {
    width: 120,
    height: 120,
    borderRadius: 60,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  avatarImage: {
    width: '100%',
    height: '100%',
  },
  avatarInitials: {
    fontSize: 36,
    lineHeight: 42,
    textAlign: 'center',
  },
  processingOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.45)',
    justifyContent: 'center',
    alignItems: 'center',
  },
});
