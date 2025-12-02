import { ThemedText } from "@/components/themed-text";
import { ThemedView } from "@/components/themed-view";
import { Drawout } from "@/components/ui/drawout";
import { Colors } from "@/constants/theme";
import { useColorScheme } from "@/hooks/use-color-scheme";
import { Ionicons } from "@expo/vector-icons";
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as DocumentPicker from "expo-document-picker";
import * as ImagePicker from "expo-image-picker";
import { useRouter } from 'expo-router';
import { useEffect, useRef, useState } from "react";
import {
  Alert,
  FlatList,
  Image,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import MessageRow from "../../components/MessageRow";
import { formatFileSize } from "../../components/utils";
import NLIPClient from "../nlipClient";

type ConversationSummary = { id: string; title?: string | null };

export default function TabThreeScreen() {
  const router = useRouter();
  const theme = useColorScheme() ?? "light";
  const [currentConversation, setCurrentConversation] = useState<ConversationSummary | null>(null);
  const currentConversationId = currentConversation?.id ?? null;
  // Redirect to login if user missing; otherwise load last selected conversation
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const u = await AsyncStorage.getItem('user');
        if (mounted && !u) {
          try { router.replace('/login' as any); } catch { /* ignore */ }
          return;
        }
        if (mounted) {
          const stored = await AsyncStorage.getItem('current_conversation');
          if (stored) {
            try {
              const parsed = JSON.parse(stored);
              if (parsed && parsed.id) {
                setCurrentConversation({ id: parsed.id, title: parsed.title ?? null });
              } else {
                setCurrentConversation({ id: stored, title: null });
              }
            } catch {
              setCurrentConversation({ id: stored, title: null });
            }
          }
        }
      } catch (e) {
        console.warn('Failed to read user storage', e);
      }
    })();
    return () => { mounted = false; };
  }, [router]);
  const c = Colors[theme];
  const insets = useSafeAreaInsets();
  const isWeb = Platform.OS === "web";
  const [text, setText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [fileUri, setFileUri] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileSize, setFileSize] = useState<number | null>(null);
  const [fileType, setFileType] = useState<string | null>(null);
  const [, setOldConversations] = useState<Message[][]>([]);
  type Message = {
    id: string;
    text?: string;
    imageUri?: string | null;
    fileUri?: string | null;
    fileName?: string | null;
    fileSize?: number | null;
    fileType?: string | null;
    timestamp: number;
    sender: "me" | "other";
  };
  const [messages, setMessages] = useState<Message[]>([]);
  const listRef = useRef<FlatList<Message>>(null);
  const topSpacerHeight = (insets.top || 0) + 12;

  const API_BASE = process.env.EXPO_PUBLIC_API_BASE;
  if (!API_BASE || API_BASE.trim().length === 0) {
    throw new Error('EXPO_PUBLIC_API_BASE is not set. Please set it to the backend server URL which is proably looks like "http://localhost:8024"');
  }
  const client = new NLIPClient(API_BASE, { timeout: 30000 });

  const persistConversationSelection = async (conversation: ConversationSummary | null) => {
    try {
      if (!conversation) {
        await AsyncStorage.removeItem('current_conversation');
        return;
      }
      await AsyncStorage.setItem('current_conversation', JSON.stringify(conversation));
    } catch (e) {
      console.warn('Failed to persist conversation selection', e);
    }
  };

  // Clear chat function
  function clearChat() {
    if (messages.length > 0) {
      setOldConversations((prev) => [...prev, messages]);
      setMessages([]);
    }
  }

  // Auto-scroll to bottom when keyboard opens so the input stays visible
  useEffect(() => {
    const eventName =
      Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const sub = Keyboard.addListener(eventName, () => {
      requestAnimationFrame(() =>
        listRef.current?.scrollToOffset({ offset: 0, animated: true })
      );
    });
    return () => sub.remove();
  }, []);

  // Auto-scroll when an image is attached (from camera or library)
  useEffect(() => {
    if (imageUri) {
      requestAnimationFrame(() =>
        listRef.current?.scrollToOffset({ offset: 0, animated: true })
      );
    }
  }, [imageUri]);

  async function openCamera() {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== "granted") {
      Alert.alert(
        "Permission required",
        "Camera permission is required to take a photo."
      );
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
      console.log("Image picked:", uri);
    }
  }

  async function pickImageFromLibrary() {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== "granted") {
      Alert.alert(
        "Permission required",
        "Photo library permission is required to choose a photo."
      );
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
      console.log("Image chosen:", uri);
    }
  }

  function handleAttachPress() {
    Keyboard.dismiss();
    Alert.alert("Attach", "Choose an option", [
      { text: "Take Photo", onPress: () => void openCamera() },
      { text: "Choose Photo", onPress: () => void pickImageFromLibrary() },
      { text: "Choose File", onPress: () => void pickDocument() },
      { text: "Cancel", style: "cancel" },
    ]);
  }

  async function pickDocument() {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: "*/*",
        copyToCacheDirectory: true,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const file = result.assets[0];
        setFileUri(file.uri);
        setFileName(file.name);
        setFileSize(file.size ?? null);
        setFileType(file.mimeType ?? null);
        console.log("File picked:", file.name, file.uri);
      }
    } catch (err) {
      console.error("Error picking document:", err);
      Alert.alert("Error", "Failed to pick document");
    }
  }

  const metadataForRequest = () => {
    if (!currentConversationId) return undefined;
    return { conversation_id: currentConversationId };
  };

  const conversationTokenSubmessage = () => {
    if (!currentConversationId) return undefined;
    return {
      format: 'token',
      subformat: 'conversation',
      content: currentConversationId,
    };
  };

  async function sendToBackend(
    inputText: string,
    options?: {
      imageUri?: string | null;
      fileUri?: string | null;
      fileName?: string | null;
      fileType?: string | null;
    }
  ): Promise<any> {
    console.log(
      "[sendToBackend] Delegating to NLIPClient with text:",
      inputText,
      "options:",
      options
    );
    try {
      const metadata = metadataForRequest();
      const conversationToken = conversationTokenSubmessage();
      const baseSubmessages = conversationToken ? [conversationToken] : [];
      if (options?.imageUri) {
        const reply = await client.sendMessage({
          format: "text",
          subformat: "english",
          content: inputText,
          submessages: [
            ...baseSubmessages,
            {
              format: "binary",
              subformat: "image/base64",
              content: await client.uriToBase64(options.imageUri),
              label: options.fileName ?? "image.jpg",
            },
          ],
          metadata,
        });
        console.log("[sendToBackend] NLIPClient replied (image):", reply);
        return reply;
      }
      // if (options?.fileUri) {
      //     const reply = await client.sendWithFile(inputText, options.fileUri, options.fileName ?? undefined, options.fileType ?? undefined);
      //     console.log('[sendToBackend] NLIPClient replied (file):', reply);
      //     return reply;
      // }
      else {
        const reply = await client.sendMessage({
          format: "text",
          subformat: "english",
          content: inputText,
          submessages: baseSubmessages,
          metadata,
        });
        console.log("[sendToBackend] NLIPClient replied:", reply);
        return reply;
      }
    } catch (err: any) {
      console.error("[sendToBackend] NLIPClient error:", err);
      throw err;
    }
  }

  function formatReplyText(reply: unknown): string {
    if (reply == null) return "";
    if (typeof reply === "string") return reply;
    if (typeof reply === "object") {
      const r = reply as any;
      if (r && typeof r.content === "string") {
        let combined = r.content;
        if (Array.isArray(r.submessages) && r.submessages.length > 0) {
          const subTexts = r.submessages
            .map((sm: any) => {
              if (!sm) return "";
              if (typeof sm.content === "string") return sm.content;
              if (sm.content != null) {
                try {
                  return JSON.stringify(sm.content);
                } catch {
                  return String(sm.content);
                }
              }
              return "";
            })
            .filter((t: string) => t.length > 0);
          if (subTexts.length > 0) {
            combined = [combined, ...subTexts].join("\n\n");
          }
        }
        return combined;
      }
      try {
        return JSON.stringify(reply);
      } catch {
        return String(reply);
      }
    }
    return String(reply);
  }

  function handleSend() {
    console.log("[handleSend] Called with text:", text);
    const trimmed = text.trim();
    if (!trimmed && !imageUri && !fileUri) {
      console.log("[handleSend] No content to send, returning early");
      return;
    }
    console.log("[handleSend] Creating message with trimmed text:", trimmed);
    const newMessage: Message = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      text: trimmed || undefined,
      imageUri: imageUri || undefined,
      fileUri: fileUri || undefined,
      fileName: fileName || undefined,
      fileSize: fileSize || undefined,
      fileType: fileType || undefined,
      timestamp: Date.now(),
      sender: "me",
    };

    console.log("[handleSend] Adding message to list:", newMessage);
    // Prepend for inverted FlatList so newest appears at the visual bottom
    setMessages((prev) => [newMessage, ...prev]);
    // capture attachments locally before clearing UI state
    const localImage = imageUri;
    const localFile = fileUri;
    const localFileName = fileName;
    const localFileType = fileType;

    setText("");
    setImageUri(null);
    setFileUri(null);
    setFileName(null);
    setFileSize(null);
    setFileType(null);
    Keyboard.dismiss();
    requestAnimationFrame(() => {
      listRef.current?.scrollToOffset({ offset: 0, animated: true });
    });

    // Send to backend with optional attachments
    console.log("[handleSend] Sending to backend...", {
      trimmed,
      localImage,
      localFile,
      localFileName,
      localFileType,
    });
    setIsSending(true);
    void sendToBackend(trimmed, {
      imageUri: localImage,
      fileUri: localFile,
      fileName: localFileName,
      fileType: localFileType,
    })
      .then((reply) => {
        console.log("[handleSend] Received reply:", reply);
        // Persist conversation ID if backend created one
        try {
          if (reply && typeof reply === "object") {
            const maybeId =
              (reply as any).conversation_id ||
              (reply as any).conversationId ||
              (reply as any).conversation;
            if (maybeId) {
              const cid = String(maybeId);
              const fallbackTitle =
                currentConversation?.title ?? (trimmed ? trimmed.slice(0, 80) : null);
              const nextConversation: ConversationSummary = { id: cid, title: fallbackTitle };
              setCurrentConversation(nextConversation);
              void persistConversationSelection(nextConversation);
            }
          }
        } catch (e) {
          console.warn("[handleSend] Error while persisting conversation id", e);
        }

        const replyText = formatReplyText(reply);
        const replyMessage: Message = {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          text: replyText,
          timestamp: Date.now(),
          sender: "other",
        };
        console.log("[handleSend] Adding reply message:", replyMessage);
        setMessages((prev) => [replyMessage, ...prev]);
        requestAnimationFrame(() => {
          listRef.current?.scrollToOffset({ offset: 0, animated: true });
        });
      })
      .catch((err) => {
        console.error("[handleSend] Error sending message:", err);
        Alert.alert("Error", `Failed to contact server: ${err.message}`);
      })
      .finally(() => {
        console.log("[handleSend] Request complete, resetting isSending");
        setIsSending(false);
      });
  }

  return (
    <KeyboardAvoidingView
      style={styles.flex1}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}
    >
      {/* Use a non-intercepting container so scrolling gestures reach the FlatList on web */}
      <View style={styles.flex1} pointerEvents='box-none'>
        <ThemedView style={styles.container}>
          {/* Top spacer to avoid notch/camera area on newer iPhones (e.g. iPhone 16 Pro) */}
          <View
            pointerEvents='none'
            style={[styles.topSpacer, { height: topSpacerHeight }]}
          />
          <Drawout
            clearChat={clearChat}
            apiBase={API_BASE}
            renderTrigger={({ toggle }) => (
              <View
                style={[
                  styles.conversationHeaderRow,
                  { borderColor: currentConversation ? c.icon : 'transparent' },
                  !currentConversation ? styles.conversationHeaderRowEmpty : null,
                ]}
                accessibilityLabel={currentConversation ? 'Current conversation summary' : 'Conversation drawer'}
              >
                <TouchableOpacity
                  onPress={toggle}
                  accessibilityLabel="Open conversation drawer"
                  style={styles.headerHamburger}
                  activeOpacity={0.8}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                  <View style={[styles.headerHamburgerLine, { backgroundColor: c.icon }]} />
                  <View style={[styles.headerHamburgerLine, { backgroundColor: c.icon }]} />
                  <View style={[styles.headerHamburgerLine, { backgroundColor: c.icon }]} />
                </TouchableOpacity>
                <View style={styles.conversationHeaderText}>
                  {currentConversation ? (
                    <>
                      <ThemedText style={[styles.conversationTitle, { color: c.text }]}>
                        {currentConversation.title?.trim() || 'Untitled conversation'}
                      </ThemedText>
                      <ThemedText style={[styles.conversationSubtitle, { color: c.icon }]}>
                        {`ID: ${currentConversation.id}`}
                      </ThemedText>
                    </>
                  ) : (
                    <></>
                  )}
                </View>
              </View>
            )}
            onSelectConversation={async (conversation) => {
              if (!conversation) {
                clearChat();
                setCurrentConversation(null);
                setText("");
                setImageUri(null);
                setFileUri(null);
                setFileName(null);
                setFileSize(null);
                setFileType(null);
                await persistConversationSelection(null);
                return;
              }
              try {
                const convId = conversation.id;
                const res = await fetch(`${API_BASE}/conversations/${convId}/messages?limit=200`, { credentials: 'include' });
                if (!res.ok) {
                  Alert.alert('Error', 'Failed to load conversation');
                  return;
                }
                const data = await res.json();
                const msgs = (data.messages || []).map((m: any) => ({
                  id: m.id,
                  text: m.content ?? '',
                  timestamp: m.created_at ? Date.parse(m.created_at) : Date.now(),
                  sender: m.role === 'user' ? 'me' : 'other',
                } as Message));
                setMessages(msgs.reverse());
                const selectedConversation: ConversationSummary = {
                  id: convId,
                  title: conversation.title ?? null,
                };
                setCurrentConversation(selectedConversation);
                await persistConversationSelection(selectedConversation);
              } catch (e) {
                console.warn('Failed to load conversation', e);
                Alert.alert('Error', 'Failed to load conversation');
              }
            }}
          />
          <FlatList
            ref={listRef}
            style={styles.list}
            data={messages}
            keyExtractor={(item) => item.id}
            inverted={!isWeb}
            nestedScrollEnabled
            keyboardShouldPersistTaps='handled'
            {...(!isWeb
              ? { maintainVisibleContentPosition: { minIndexForVisible: 0 } }
              : {})}
            contentContainerStyle={[
              { flexGrow: 1 },
              messages.length === 0 ? styles.emptyListContainer : undefined,
            ]}
            renderItem={({ item }) => <MessageRow item={item} c={c} />}
          />
          {imageUri ? (
            <Image source={{ uri: imageUri }} style={styles.preview} />
          ) : null}
          {fileUri && fileName ? (
            <View
              style={[
                styles.filePreview,
                { backgroundColor: c.messageMeBg, borderColor: c.icon },
              ]}
            >
              <Ionicons name='document' size={32} color={c.messageMeText} />
              <View style={styles.fileInfo}>
                <ThemedText
                  style={[styles.fileName, { color: c.messageMeText }]}
                >
                  {fileName}
                </ThemedText>
                {fileSize !== null && fileSize !== undefined ? (
                  <ThemedText
                    style={[styles.fileSize, { color: c.messageMeText }]}
                  >
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
                accessibilityLabel='Remove file'
              >
                <Ionicons
                  name='close-circle'
                  size={24}
                  color={c.messageMeText}
                />
              </TouchableOpacity>
            </View>
          ) : null}

          <View
            style={[
              styles.inputRow,
              { backgroundColor: c.background, borderColor: c.icon },
            ]}
          >
            <TouchableOpacity
              style={[styles.plusButton, { borderColor: c.icon }]}
              onPress={handleAttachPress}
              accessibilityLabel='Attach image'
            >
              <ThemedText style={styles.plusText}>+</ThemedText>
            </TouchableOpacity>

            <TextInput
              value={text}
              onChangeText={setText}
              placeholder='Message'
              style={[styles.textInput, { color: c.text }]}
              placeholderTextColor={
                theme === "dark" ? Colors.dark.icon : Colors.light.icon
              }
              returnKeyType='send'
              onSubmitEditing={handleSend}
              blurOnSubmit={false}
            />
            <TouchableOpacity
              style={[styles.sendButton, { backgroundColor: c.tint }]}
              onPress={handleSend}
              accessibilityLabel='Send message'
            >
              <ThemedText style={[{ color: c.buttonText }]}>
                {isSending ? "..." : "Send"}
              </ThemedText>
            </TouchableOpacity>
          </View>
        </ThemedView>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex1: {
    flex: 1,
  },
  container: {
    flex: 1,
    justifyContent: "center",
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
    alignItems: "center",
    justifyContent: "center",
  },
  emptyText: {},
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "center",
    width: "94%",
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
    fontWeight: "600",
  },
  plusButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    alignItems: "center",
    justifyContent: "center",
    marginRight: 8,
  },
  plusText: {
    fontSize: 22,
    lineHeight: 22,
  },
  conversationHeaderRow: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderBottomWidth: 1,
    gap: 12,
  },
  conversationHeaderRowEmpty: {
    borderBottomWidth: 0,
    paddingBottom: 4,
  },
  conversationHeaderText: {
    flex: 1,
  },
  conversationTitle: {
    fontSize: 18,
    fontWeight: '600',
  },
  conversationSubtitle: {
    fontSize: 12,
    marginTop: 4,
  },
  headerHamburger: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'transparent',
  },
  headerHamburgerLine: {
    width: 24,
    height: 3,
    borderRadius: 2,
    marginVertical: 2,
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
    maxWidth: "80%",
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginVertical: 4,
  },
  topSpacer: {
    backgroundColor: "#ffffff",
    width: "100%",
  },
  messageRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 8,
  },
  rowMe: {
    alignSelf: "flex-end",
  },
  rowOther: {
    alignSelf: "flex-start",
  },
  avatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
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
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingVertical: 8,
  },
  fileInfo: {
    flex: 1,
  },
  fileName: {
    fontSize: 14,
    fontWeight: "600",
  },
  fileSize: {
    fontSize: 12,
    marginTop: 2,
  },
  filePreview: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    marginHorizontal: 12,
    marginBottom: 8,
  },
});
