import React from 'react';
import { StyleSheet, TextInput, View } from 'react-native';
import { ThemedText } from '@/components/themed-text';
import { Colors } from '@/constants/theme';

type ThemeColors = typeof Colors.light;

interface PhoneFieldProps {
  colors: ThemeColors;
  theme: 'light' | 'dark';
  countryCode: string;
  phoneNumber: string;
  onCountryCodeChange: (value: string) => void;
  onPhoneNumberChange: (value: string) => void;
}

export function PhoneField({
  colors,
  theme,
  countryCode,
  phoneNumber,
  onCountryCodeChange,
  onPhoneNumberChange,
}: PhoneFieldProps) {
  const placeholderColor = theme === 'dark' ? Colors.dark.icon : Colors.light.icon;

  return (
    <View style={styles.fieldGroup}>
      <ThemedText>Phone Number</ThemedText>
      <View style={styles.phoneRow}>
        <View
          style={[
            styles.countryCodeInput,
            { borderColor: colors.icon, backgroundColor: colors.background },
          ]}
        >
          <ThemedText style={styles.plusSign}>+</ThemedText>
          <TextInput
            value={countryCode}
            onChangeText={onCountryCodeChange}
            placeholder="1"
            placeholderTextColor={placeholderColor}
            style={[styles.codeInput, { color: colors.text }]}
            keyboardType="number-pad"
            maxLength={3}
            returnKeyType="next"
          />
        </View>
        <TextInput
          value={phoneNumber}
          onChangeText={onPhoneNumberChange}
          placeholder="(123) 456-7890"
          placeholderTextColor={placeholderColor}
          style={[
            styles.phoneInput,
            {
              color: colors.text,
              borderColor: colors.icon,
              backgroundColor: colors.background,
            },
          ]}
          keyboardType="phone-pad"
          maxLength={14}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  fieldGroup: {
    gap: 6,
  },
  phoneRow: {
    flexDirection: 'row',
    gap: 8,
  },
  countryCodeInput: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
    minWidth: 70,
  },
  plusSign: {
    fontSize: 16,
    marginRight: 2,
  },
  codeInput: {
    fontSize: 16,
    minWidth: 30,
    padding: 0,
  },
  phoneInput: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
});
