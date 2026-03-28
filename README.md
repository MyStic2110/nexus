# IPL Nexus 2026 - Premium Prediction Platform

A futuristic, high-performance backend and frontend for IPL matches prediction, migrated to a premium "Nexus" experience.

## Features
- **FastAPI Backend**: Asynchronous, production-ready REST & WebSocket API.
- **Nexus UI**: Futuristic glassmorphism design with dark mode and smooth animations.
- **Google OAuth2**: Seamless, secure authentication using Google One Tap and Sign-In.
- **MongoDB Atlas**: Scalable persistence for users and prediction history.
- **Redis Integration**: 
  - Ultra-fast leaderboard using sorted sets.
  - Real-time live updates via Pub/Sub and WebSockets.
- **Production Logging**: Integrated logging system for real-time monitoring and debugging.

## Setup Instructions

1. **Environment Setup**:
   Create a `.env` file from `.env.example`.
   ```bash
   GOOGLE_CLIENT_ID=your_client_id_here
   MONGO_URI=your_mongodb_uri
   REDIS_URL=redis://localhost:6379/0
   ```

2. **Backend Installation**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Application**:
   ```bash
   # Starts both backend and serves frontend
   python run.py
   ```

## Infrastructure
- **API Base**: `http://localhost:8000/`
- **Frontend**: Served automatically at root `/`
- **WebSocket**: `ws://localhost:8000/ws/{match_id}`

## Modern Architecture
The platform is designed for zero in-memory state, ensuring high availability and horizontal scalability across production clusters.
