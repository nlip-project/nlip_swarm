import React from 'react';
import { StyleSheet, TouchableOpacity, View } from 'react-native';
import { ThemedText } from '@/components/themed-text';

interface ProfileActionsProps {
  onSave: () => void;
  onLogout: () => void;
  tintColor: string;
  disabled?: boolean;
}

export function ProfileActions({ onSave, onLogout, tintColor, disabled }: ProfileActionsProps) {
  return (
    <View style={styles.actionsContainer}>
      <TouchableOpacity
        onPress={onSave}
        style={[styles.primaryButton, { backgroundColor: tintColor, opacity: disabled ? 0.5 : 1 }]}
        accessibilityLabel="Save profile"
        disabled={disabled}
      >
        <ThemedText style={styles.primaryButtonText}>Save</ThemedText>
      </TouchableOpacity>
      <TouchableOpacity
        onPress={onLogout}
        style={styles.destructiveButton}
        accessibilityLabel="Log out"
      >
        <ThemedText style={styles.destructiveButtonText}>Log out</ThemedText>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  actionsContainer: {
    marginTop: 8,
    alignItems: 'center',
    width: '100%',
    gap: 8,
  },
  primaryButton: {
    paddingVertical: 12,
    paddingHorizontal: 28,
    borderRadius: 12,
    minWidth: 160,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  destructiveButton: {
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: 'center',
    width: 160,
    borderColor: '#d9534f',
  },
  destructiveButtonText: {
    color: '#d9534f',
    fontWeight: '600',
  },
});
