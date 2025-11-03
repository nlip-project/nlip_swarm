import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { Ionicons } from '@expo/vector-icons';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import { useEffect, useRef, useState } from 'react';
import { Alert, FlatList, Image, Keyboard, KeyboardAvoidingView, Linking, Platform, StyleSheet, TextInput, TouchableOpacity, TouchableWithoutFeedback, View } from 'react-native';

export default function TabThreeScreen() {
    const theme = useColorScheme() ?? 'light';
    const c = Colors[theme];
    const [text, setText] = useState('');
    const [isSending, setIsSending] = useState(false);
    const [imageUri, setImageUri] = useState<string | null>(null);
    const [fileUri, setFileUri] = useState<string | null>(null);
    const [fileName, setFileName] = useState<string | null>(null);
    const [fileSize, setFileSize] = useState<number | null>(null);
    const [fileType, setFileType] = useState<string | null>(null);
    type Message = {
        id: string;
        text?: string;
        imageUri?: string | null;
        fileUri?: string | null;
        fileName?: string | null;
        fileSize?: number | null;
        fileType?: string | null;
        timestamp: number;
        sender: 'me' | 'other'
    };
    const [messages, setMessages] = useState<Message[]>([]);
    const listRef = useRef<FlatList<Message>>(null);

    const API_URL = 'http://localhost:8000/nlip/';

    // Helper function to format file size
    function formatFileSize(bytes: number): string {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
        return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
    }

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
        Alert.alert('Attach', 'Choose an option', [
            { text: 'Take Photo', onPress: () => void openCamera() },
            { text: 'Choose Photo', onPress: () => void pickImageFromLibrary() },
            { text: 'Choose File', onPress: () => void pickDocument() },
            { text: 'Cancel', style: 'cancel' },
        ]);
    }

    async function pickDocument() {
        try {
            const result = await DocumentPicker.getDocumentAsync({
                type: '*/*',
                copyToCacheDirectory: true,
            });

            if (!result.canceled && result.assets && result.assets.length > 0) {
                const file = result.assets[0];
                setFileUri(file.uri);
                setFileName(file.name);
                setFileSize(file.size ?? null);
                setFileType(file.mimeType ?? null);
                console.log('File picked:', file.name, file.uri);
            }
        } catch (err) {
            console.error('Error picking document:', err);
            Alert.alert('Error', 'Failed to pick document');
        }
    }

    async function sendToBackend(inputText: string): Promise<string> {
        console.log('[sendToBackend] Starting request with text:', inputText);
        
        const payload = {
            format: 'text',
            subformat: 'plain',
            content: inputText,
            submessages: [
                {
                    format: 'generic',
                    subformat: 'translation_request',
                    content: {
                        target_language: 'en',
                    },
                },
            ],
        };
        
        console.log('[sendToBackend] Payload:', JSON.stringify(payload, null, 2));
        console.log('[sendToBackend] Sending POST to:', API_URL);

        // Add timeout to prevent hanging forever
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

        try {
            const res = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
                signal: controller.signal,
            });

            clearTimeout(timeoutId);
            console.log('[sendToBackend] Response status:', res.status, res.statusText);

            if (!res.ok) {
                const text = await res.text().catch(() => '');
                console.error('[sendToBackend] Error response body:', text);
                throw new Error(`Backend error ${res.status}: ${text || res.statusText}`);
            }

            const data = await res.json();
            console.log('[sendToBackend] Response data:', JSON.stringify(data, null, 2));
            
            const content = data?.content;
            console.log('[sendToBackend] Extracted content:', content);
            
            if (typeof content === 'string' && content.trim().length > 0) {
                console.log('[sendToBackend] Returning content as string:', content);
                return content;
            }
            if (Array.isArray(data?.submessages)) {
                console.log('[sendToBackend] Checking submessages:', data.submessages.length);
                const firstText = data.submessages.find((s: any) => s?.format?.toLowerCase?.() === 'text' && typeof s?.content === 'string');
                if (firstText?.content) {
                    console.log('[sendToBackend] Found text in submessage:', firstText.content);
                    return firstText.content as string;
                }
            }
            const fallback = typeof content === 'object' ? JSON.stringify(content) : 'Received response';
            console.log('[sendToBackend] Using fallback response:', fallback);
            return fallback;
        } catch (error: any) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                console.error('[sendToBackend] Request timed out after 30 seconds');
                throw new Error('Request timed out. The server may be slow or unresponsive.');
            }
            console.error('[sendToBackend] Fetch error:', error);
            throw error;
        }
    }

    function handleSend() {
        console.log('[handleSend] Called with text:', text);
        const trimmed = text.trim();
        if (!trimmed && !imageUri && !fileUri) {
            console.log('[handleSend] No content to send, returning early');
            return;
        }
        
        console.log('[handleSend] Creating message with trimmed text:', trimmed);
        const newMessage: Message = {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            text: trimmed || undefined,
            imageUri: imageUri || undefined,
            fileUri: fileUri || undefined,
            fileName: fileName || undefined,
            fileSize: fileSize || undefined,
            fileType: fileType || undefined,
            timestamp: Date.now(),
            sender: 'me',
        };
        
        console.log('[handleSend] Adding message to list:', newMessage);
        // Prepend for inverted FlatList so newest appears at the visual bottom
        setMessages((prev) => [newMessage, ...prev]);
        setText('');
        setImageUri(null);
        setFileUri(null);
        setFileName(null);
        setFileSize(null);
        setFileType(null);
        Keyboard.dismiss();
        requestAnimationFrame(() => {
            listRef.current?.scrollToOffset({ offset: 0, animated: true });
        });

        // Only send to backend when there's text content. Attachments are not sent yet.
        if (!trimmed) {
            console.log('[handleSend] No text content, skipping backend call');
            return;
        }
        
        console.log('[handleSend] Sending to backend...');
        setIsSending(true);
        void sendToBackend(trimmed)
            .then((reply) => {
                console.log('[handleSend] Received reply:', reply);
                const replyMessage: Message = {
                    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                    text: reply,
                    timestamp: Date.now(),
                    sender: 'other',
                };
                console.log('[handleSend] Adding reply message:', replyMessage);
                setMessages((prev) => [replyMessage, ...prev]);
                requestAnimationFrame(() => {
                    listRef.current?.scrollToOffset({ offset: 0, animated: true });
                });
            })
            .catch((err) => {
                console.error('[handleSend] Error sending message:', err);
                Alert.alert('Error', `Failed to contact server: ${err.message}`);
            })
            .finally(() => {
                console.log('[handleSend] Request complete, resetting isSending');
                setIsSending(false);
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
                            <View style={[
                                styles.messageRow,
                                item.sender === 'me' ? styles.rowMe : styles.rowOther,
                            ]}>
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
                                    {item.fileUri ? (
                                        <TouchableOpacity
                                            style={styles.fileAttachment}
                                            onPress={() => {
                                                if (item.fileUri) {
                                                    void Linking.openURL(item.fileUri).catch((err) => {
                                                        console.error('Failed to open file:', err);
                                                        Alert.alert('Error', 'Could not open file');
                                                    });
                                                }
                                            }}
                                        >
                                            <Ionicons name="document" size={24} color={item.sender === 'me' ? c.messageMeText : c.messageOtherText} />
                                            <View style={styles.fileInfo}>
                                                <ThemedText style={[
                                                    styles.fileName,
                                                    { color: item.sender === 'me' ? c.messageMeText : c.messageOtherText },
                                                ]}>
                                                    {item.fileName || 'Unknown file'}
                                                </ThemedText>
                                                {item.fileSize !== null && item.fileSize !== undefined ? (
                                                    <ThemedText style={[
                                                        styles.fileSize,
                                                        { color: item.sender === 'me' ? c.messageMeText : c.messageOtherText },
                                                    ]}>
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
                        )}
                    />
                    {imageUri ? (
                        <Image source={{ uri: imageUri }} style={styles.preview} />
                    ) : null}
                    {fileUri && fileName ? (
                        <View style={[styles.filePreview, { backgroundColor: c.messageMeBg, borderColor: c.icon }]}>
                            <Ionicons name="document" size={32} color={c.messageMeText} />
                            <View style={styles.fileInfo}>
                                <ThemedText style={[styles.fileName, { color: c.messageMeText }]}>
                                    {fileName}
                                </ThemedText>
                                {fileSize !== null && fileSize !== undefined ? (
                                    <ThemedText style={[styles.fileSize, { color: c.messageMeText }]}>
                                        {formatFileSize(fileSize)}
                                    </ThemedText>
                                ) : null}
                            </View>
                            <TouchableOpacity
                                onPress={() => {
                                    setFileUri(null);
                                    setFileName(null);
                                    setFileSize(null);
                                    setFileType(null);
                                }}
                                accessibilityLabel="Remove file"
                            >
                                <Ionicons name="close-circle" size={24} color={c.messageMeText} />
                            </TouchableOpacity>
                        </View>
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
                        <TouchableOpacity style={[styles.sendButton, { backgroundColor: c.tint }]} onPress={handleSend} accessibilityLabel="Send message" disabled={isSending}>
                            <ThemedText style={[{ color: c.buttonText }]}>{isSending ? '...' : 'Send'}</ThemedText>
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
    },
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
});