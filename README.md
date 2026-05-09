# 🏏 IPL Nexus 2026

**The Premium Prediction Platform for Cricket Enthusiasts.**

IPL Nexus is a high-performance, futuristic web application designed for real-time IPL match predictions. Built with a focus on speed, security, and a premium user experience (the "Nexus" design system), it provides a seamless interface for fans to engage with the game.

---

## 🚀 Key Features

- **Futuristic UI/UX**: A "Nexus" themed frontend featuring glassmorphism, smooth animations, and a sleek dark mode.
- **Real-time Synchronization**: WebSocket-driven live match updates and instant leaderboard shifts.
- **Secure Authentication**: Integrated Google OAuth2 with One Tap sign-in for a friction-less experience.
- **Scalable Architecture**: FastAPI-powered backend designed for high concurrency and zero in-memory state.
- **Production-grade Logging**: Comprehensive logging system for monitoring, debugging, and audit trails.
- **Automated Intelligence**: Background agents for live data scraping and synchronization.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn
- **Frontend**: Vanilla JS/HTML/CSS (Nexus Design System)
- **Database**: MongoDB Atlas
- **Real-time**: WebSockets
- **Deployment**: Docker, Railway

---

## 📂 Project Structure

```text
.
├── app/                # Backend source code
│   ├── auth/           # OAuth and session management
│   ├── routes/         # API endpoints (Auth, Match, WebSocket)
│   ├── models/         # Database schemas
│   ├── services/       # Business logic and external integrations
│   └── main.py         # App entry point
├── frontend/           # Static frontend assets
├── tools/              # Utility scripts and maintenance tools
├── scripts/            # Automation agents (e.g., Cricbuzz scraper)
├── Dockerfile          # Containerization config
└── start.sh            # Production startup script
```

---

## ⚙️ Setup & Installation

### 1. Environment Configuration
Clone the `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```
Key variables required:
- `MONGO_URI`: Your MongoDB connection string.
- `GOOGLE_CLIENT_ID`: Your Google OAuth Client ID.

### 2. Backend Setup
Install the necessary Python dependencies:
```bash
pip install -r requirements.txt
```

### 3. Running the Application
You can start the server and the automation agent using the provided shell script:
```bash
bash start.sh
```
Or manually run the FastAPI server:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🛠️ Utility Tools
The `/tools` directory contains various scripts for:
- Database cleanup and maintenance.
- Match schedule imports (including PDF processing).
- Session management and debugging.

---

## 🌐 Infrastructure
- **API Base**: `http://localhost:8000/`
- **Frontend**: Automatically served at `/`
- **WebSocket**: `ws://localhost:8000/ws/{match_id}`

---

## 📄 License
This project is proprietary and built for the IPL 2026 season.
