# 🛡️ SafeAI

**AI-powered Telegram safety and support assistant**

SafeAI is a Telegram bot designed to provide conversational support, personal memory, safety analysis, SOS alerts, trusted contacts, and voice interaction.

The project is built with Python and integrates AI services with a local SQLite database and Telegram Bot API.

> **Project status:** Active development 🚧

---

## ✨ Features

### 🤖 AI Conversation

* Natural conversational interaction
* Context-aware responses
* Conversation history
* Personal memory
* AI-powered safety analysis
* Local fallback mode when the AI API is unavailable

### 🧠 Personal Memory

SafeAI can store relevant information from previous conversations and use it to maintain context.

The memory system is designed to make conversations more personalized instead of treating every message as a new conversation.

### 🚨 SOS System

Users can activate an emergency SOS:

* SOS button inside Telegram
* `/sos` command
* SOS events stored in the database
* Safety level and event score
* Trusted contact notifications
* Planned location sharing

### 👤 Trusted Contacts

Users can invite trusted people using a personal Telegram invitation link.

Trusted contacts can receive SOS notifications when the user requests help.

### 🔊 Voice Interaction

SafeAI includes a local voice system with Russian speech models.

Current voice models:

* Russian female voice — Irina
* Russian male voice — Dmitri

The project is designed to support:

```text
🎤 Voice message
      ↓
Speech-to-Text
      ↓
AI processing
      ↓
Text-to-Speech
      ↓
🔊 Voice response
```

### 🔐 Security

Security is treated as an important part of the project architecture.

Implemented or planned protections include:

* Environment variables for API credentials
* `.env` excluded from Git
* Database excluded from Git
* Prompt-injection protection
* Privacy filtering
* Rate limiting
* Input validation
* Protected administrative functionality
* Server hardening
* Secure SSH configuration
* Firewall configuration
* Automatic backups

---

## 🏗️ Architecture

```text
                    Telegram
                       │
                       ▼
                ┌─────────────┐
                │   main.py   │
                └──────┬──────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     AI Router     Safety Engine   Memory
          │            │            │
          ▼            ▼            ▼
     AI Engine     Risk Analysis  SQLite
          │
          ▼
      OpenAI API
          │
          ▼
    AI Response
```

---

## 📁 Project Structure

```text
safeai/
│
├── main.py
├── ai_engine.py
├── ai_router.py
├── ai_core.py
├── safety_engine.py
│
├── memory.py
├── personal_memory.py
├── privacy_filter.py
├── rate_limiter.py
├── voice_service.py
│
├── database.py
├── config.py
│
├── voice_models/
│   ├── ru_RU-irina-medium.onnx
│   ├── ru_RU-irina-medium.onnx.json
│   ├── ru_RU-dmitri-medium.onnx
│   └── ru_RU-dmitri-medium.onnx.json
│
├── tests/
│   ├── test_ai.py
│   ├── test_personal_memory.py
│   ├── test_privacy_filter.py
│   └── test_rate_limiter.py
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🛠️ Technologies

| Technology          | Purpose                 |
| ------------------- | ----------------------- |
| Python              | Backend                 |
| python-telegram-bot | Telegram integration    |
| OpenAI API          | AI responses            |
| SQLite              | Local database          |
| ONNX                | Local voice models      |
| Git                 | Version control         |
| Linux               | Development environment |

---

## 🔒 Environment Variables

Create a local `.env` file based on `.env.example`:

```env
BOT_TOKEN=
AI_API_KEY=
ADMIN_ID=
RATE_LIMIT_REQUESTS_PER_MINUTE=40
```

**Never commit ****`.env`**** to Git.**

Secrets are intentionally excluded from the repository.

---

## 🚀 Local Installation

Clone the repository:

```bash
git clone git@github.com:sashapanov93-tech/safeai.git
cd safeai
```

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create environment configuration:

```bash
cp .env.example .env
```

Edit `.env` and add the required credentials.

Run SafeAI:

```bash
python main.py
```

Expected output:

```text
SafeAI запущен 🚀
```

---

## 🧪 Testing

Run individual tests:

```bash
python test_ai.py
python test_personal_memory.py
python test_privacy_filter.py
python test_rate_limiter.py
```

---

## 🗺️ Roadmap

### Completed

* [x] Telegram bot
* [x] AI conversation
* [x] SQLite database
* [x] Conversation history
* [x] Personal memory foundation
* [x] Safety analysis
* [x] SOS system
* [x] Trusted contacts
* [x] Privacy filtering
* [x] Rate limiting foundation
* [x] Local Russian voice models

### In Development

* [ ] Voice message recognition
* [x] AI voice responses
* [ ] Automatic learning from user feedback
* [ ] Advanced personal memory
* [x] Location sharing during SOS
* [ ] Improved emergency workflow
* [ ] Production VPS deployment
* [ ] Server monitoring
* [ ] Automated backups
* [ ] Advanced anti-abuse protection

---

## 🎯 Project Goals

The long-term goal of SafeAI is to create a reliable AI assistant capable of combining:

```text
AI
+
Personal Memory
+
Safety Analysis
+
SOS
+
Trusted Contacts
+
Voice Interaction
```

into a single Telegram-based safety and support platform.

---

## ⚠️ Disclaimer

SafeAI is a software project and does not replace professional medical, psychological, emergency, or law-enforcement services.

In a real emergency, users should contact appropriate local emergency services.

---

## 👨‍💻 Author

**Sasha Panov**

GitHub:

https://github.com/sashapanov93-tech

---

## 📄 License

License information will be added before the production release.
