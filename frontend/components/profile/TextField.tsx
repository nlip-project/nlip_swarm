import React from 'react';
import { StyleSheet, TextInput, TextInputProps, View, ViewStyle } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { Colors } from '@/constants/theme';

type ThemeColors = typeof Colors.light;

type ProfileTextFieldProps = TextInputProps & {
  label: string;
  colors: ThemeColors;
  theme: 'light' | 'dark';
  containerStyle?: ViewStyle;
};

export function ProfileTextField({
  label,
  colors,
  theme,
  containerStyle,
  ...inputProps
}: ProfileTextFieldProps) {
  const placeholderColor = theme === 'dark' ? Colors.dark.icon : Colors.light.icon;

  return (
    <View style={[styles.fieldGroup, containerStyle]}>
      <ThemedText>{label}</ThemedText>
      <TextInput
        placeholderTextColor={placeholderColor}
        style={[
          styles.input,
          {
            color: colors.text,
            borderColor: colors.icon,
            backgroundColor: colors.background,
          },
        ]}
        {...inputProps}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  fieldGroup: {
    gap: 6,
  },
  input: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
});
