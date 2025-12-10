# NLIP Swarm – Frontend

Expo/React Native client for the NLIP Swarm project. The mobile experience captures text, audio, and images from farmers in East Africa, wraps them in NLIP envelopes, and exchanges them with the Python agent swarm described in the root README. This document focuses only on the frontend workspace found in `frontend/`.

## Tech Stack

- **Framework**: React Native with Expo Router (file-based routing)
- **Language**: TypeScript
- **UI utilities**: Custom themed components, Drawout sheet, Message composer
- **Device APIs**: `expo-image-picker`, `expo-document-picker`, `expo-file-system`, `expo-haptics`
- **State/Persistence**: React hooks + AsyncStorage

## Requirements

- Node.js 18+ (Expo SDK 54 requirement)
- npm or pnpm (examples below use npm)
- Xcode (for iOS simulator) and/or Android Studio if you want native emulators
- Backend server running from `/backend` (provides `/nlip`, `/me`, `/conversations` endpoints). The Expo app reads the API origin from `EXPO_PUBLIC_API_BASE`.

## Getting Started

1. **Install dependencies**
	```bash
	cd frontend
	npm install
	```

2. **Set environment variables**
	- Duplicate `example.env` to `.env` or export `EXPO_PUBLIC_API_BASE` in your shell.
	- Typical value during local development: `http://localhost:8024` (matches the FastAPI session server).

3. **Start the Expo dev server**
	```bash
	npm run start
	```
	- Press `i` for iOS simulator, `a` for Android, or `w` for web.
	- Expo Go users can scan the QR code printed in the terminal.

Keep both processes running so the frontend can log in, fetch `/me`, and send NLIP traffic.

## npm Scripts

| Command          | Description |
|------------------|-------------|
| `npm run start`  | Expo dev server with tunnel (default workflow). |
| `npm run android`| Build & launch the Android binary via `expo run:android`. |
| `npm run ios`    | Build & launch the iOS binary via `expo run:ios`. |
| `npm run web`    | Serve the app via Expo Web. |
| `npm run lint`   | Run Expo’s ESLint config. |

## Directory Guide

```
frontend/
├── app/          # Expo Router routes (login, signup, tabs, profile)
├── components/   # Chat UI (ConversationList, MessageComposer, SelectedAttachment, etc.)
├── hooks/        # Custom hooks (image attachments, persisted conversations)
├── constants/    # Theme definitions
├── lib/          # Shared helpers (avatar normalization, navigation facade)
├── types/        # Shared TypeScript types for chat data
└── scripts/      # Utility scripts (e.g., reset-project.js)
```

## Environment Variables

| Name                      | Purpose |
|---------------------------|---------|
| `EXPO_PUBLIC_API_BASE`    | Fully qualified URL of the backend (e.g., `https://swarm.example.com`). Exposed to the client. |

For backend instructions or full-stack deployment (Docker Compose), refer to the root-level `README.md`.
