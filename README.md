# NLIP Swarm

NLIP Swarm is a University of Delaware senior design project built in collaboration with IBM to explore the Natural Language Interaction Protocol (NLIP) in a real-world sustainability scenario. Our team is creating a smartphone app paired with server-side AI agents that help farmers in Tanzania and Uganda access translation, lookup, and sensor-driven insights without needing proprietary vendor stacks.

## Project Goal

Dinesh’s plan splits the work into two tracks:
- **Mobile experience** – a React Native (Expo) application that can use onboard sensors, collect farmer input, and securely exchange NLIP envelopes with the backend.
- **Agent registrar & swarm manager** – Python services that host and orchestrate NLIP-compliant agents (translation, text lookup, audio/image understanding today; more sophisticated chains later).

The long-term objective is to ship a reference implementation that demonstrates how vendor-neutral NLIP traffic can move between lightweight edge clients and richer cloud-based reasoning services.

## NLIP in this project

NLIP is an open, multi-modal, JSON-based protocol for agent-to-agent communication. In NLIP Swarm we:
- Use NLIP envelopes to route requests between the Expo client and Python agents.
- Adhere to HTTPS bindings for transport, leaving room for future upgrades (WebRTC, QUIC, etc.).
- Focus on policy-aware, secure message exchange while keeping the rest of the stack cloud-agnostic.

## Tech Stack

### Frontend
- **Framework:** React Native with Expo
- **Routing:** Expo Router (file-based routing)
- **Language:** TypeScript

### Backend
- **Language:** Python

## Architecture Overview

```
frontend/   # Expo mobile client that captures text/audio/image inputs
backend/    # Python agent services, registrar, and NLIP session server
compose.yaml# Docker Compose for running both tiers together
```

## Project Structure

```
nlip_swarm/
├── frontend/          # React Native mobile application
│   ├── app/          # Expo Router file-based routes
│   ├── components/   # Reusable UI components
│   ├── constants/    # Theme and app constants
│   └── hooks/        # Custom React hooks
└── backend/          # Python backend services
```

## Getting Started

### Frontend

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run start
   ```

4. Open the app:
   - Press `i` for iOS simulator
   - Press `a` for Android emulator
   - Press `w` for web browser
   - Scan QR code with Expo Go app on your device

### Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install Requirements
   ```bash
   pip install -r requirements.txt
   ```

3. Run The backend server
   ```bash
   python -m app.system.main
   ```

### Docker Compose (full stack)

1. Create environment files from the variables below, or set them directly in your shell.

   **Frontend** — create `frontend/.env`:
   ```
   EXPO_PUBLIC_API_BASE=http://localhost:8024
   ```

   **Backend** — create `backend/.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/nlip_db
   NLIP_LOG_LEVEL=INFO
   # Optional: override LLM endpoint and model
   OLLAMA_URL=http://ollama:11434
   OLLAMA_MODEL=ai/llama3.2:3B-Q4_0
   ```

2. Start the full stack with Docker:
   ```bash
   docker compose up --build
   ```
3. The coordinator API will be available at http://localhost:8024, and Expo DevTools will be available on the forwarded ports.
4. If you are using Expo Go on a physical device, set `EXPO_PUBLIC_API_BASE` to your host LAN IP before running compose.

## Contributors

- **John Fulkerson** <jtfulky@udel.edu>
- **Mason Kulikowski** <masonkul@udel.edu>
- **Christopher Calderone** <ccald@udel.edu>
- **Kevin Kramer** <kkramer@udel.edu>
- **Benjamin Zlatin** <bzlatin@udel.edu>
- **Tyler Walsh** <tjwalsh@udel.edu>