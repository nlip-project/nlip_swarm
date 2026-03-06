import { Ionicons } from "@expo/vector-icons";
import React, { useEffect, useRef } from "react";
import { Animated, Easing, StyleSheet, View } from "react-native";
import { Colors } from "@/constants/theme";

type ThemeShape = typeof Colors.light;

interface TypingIndicatorProps {
  colors: ThemeShape;
}

const DOT_COUNT = 3;
const DOT_DELAY_MS = 140;
const DOT_BASE_OPACITY = 0.25;

export function TypingIndicator({ colors }: TypingIndicatorProps) {
  const dotValues = useRef(
    Array.from({ length: DOT_COUNT }, () => new Animated.Value(DOT_BASE_OPACITY))
  ).current;

  useEffect(() => {
    const loops = dotValues.map((value, index) => {
      const animation = Animated.loop(
        Animated.sequence([
          Animated.delay(index * DOT_DELAY_MS),
          Animated.timing(value, {
            toValue: 1,
            duration: 220,
            easing: Easing.out(Easing.quad),
            useNativeDriver: true,
          }),
          Animated.timing(value, {
            toValue: DOT_BASE_OPACITY,
            duration: 220,
            easing: Easing.in(Easing.quad),
            useNativeDriver: true,
          }),
          Animated.delay((DOT_COUNT - index - 1) * DOT_DELAY_MS),
        ])
      );
      animation.start();
      return animation;
    });

    return () => {
      loops.forEach((animation) => animation.stop());
    };
  }, [dotValues]);

  return (
    <View style={styles.row} pointerEvents="none" accessibilityLabel="Assistant is typing">
      <View style={[styles.avatar, { borderColor: colors.icon, backgroundColor: colors.background }]}>
        <Ionicons name="person" size={18} color={colors.icon} />
      </View>

      <View
        style={[
          styles.bubble,
          {
            backgroundColor: colors.messageOtherBg,
            borderColor: colors.icon,
          },
        ]}
      >
        <View style={styles.dotRow}>
          {dotValues.map((value, idx) => (
            <Animated.View
              key={`typing-dot-${idx}`}
              style={[
                styles.dot,
                {
                  backgroundColor: colors.messageOtherText,
                  opacity: value,
                  transform: [
                    {
                      translateY: value.interpolate({
                        inputRange: [DOT_BASE_OPACITY, 1],
                        outputRange: [2, -1],
                      }),
                    },
                  ],
                },
              ]}
            />
          ))}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    gap: 8,
    paddingHorizontal: 20,
  },
  avatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
  },
  bubble: {
    borderRadius: 16,
    borderWidth: 1,
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginVertical: 4,
  },
  dotRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
  },
});
