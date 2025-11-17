# NLIP Swarm

A senior design project at the University of Delaware focused on the open source NLIP protocol. 

## Description



## Tech Stack

### Frontend
- **Framework:** React Native with Expo
- **Routing:** Expo Router (file-based routing)
- **Language:** TypeScript

### Backend
- **Language:** Python

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
   npx run web
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
   pip install -r .\requirements.txt
   ```

3. Run The backend server
   ```bash
   python -m app.system.main
   ```

## Contributors

- **John Fulkerson** <jtfulky@udel.edu>
- **Mason Kulikowski** <masonkul@udel.edu>
- **Christopher Calderone** <ccald@udel.edu>
- **Kevin Kramer** <kkramer@udel.edu>
- **Benjamin Zlatin** <bzlatin@udel.edu>