import { ConversationHeader } from "@/components/chat/ConversationHeader";
import { ConversationList } from "@/components/chat/ConversationList";
import { MessageComposer } from "@/components/chat/MessageComposer";
import { SelectedAttachment } from "@/components/chat/SelectedAttachment";
import { ThemedView } from "@/components/themed-view";
import { Drawout } from "@/components/ui/drawout";
import { API_BASE } from "@/constants/env";
import { Colors } from "@/constants/theme";
import { useColorScheme } from "@/hooks/use-color-scheme";
import { useImageAttachment } from "@/hooks/use-image-attachment";
import { usePersistedConversation } from "@/hooks/use-persisted-conversation";
import type { ConversationSummary, Message } from "@/types/chat";
import * as DocumentPicker from "expo-document-picker";
import { useRouter } from "expo-router";
import { useEffect, useRef, useState } from "react";
import {
  Alert,
  FlatList,
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import NLIPClient from "../nlipClient";

export default function TabThreeScreen() {
  const router = useRouter();
  const theme = useColorScheme() ?? "light";
  const colors = Colors[theme];
  const insets = useSafeAreaInsets();
  const isWeb = Platform.OS === "web";
  const { currentConversation, persistConversationSelection } = usePersistedConversation(router);
  const currentConversationId = currentConversation?.id ?? null;

  const [text, setText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [fileUri, setFileUri] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileSize, setFileSize] = useState<number | null>(null);
  const [fileType, setFileType] = useState<string | null>(null);
  const selectedFile = fileUri && fileName ? { uri: fileUri, name: fileName, size: fileSize, type: fileType } : undefined;
  const clearFileSelection = () => {
    setFileUri(null);
    setFileName(null);
    setFileSize(null);
    setFileType(null);
  };
  const [, setOldConversations] = useState<Message[][]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const listRef = useRef<FlatList<Message>>(null);
  const topSpacerHeight = (insets.top || 0) + 12;

  const client = new NLIPClient(API_BASE, { timeout: 30000 });

  const { openCamera, pickImageFromLibrary } = useImageAttachment({
    onImageSelected: (uri) => {
      setImageUri(uri);
      requestAnimationFrame(() =>
        listRef.current?.scrollToOffset({ offset: 0, animated: true })
      );
    },
    onError: (message) => console.warn("[useImageAttachment]", message),
    cameraOptions: { quality: 0.6 },
  });

  const pickDocument = async () => {
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
        requestAnimationFrame(() =>
          listRef.current?.scrollToOffset({ offset: 0, animated: true })
        );
      }
    } catch (err) {
      console.error("Error picking document:", err);
      Alert.alert("Error", "Failed to pick document");
    }
  };

  const metadataForRequest = () => {
    if (!currentConversationId) return undefined;
    return { conversation_id: currentConversationId };
  };

  const conversationTokenSubmessage = () => {
    if (!currentConversationId) return undefined;
    return {
      format: "token",
      subformat: "conversation",
      content: currentConversationId,
    } as const;
  };

  async function sendToBackend(
    inputText: string,
    options?: {
      imageUri?: string | null;
      fileUri?: string | null;
      fileName?: string | null;
      fileType?: string | null;
    }
  ) {
    try {
      const metadata = metadataForRequest();
      const conversationToken = conversationTokenSubmessage();
      const baseSubmessages = conversationToken ? [conversationToken] : [];
      if (options?.imageUri) {
        return client.sendMessage({
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
      }

      return client.sendMessage({
        format: "text",
        subformat: "english",
        content: inputText,
        submessages: baseSubmessages,
        metadata,
      });
    } catch (err) {
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

  function clearChat() {
    if (messages.length > 0) {
      setOldConversations((prev) => [...prev, messages]);
      setMessages([]);
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

  function handleSend() {
    const trimmed = text.trim();
    if (!trimmed && !imageUri && !fileUri) {
      return;
    }

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

    setMessages((prev) => [newMessage, ...prev]);
    const localImage = imageUri;
    const localFile = fileUri;
    const localFileName = fileName;
    const localFileType = fileType;

    setText("");
    setImageUri(null);
    clearFileSelection();
    Keyboard.dismiss();
    requestAnimationFrame(() =>
      listRef.current?.scrollToOffset({ offset: 0, animated: true })
    );

    setIsSending(true);
    void sendToBackend(trimmed, {
      imageUri: localImage,
      fileUri: localFile,
      fileName: localFileName,
      fileType: localFileType,
    })
      .then((reply) => {
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
        setMessages((prev) => [replyMessage, ...prev]);
        requestAnimationFrame(() =>
          listRef.current?.scrollToOffset({ offset: 0, animated: true })
        );
      })
      .catch((err) => {
        console.error("[handleSend] Error sending message:", err);
        Alert.alert("Error", `Failed to contact server: ${err.message}`);
      })
      .finally(() => {
        setIsSending(false);
      });
  }

  useEffect(() => {
    const eventName = Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const sub = Keyboard.addListener(eventName, () => {
      requestAnimationFrame(() =>
        listRef.current?.scrollToOffset({ offset: 0, animated: true })
      );
    });
    return () => sub.remove();
  }, []);

  useEffect(() => {
    if (imageUri) {
      requestAnimationFrame(() =>
        listRef.current?.scrollToOffset({ offset: 0, animated: true })
      );
    }
  }, [imageUri]);

  return (
    <KeyboardAvoidingView
      style={styles.flex1}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}
    >
      <View style={styles.flex1} pointerEvents="box-none">
        <ThemedView style={styles.container}>
          <View pointerEvents="none" style={[styles.topSpacer, { height: topSpacerHeight }]} />
          <Drawout
            clearChat={clearChat}
            apiBase={API_BASE}
            renderTrigger={({ toggle }) => (
              <ConversationHeader conversation={currentConversation} colors={colors} onToggle={toggle} />
            )}
            onSelectConversation={async (conversation) => {
              if (!conversation) {
                clearChat();
                setText("");
                setImageUri(null);
                clearFileSelection();
                await persistConversationSelection(null);
                return;
              }

              try {
                const convId = conversation.id;
                const res = await fetch(`${API_BASE}/conversations/${convId}/messages?limit=200`, {
                  credentials: "include",
                });
                if (!res.ok) {
                  Alert.alert("Error", "Failed to load conversation");
                  return;
                }
                const data = await res.json();
                const msgs = (data.messages || []).map((m: any) => ({
                  id: m.id,
                  text: m.content ?? "",
                  timestamp: m.created_at ? Date.parse(m.created_at) : Date.now(),
                  sender: m.role === "user" ? "me" : "other",
                })) as Message[];
                setMessages(msgs.reverse());
                const selectedConversation: ConversationSummary = {
                  id: convId,
                  title: conversation.title ?? null,
                };
                await persistConversationSelection(selectedConversation);
              } catch (e) {
                console.warn("Failed to load conversation", e);
                Alert.alert("Error", "Failed to load conversation");
              }
            }}
          />

          <ConversationList messages={messages} listRef={listRef} colors={colors} isWeb={isWeb} />

          <SelectedAttachment
            imageUri={imageUri}
            file={selectedFile}
            colors={colors}
            onRemoveFile={clearFileSelection}
          />

          <MessageComposer
            text={text}
            onChangeText={setText}
            onSend={handleSend}
            onAttachPress={handleAttachPress}
            isSending={isSending}
            colors={colors}
            theme={theme}
          />
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
  topSpacer: {
    backgroundColor: "#ffffff",
    width: "100%",
  },
});
