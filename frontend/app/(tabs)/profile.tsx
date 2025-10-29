import * as ImagePicker from 'expo-image-picker';
import { useState } from 'react';
import {
  Alert,
  Image,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  TouchableWithoutFeedback,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { Ionicons } from '@expo/vector-icons';

export default function ProfileScreen() {
  const theme = useColorScheme() ?? 'light';
  const c = Colors[theme];

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [countryCode, setCountryCode] = useState('1');
  const [email, setEmail] = useState('');
  const [avatarUri, setAvatarUri] = useState<string | null>(null);

  function handleCountryCodeChange(text: string) {
    // Only allow digits
    const cleaned = text.replace(/\D/g, '');
    setCountryCode(cleaned);
  }

  async function openCamera() {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission required', 'Camera permission is required to take a profile photo.');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      setAvatarUri(result.assets[0].uri);
    }
  }

  async function pickImageFromLibrary() {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission required', 'Photo library permission is required to choose a profile photo.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
      allowsMultipleSelection: false,
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      setAvatarUri(result.assets[0].uri);
    }
  }

  function handleChangePhoto() {
    Keyboard.dismiss();
    Alert.alert('Profile Photo', 'Choose an option', [
      { text: 'Take Photo', onPress: () => void openCamera() },
      { text: 'Choose from Library', onPress: () => void pickImageFromLibrary() },
      { text: 'Cancel', style: 'cancel' },
    ]);
  }

  return (
    <KeyboardAvoidingView
      style={styles.flex1}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
    >
      <TouchableWithoutFeedback onPress={Keyboard.dismiss} accessible={false}>
        <SafeAreaView style={[styles.flex1, { backgroundColor: c.background }]} edges={["top", "bottom"]}>
          <ThemedView style={styles.container}>
            <View style={styles.header}>
              <TouchableOpacity style={[styles.avatar, { borderColor: c.icon }]} onPress={handleChangePhoto} accessibilityLabel="Change profile photo">
                {avatarUri ? (
                  <Image source={{ uri: avatarUri }} style={styles.avatarImage} />
                ) : (() => {
                  const initials = [firstName?.[0], lastName?.[0]]
                    .filter(Boolean)
                    .join('')
                    .toUpperCase();
                  return initials ? (
                    <ThemedText style={[styles.avatarInitials]}>{initials}</ThemedText>
                  ) : (
                    <Ionicons name="person" size={56} color={c.icon} />
                  );
                })()}
              </TouchableOpacity>
              <TouchableOpacity onPress={handleChangePhoto}>
                <ThemedText type="link">Change Photo</ThemedText>
              </TouchableOpacity>
            </View>

            <View style={styles.form}>
              <View style={styles.fieldGroup}>
                <ThemedText>First name</ThemedText>
                <TextInput
                  value={firstName}
                  onChangeText={setFirstName}
                  placeholder="First name"
                  placeholderTextColor={theme === 'dark' ? Colors.dark.icon : Colors.light.icon}
                  style={[styles.input, { color: c.text, borderColor: c.icon, backgroundColor: c.background }]}
                  autoCapitalize="words"
                  returnKeyType="next"
                />
              </View>

              <View style={styles.fieldGroup}>
                <ThemedText>Last name</ThemedText>
                <TextInput
                  value={lastName}
                  onChangeText={setLastName}
                  placeholder="Last name"
                  placeholderTextColor={theme === 'dark' ? Colors.dark.icon : Colors.light.icon}
                  style={[styles.input, { color: c.text, borderColor: c.icon, backgroundColor: c.background }]}
                  autoCapitalize="words"
                  returnKeyType="next"
                />
              </View>

              <View style={styles.fieldGroup}>
                <ThemedText>Phone Number</ThemedText>
                <View style={styles.phoneRow}>
                  <View style={[styles.countryCodeInput, { borderColor: c.icon, backgroundColor: c.background }]}>
                    <ThemedText style={styles.plusSign}>+</ThemedText>
                    <TextInput
                      value={countryCode}
                      onChangeText={handleCountryCodeChange}
                      placeholder="1"
                      placeholderTextColor={theme === 'dark' ? Colors.dark.icon : Colors.light.icon}
                      style={[styles.codeInput, { color: c.text }]}
                      keyboardType="number-pad"
                      maxLength={3}
                      returnKeyType="next"
                    />
                  </View>
                  <TextInput
                    value={phoneNumber}
                    onChangeText={setPhoneNumber}
                    placeholder="(123) 456-7890"
                    placeholderTextColor={theme === 'dark' ? Colors.dark.icon : Colors.light.icon}
                    style={[styles.input, styles.phoneInput, { color: c.text, borderColor: c.icon, backgroundColor: c.background }]}
                    keyboardType="phone-pad"
                    returnKeyType="next"
                  />
                </View>
              </View>

              <View style={styles.fieldGroup}>
                <ThemedText>Email</ThemedText>
                <TextInput
                  value={email}
                  onChangeText={setEmail}
                  placeholder="you@example.com"
                  placeholderTextColor={theme === 'dark' ? Colors.dark.icon : Colors.light.icon}
                  style={[styles.input, { color: c.text, borderColor: c.icon, backgroundColor: c.background }]}
                  keyboardType="email-address"
                  returnKeyType="next"
                />
              </View>
            </View>
          </ThemedView>
        </SafeAreaView>
      </TouchableWithoutFeedback>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex1: { flex: 1 },
  container: {
    flex: 1,
    paddingHorizontal: 16,
    paddingTop: 0,
    gap: 24,
    justifyContent: 'center',
  },
  header: {
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
  form: {
    gap: 16,
  },
  fieldGroup: {
    gap: 6,
  },
  input: {
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
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
  },
});
