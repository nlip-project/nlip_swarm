import React, { useEffect, useMemo, useState } from "react";
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
  Pressable,
  Button,
  Alert,
  ScrollView,
} from "react-native";
import { Colors } from "@/constants/theme";
import { ThemedText } from "@/components/themed-text";

type ConversationSummary = { id: string; title?: string | null; last_activity_at?: string | null };

type DrawoutProps = {
  triggerPosition?: { top: number; left: number };
  clearChat?: () => void;
  onSelectConversation?: (conversation: { id: string; title?: string | null } | null) => void;
  apiBase?: string;
};

export function Drawout({ triggerPosition, clearChat, onSelectConversation, apiBase }: DrawoutProps) {
  const [open, setOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const screenWidth = Dimensions.get("window").width;
  const panelWidth = Math.min(260, screenWidth * 0.8);
  const slideAnim = useState(new Animated.Value(-panelWidth))[0];

  const resolvedApiBase = useMemo(() => {
    const origin = apiBase ?? process?.env?.EXPO_PUBLIC_API_BASE ?? (global as any)?.API_BASE ?? "http://0.0.0.0:8024";
    return origin.replace(/\/$/, "");
  }, [apiBase]);

  useEffect(() => {
    Animated.timing(slideAnim, {
      toValue: open ? 0 : -panelWidth,
      duration: 260,
      useNativeDriver: true,
    }).start();
    if (!open) return;

    let canceled = false;
    (async () => {
      setLoading(true);
      try {
        const resp = await fetch(`${resolvedApiBase}/conversations`, { credentials: "include" });
        if (!resp.ok) {
          if (!canceled) setConversations([]);
          return;
        }
        const data = await resp.json();
        if (!canceled) setConversations(data.conversations || []);
      } catch (e) {
        console.warn("Failed to fetch conversations", e);
        if (!canceled) setConversations([]);
      } finally {
        if (!canceled) setLoading(false);
      }
    })();

    return () => {
      canceled = true;
    };
  }, [open, panelWidth, resolvedApiBase, slideAnim]);

  function startNewConversation() {
    setOpen(false);
    clearChat?.();
    onSelectConversation?.(null);
  }

  async function archiveConversation(id: string) {
    try {
      const res = await fetch(`${resolvedApiBase}/conversations/${id}/archive`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        Alert.alert("Archive failed", `Status ${res.status}: ${txt}`);
        return;
      }
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch (e) {
      console.warn("Failed to archive conversation", e);
      Alert.alert("Error", "Failed to archive conversation");
    }
  }

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      {open && (
        <Pressable style={styles.overlay} onPress={() => setOpen(false)} accessibilityLabel="Close drawout panel" />
      )}
      <TouchableOpacity
        style={[
          styles.hamburger,
          triggerPosition ? { top: triggerPosition.top, left: triggerPosition.left } : null,
        ]}
        onPress={() => setOpen((v) => !v)}
        activeOpacity={0.7}
        accessibilityLabel="Open drawout panel"
      >
        <View style={styles.line} />
        <View style={styles.line} />
        <View style={styles.line} />
      </TouchableOpacity>
      <Animated.View
        style={[
          styles.panel,
          {
            width: panelWidth,
            transform: [{ translateX: slideAnim }],
            shadowOpacity: open ? 0.18 : 0,
          },
        ]}
        pointerEvents={open ? "auto" : "none"}
      >
        <View style={styles.panelContent}>
          <ScrollView style={{ marginTop: 12, flex: 1 }} contentContainerStyle={{ paddingBottom: 24 }}>
            {!loading && conversations.length === 0 ? (
              <View style={{ paddingVertical: 8 }}>
                <ThemedText>No conversations</ThemedText>
              </View>
            ) : null}
            {conversations.map((c) => (
              <View key={c.id} style={styles.convoRowRow}>
                <TouchableOpacity
                  style={styles.convoRowTouchable}
                  onPress={() => {
                    setOpen(false);
                    onSelectConversation?.({ id: c.id, title: c.title ?? null });
                  }}
                  accessibilityLabel={`Open conversation ${c.title ?? c.id}`}
                >
                  <View style={{ paddingVertical: 8 }}>
                    <ThemedText>{c.title ?? `Conversation ${c.id.slice(0, 6)}`}</ThemedText>
                    {c.last_activity_at ? (
                      <ThemedText style={{ fontSize: 12, color: Colors.light.icon }}>
                        {new Date(c.last_activity_at).toLocaleString()}
                      </ThemedText>
                    ) : null}
                  </View>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.archiveButton}
                  onPress={() => void archiveConversation(c.id)}
                  accessibilityLabel={`Archive conversation ${c.title ?? c.id}`}
                >
                  <ThemedText style={styles.archiveButtonText}>Archive</ThemedText>
                </TouchableOpacity>
              </View>
            ))}
            {loading ? (
              <View style={{ paddingVertical: 8 }}>
                <Button title="Loading..." onPress={() => {}} />
              </View>
            ) : null}
          </ScrollView>
          <View style={styles.footerContainer} pointerEvents="box-none">
            <Button title="New Conversation" onPress={startNewConversation} />
          </View>
        </View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  hamburger: {
    position: "absolute",
    top: 65,
    left: 16,
    zIndex: 1100,
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "flex-start",
    gap: 3,
    padding: 10,
    borderRadius: 8,
    backgroundColor: "rgba(255,255,255,0.01)",
    shadowColor: "#000",
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  line: {
    width: 24,
    height: 3,
    backgroundColor: Colors.light.icon,
    borderRadius: 2,
    marginVertical: 2,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.18)",
    zIndex: 1000,
  },
  panel: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 0,
    backgroundColor: Colors.light.background,
    borderTopRightRadius: 18,
    borderBottomRightRadius: 18,
    borderRightWidth: 1,
    borderColor: Colors.light.icon,
    paddingTop: 60,
    paddingHorizontal: 18,
    shadowColor: "#000",
    shadowOffset: { width: 2, height: 0 },
    shadowRadius: 12,
    elevation: 8,
    zIndex: 1200,
  },
  panelContent: {
    padding: 8,
    flex: 1,
  },
  convoRowRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottomWidth: 1,
    borderColor: Colors.light.icon,
    paddingVertical: 6,
  },
  convoRowTouchable: {
    flex: 1,
  },
  archiveButton: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    marginLeft: 8,
    borderRadius: 6,
    backgroundColor: "transparent",
  },
  archiveButtonText: {
    color: "#d9534f",
    fontWeight: "600",
  },
  footerContainer: {
    alignItems: "center",
    paddingVertical: 12,
    backgroundColor: "transparent",
  },
});
