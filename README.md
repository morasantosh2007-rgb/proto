# JARVIS: Autonomous Voice-Controlled Personal AI Assistant

JARVIS (Just A Rather Very Intelligent System) is a complete, hands-free personal AI assistant engineered to run locally on your laptop. Built with a modular event-driven architecture, JARVIS delivers low-latency speech recognition, neural voice synthesis, native OS automation, multi-step routines, persistent memory, and strict safety tiers.

---

## 🌟 Key Features

- **Hands-Free Wake Word & Follow-up**: Listens continuously for `"Jarvis"` with openWakeWord/acoustic spotting and an automatic 8-second conversational follow-up window.
- **Natural Neural Speech**: Free, streaming, ultra-realistic British neural voice (`en-GB-RyanNeural`) with zero API costs, plus offline Windows SAPI and gTTS fallbacks.
- **Local Speech-to-Text**: Offline transcription powered by `faster-whisper` (`base.en` with int8 quantization).
- **Hybrid Brain Engine**: Fast, zero-latency local intent engine for core tools (volume, apps, weather, news, system stats, routines) paired with pluggable LLMs (local Ollama or free Gemini/Groq APIs).
- **Windows Native Laptop Control**: Fuzzy-matched application launching, URL navigation, volume adjustments, media keys, screen locking, desktop screenshots, and background process verification.
- **Safety Tiers & Injection Defense**:
  - **Tier 1 (Auto)**: Read-only queries, app opening, volume, weather, news, system vitals.
  - **Tier 2 (Voice Confirm)**: Closing apps, sending emails, moving files.
  - **Tier 3 (Passphrase Confirm)**: File deletion, system configuration changes.
  - **Tier 4 (Hard Blocked)**: Prohibited paths (`.ssh`, `.aws`, credential vaults, system32) and destructive shell commands.
  - **Prompt Injection Defense**: Sanitizes external data (emails, RSS feeds, web text) so adversarial instructions are neutralized and never trigger tool calls.
- **Keyring-Backed Integrations**: Interactive setup wizard (`python -m jarvis setup`) for Gmail, Google Calendar, Outlook, Weather, and News with least-privilege scopes and OS Credential Manager security.
- **Diagnostics (`doctor`)**: Built-in self-inspection tool (`python -m jarvis doctor`) checking microphones, speakers, whisper models, and permissions.

---

## 🚀 One-Command Install & Run (Windows)

### Option 1: One-Command PowerShell Scripts
Open Windows PowerShell in the project directory:

```powershell
# 1. Install all dependencies and run diagnostics:
.\scripts\install.ps1

# 2. Start JARVIS in hands-free voice mode:
.\scripts\run.ps1
```

### Option 2: Manual Fast Setup
```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt

# Run system health diagnostics
python -m jarvis doctor

# Launch JARVIS in Voice Mode
python -m jarvis

# Launch JARVIS in Text Mode (keyboard-driven)
python -m jarvis --text

# Launch JARVIS in Dry-Run Mode (safe simulation)
python -m jarvis --dry-run
```

---

## ⏱️ 10-Minute First-Run Guide

1. **Verify Audio & Hardware**: Run `python -m jarvis doctor` to confirm that your microphone and audio output devices are recognized and operational.
2. **Launch Interactive Setup Wizard**: Run `python -m jarvis setup` (or say *"Jarvis, connect my email"*).
   - Follow the step-by-step guidance for Gmail or Google Calendar OAuth.
   - Credentials are saved securely to your Windows Credential Keyring (never in plaintext).
3. **Start JARVIS**: Run `python -m jarvis` (or `.\scripts\run.ps1`).
4. **Speak Your First Command**:
   - Say: *"Jarvis"*
   - Assistant: *"Yes, sir?"*
   - Say: *"Give me the morning briefing"*
   - JARVIS will deliver a structured briefing with weather, hardware status, agenda, and top tech news.

---

## 🎙️ Voice Command Cheat Sheet

| Category | Example Voice Commands | Execution Tier |
| :--- | :--- | :--- |
| **Morning Briefing** | *"Jarvis, give me the morning briefing"* | Tier 1 (Auto) |
| **Laptop Apps** | *"Jarvis, open Chrome and go to YouTube"* | Tier 1 (Auto) |
| | *"Launch Visual Studio Code"* | Tier 1 (Auto) |
| | *"Close Chrome"* | Tier 2 (Requires voice confirmation) |
| **Volume & Media** | *"Set volume to 30"* | Tier 1 (Auto) |
| | *"Mute audio"*, *"Pause music"*, *"Next track"* | Tier 1 (Auto) |
| **Workstation Safety**| *"Lock my laptop"* | Tier 1 (Auto) |
| | *"Take a screenshot"* | Tier 1 (Auto, saved to Desktop) |
| | *"Delete my project files"* | Tier 3 (Requires passphrase: *"jarvis authorize"*) |
| **System Status** | *"How is my laptop looking?"* | Tier 1 (Battery, CPU, disk, WiFi) |
| **Live Weather** | *"What is the weather in London?"* | Tier 1 (Zero-API wttr.in/Open-Meteo) |
| **Live News** | *"What are the latest tech headlines?"* | Tier 1 (Ars Technica, BBC, TechCrunch) |
| **Custom Routines** | *"Work mode"* | Tier 1 (Launches VS Code, sets volume) |
| | *"Focus mode"*, *"Wrap up"* | Tier 1 (Configurable in `config.yaml`) |
| **Persistent Memory** | *"Remember that my dentist is Dr. Smith"* | Tier 1 (Stored in SQLite) |
| | *"Who is my dentist?"* | Tier 1 (Natural recall) |
| **Email & Calendar** | *"Check my emails"* | Tier 1 (Read-only query) |
| | *"Draft an email to Alex saying sprint complete"* | Tier 1 (Drafting) |
| | *"Send it"* | Tier 2 (Explicit voice confirmation) |
| | *"What is on my schedule today?"* | Tier 1 (With conflict detection) |
| **Interruption** | Say *"Stop"* or start speaking while JARVIS speaks | Instant Barge-In |

---

## 🔒 Security & Privacy Architecture

1. **Zero Credential Exposure**: OAuth tokens and secrets are stored in the OS Keyring (`WinVaultKeyring` on Windows / `SecretService` on Linux / `Keychain` on macOS).
2. **Strict Blocklists**: Files in `.ssh`, `.aws`, credential vaults, and system directories (`Windows/System32`) can never be opened, read, or modified.
3. **Prompt Injection Neutralization**: All external text (incoming emails, RSS feeds, scraped web pages) is stripped of adversarial instructions (e.g. `ignore previous instructions`, `execute script`) and encapsulated in strict `[DATA ONLY]` delimiters.
4. **Audit Trail**: Every command, permission tier, confirmation, and outcome is logged to `jarvis_audit.db`.

---

## ⚠️ Known Limitations & Workarounds

1. **Edge-TTS WebSocket Rate Limits**: Microsoft's free edge-tts endpoint may intermittently return a 403 status during high traffic.
   - *Workaround*: JARVIS includes an automatic fallback cascade to Windows native SAPI (`System.Speech`) and `gTTS`, ensuring continuous voice synthesis without interruption.
2. **Background Noise Wake Word Spurious Triggers**: High ambient room noise can occasionally trigger false wake words.
   - *Workaround*: Adjust `system.sensitivity` in `config.yaml` (default: 0.5) or increase `audio.energy_threshold`.
3. **Offline Brain Scope**: When running in 100% offline mode without an LLM API key, JARVIS uses its deterministic local intent engine. Open-ended general knowledge questions default to conversational chief-of-staff updates.
   - *Workaround*: Install local [Ollama](https://ollama.ai) (`ollama run llama3.2`) or add a free [Google AI Studio Gemini key](https://aistudio.google.com/) to `.env`.

---

## 🗺️ Prioritized Upgrade Roadmap

1. **Vision & Screen Understanding**: Multimodal desktop analysis via local Moondream2 or Gemini Flash Vision for visual question answering.
2. **Smart Home Integration**: Direct Home Assistant WebSocket integration for room lights, thermostats, and smart plugs.
3. **Phone Notification Sync**: Integration with KDE Connect or Pushbullet to read incoming smartphone SMS and calls.
4. **Multi-Language Support**: Multilingual wake-word detection and translation streaming.
