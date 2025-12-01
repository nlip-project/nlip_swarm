import React, { useState, useEffect } from "react";
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
  Pressable,
  Button,
} from "react-native";
import { Colors } from "@/constants/theme";
import { ThemedText } from '@/components/themed-text';

export function Drawout({
  triggerPosition,
  clearChat,
  onSelectConversation,
}: {
  triggerPosition?: { top: number; left: number };
  clearChat?: () => void;
  onSelectConversation?: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [conversations, setConversations] = useState<Array<{ id: string; title?: string; last_activity_at?: string }>>([]);
  const [loading, setLoading] = useState(false);
  const screenWidth = Dimensions.get("window").width;
  const panelWidth = Math.min(260, screenWidth * 0.8);
  const slideAnim = useState(new Animated.Value(-panelWidth))[0];

  // Animate panel in/out
  useEffect(() => {
    Animated.timing(slideAnim, {
      toValue: open ? 0 : -panelWidth,
      duration: 260,
      useNativeDriver: true,
    }).start();
    if (open) {
      // fetch conversations when panel opens
      (async () => {
        setLoading(true);
        try {
          const API_BASE = (global as any).API_BASE || 'http://0.0.0.0:8024';
          const resp = await fetch(`${API_BASE}/conversations`, { credentials: 'include' });
          if (resp.ok) {
            const data = await resp.json();
            setConversations(data.conversations || []);
          } else {
            setConversations([]);
          }
        } catch (e) {
          console.warn('Failed to fetch conversations', e);
          setConversations([]);
        } finally {
          setLoading(false);
        }
      })();
    }
  }, [open, panelWidth, slideAnim]);

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      {/* Overlay */}
      {open && (
        <Pressable
          style={styles.overlay}
          onPress={() => setOpen(false)}
          accessibilityLabel="Close drawout panel"
        />
      )}
      {/* Hamburger icon */}
      <TouchableOpacity
        style={[
          styles.hamburger,
          triggerPosition
            ? { top: triggerPosition.top, left: triggerPosition.left }
            : null,
        ]}
        onPress={() => setOpen((v) => !v)}
        activeOpacity={0.7}
        accessibilityLabel="Open drawout panel"
      >
        <View style={styles.line} />
        <View style={styles.line} />
        <View style={styles.line} />
      </TouchableOpacity>
      {/* Sliding panel */}
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
          <Button
            title="Clear"
            onPress={clearChat}
            accessibilityLabel="Clear chat feed"
          />
          {/* Conversations list */}
          <View style={{ marginTop: 12 }}>
            {!loading && conversations.length === 0 ? (
              <View style={{ paddingVertical: 8 }}>
                <ThemedText>No conversations</ThemedText>
              </View>
            ) : null}
            {conversations.map((c) => (
              <TouchableOpacity
                key={c.id}
                style={styles.convoRow}
                onPress={() => {
                  setOpen(false);
                  if (onSelectConversation) onSelectConversation(c.id);
                }}
                accessibilityLabel={`Open conversation ${c.title ?? c.id}`}
              >
                <View style={{ paddingVertical: 8 }}>
                  <ThemedText>{c.title ?? `Conversation ${c.id.slice(0,6)}`}</ThemedText>
                  {c.last_activity_at ? <ThemedText style={{ fontSize: 12, color: Colors.light.icon }}>{new Date(c.last_activity_at).toLocaleString()}</ThemedText> : null}
                </View>
              </TouchableOpacity>
            ))}
            {loading ? <View style={{ paddingVertical: 8 }}><Button title="Loading..." onPress={() => {}} /></View> : null}
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
  tabRow: {
    flexDirection: "row",
    marginBottom: 12,
    gap: 10,
  },
  tab: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 8,
    backgroundColor: "transparent",
  },
  tabSelected: {
    backgroundColor: Colors.light.tint,
  },
  tabText: {
    color: Colors.light.icon,
    fontWeight: "500",
    fontSize: 16,
  },
  tabTextSelected: {
    color: Colors.light.buttonText,
  },
  panelContent: {
    padding: 8,
  },
  panelText: {
    fontSize: 17,
    color: Colors.light.text,
  },
  convoRow: {
    borderBottomWidth: 1,
    borderColor: Colors.light.icon,
    paddingVertical: 6,
  },
});
