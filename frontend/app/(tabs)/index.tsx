import * as ImagePicker from 'expo-image-picker';
import { useEffect, useRef, useState } from 'react';
import { Alert, FlatList, Image, Keyboard, KeyboardAvoidingView, Platform, StyleSheet, TextInput, TouchableOpacity, TouchableWithoutFeedback, View } from 'react-native';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { ThemedView } from '@/components/themed-view';
import { ThemedText } from '@/components/themed-text';

export default function TabThreeScreen() {
    const theme = useColorScheme() ?? 'light';
    const c = Colors[theme];
    const [text, setText] = useState('');
    const [imageUri, setImageUri] = useState<string | null>(null);
    type Message = { id: string; text?: string; imageUri?: string | null; timestamp: number; sender: 'me' };
    const [messages, setMessages] = useState<Message[]>([]);
    const listRef = useRef<FlatList<Message>>(null);

    // Auto-scroll to bottom when keyboard opens so the input stays visible
    useEffect(() => {
        const eventName = Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow';
        const sub = Keyboard.addListener(eventName, () => {
            requestAnimationFrame(() => listRef.current?.scrollToOffset({ offset: 0, animated: true }));
        });
        return () => sub.remove();
    }, []);

    // Auto-scroll when an image is attached (from camera or library)
    useEffect(() => {
        if (imageUri) {
            requestAnimationFrame(() => listRef.current?.scrollToOffset({ offset: 0, animated: true }));
        }
    }, [imageUri]);

    async function openCamera() {
        const { status } = await ImagePicker.requestCameraPermissionsAsync();
        if (status !== 'granted') {
            Alert.alert('Permission required', 'Camera permission is required to take a photo.');
            return;
        }

        const result = await ImagePicker.launchCameraAsync({
            allowsEditing: false,
            quality: 0.6,
        });

        if (!result.canceled && result.assets && result.assets.length > 0) {
            const uri = result.assets[0].uri;
            setImageUri(uri);
            // TODO: upload the image or attach it to the chat message
            console.log('Image picked:', uri);
        }
    }

    async function pickImageFromLibrary() {
        const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (status !== 'granted') {
            Alert.alert('Permission required', 'Photo library permission is required to choose a photo.');
            return;
        }

        const result = await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ImagePicker.MediaTypeOptions.Images,
            allowsEditing: false,
            quality: 0.8,
            allowsMultipleSelection: false,
        });

        if (!result.canceled && result.assets && result.assets.length > 0) {
            const uri = result.assets[0].uri;
            setImageUri(uri);
            // TODO: upload the image or attach it to the chat message
            console.log('Image chosen:', uri);
        }
    }

    function handleAttachPress() {
        Keyboard.dismiss();
        Alert.alert('Attach image', 'Choose an option', [
            { text: 'Take Photo', onPress: () => void openCamera() },
            { text: 'Choose from Library', onPress: () => void pickImageFromLibrary() },
            { text: 'Cancel', style: 'cancel' },
        ]);
    }

    function handleSend() {
        const trimmed = text.trim();
        if (!trimmed && !imageUri) {
            return;
        }
        const newMessage: Message = {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            text: trimmed || undefined,
            imageUri: imageUri || undefined,
            timestamp: Date.now(),
            sender: 'me',
        };
        // Append new message (list is inverted so this shows at the bottom)
        setMessages((prev) => [...prev, newMessage]);
        setText('');
        setImageUri(null);
        Keyboard.dismiss();
        requestAnimationFrame(() => {
            listRef.current?.scrollToOffset({ offset: 0, animated: true });
        });
    }

    return (
        <KeyboardAvoidingView
            style={styles.flex1}
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}>
            <TouchableWithoutFeedback onPress={Keyboard.dismiss} accessible={false}>
                <ThemedView style={styles.container}>
                    <FlatList
                        ref={listRef}
                        style={styles.list}
                        data={messages}
                        keyExtractor={(item) => item.id}
                        inverted
                        maintainVisibleContentPosition={{ minIndexForVisible: 0 }}
                        contentContainerStyle={messages.length === 0 ? styles.emptyListContainer : undefined}
                        renderItem={({ item }) => (
                            <View
                                style={[
                                    styles.bubble,
                                    item.sender === 'me' ? styles.bubbleMe : styles.bubbleOther,
                                    {
                                        backgroundColor: item.sender === 'me' ? c.messageMeBg : c.messageOtherBg,
                                        borderColor: c.icon,
                                        borderWidth: 1,
                                    },
                                ]}
                            >
                                {item.text ? (
                                    <ThemedText style={[
                                        styles.bubbleText,
                                        { color: item.sender === 'me' ? c.messageMeText : c.messageOtherText },
                                    ]}>
                                        {item.text}
                                    </ThemedText>
                                ) : null}
                                {item.imageUri ? (
                                    <Image source={{ uri: item.imageUri }} style={styles.bubbleImage} />
                                ) : null}
                            </View>
                        )}
                    />
                    {imageUri ? (
                        <Image source={{ uri: imageUri }} style={styles.preview} />
                    ) : null}

                    <View style={[styles.inputRow, { backgroundColor: c.background, borderColor: c.icon }]}>
                        <TouchableOpacity style={[styles.plusButton, { borderColor: c.icon }]} onPress={handleAttachPress} accessibilityLabel="Attach image">
                            <ThemedText style={styles.plusText}>+</ThemedText>
                        </TouchableOpacity>

                        <TextInput
                            value={text}
                            onChangeText={setText}
                            placeholder="Message"
                            style={[styles.textInput, { color: c.text }]}
                            placeholderTextColor={theme === 'dark' ? Colors.dark.icon : Colors.light.icon}
                            returnKeyType="send"
                            onSubmitEditing={handleSend}
                            blurOnSubmit={false}
                        />
                        <TouchableOpacity style={[styles.sendButton, { backgroundColor: c.tint }]} onPress={handleSend} accessibilityLabel="Send message">
                            <ThemedText style={[{ color: c.buttonText }]}>Send</ThemedText>
                        </TouchableOpacity>
                    </View>
                </ThemedView>
            </TouchableWithoutFeedback>
        </KeyboardAvoidingView>
    );
}

const styles = StyleSheet.create({
    flex1: {
        flex: 1,
    },
    container: {
        flex: 1,
        justifyContent: 'center',
        paddingBottom: 8,
        paddingTop: 8,
        gap: 8,
    },
    list: {
        flex: 1,
        paddingHorizontal: 12,
    },
    emptyListContainer: {
        flexGrow: 1,
        alignItems: 'center',
        justifyContent: 'center',
    },
    emptyText: {},
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
    sendButton: {
        paddingHorizontal: 10,
        paddingVertical: 6,
        marginLeft: 6,
        borderRadius: 16,
    },
    sendText: {
        fontWeight: '600',
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
    preview: {
        width: 120,
        height: 90,
        borderRadius: 8,
        marginBottom: 8,
    },
    bubble: {
        maxWidth: '80%',
        borderRadius: 16,
        paddingHorizontal: 12,
        paddingVertical: 8,
        marginVertical: 4,
        alignSelf: 'flex-start',
    },
    bubbleMe: {
        alignSelf: 'flex-end',
    },
    bubbleOther: {
        alignSelf: 'flex-start',
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
});