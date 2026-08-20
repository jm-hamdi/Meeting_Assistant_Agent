# Meeting Assistant Agent

A local-first AI meeting assistant that captures audio from Zoom, Teams, Google Meet, or any browser-based call — then transcribes, summarises, and creates follow-up tasks automatically. No cloud APIs required for core features.

---

## How It Works

```
Your call (Zoom / Teams / Meet)
        ↓
BlackHole loopback (system audio capture)
        ↓
faster-whisper (local transcription — no internet)
        ↓
Local LLM via LM Studio (summary + action items)
        ↓
tasks.md  /  Notion  /  GitHub Issues
```

---

## Requirements

- **macOS** 12+ (Apple Silicon or Intel)
- **Python** 3.10+
- **LM Studio** — running locally with any OpenAI-compatible model (e.g. Llama 3.1 8B)
- **BlackHole 2ch** — virtual audio loopback (free, one `brew install`)

---

## Installation

```bash
# 1. Clone the repo
git clone <repo-url>
cd Meeting_Assistant_Agent

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -e .

# 4. Copy and edit config
cp .env.example .env
```

---

## One-Time macOS Audio Setup

This is required to capture system audio (call output + your mic) rather than just your microphone.

**Step 1 — Install BlackHole:**
```bash
brew install blackhole-2ch
sudo killall coreaudiod   # restart audio daemon (or just reboot)
```

**Step 2 — Create a Multi-Output Device:**
1. Open **Audio MIDI Setup** (search in Spotlight)
2. Click **+** → **Create Multi-Output Device**
3. Check both **MacBook Pro Speakers** and **BlackHole 2ch**
4. Right-click the new device → **Use This Device For Sound Output**

**Step 3 — Set your meeting app output:**
- In Zoom: Settings → Audio → Speaker → **Multi-Output Device**
- In Teams: Settings → Devices → Speaker → **Multi-Output Device**
- For browser meetings (Google Meet, etc.): set system output to Multi-Output Device — it works automatically

> **No BlackHole?** The assistant falls back to your microphone only (captures your voice but not remote participants). Set `MEETASSIST_AUDIO_FALLBACK_TO_MIC=true` in `.env`.

---

## Configuration

All settings are in `.env` (copy from `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `MEETASSIST_LM_STUDIO_BASE_URL` | `http://127.0.0.1:1234/v1` | LM Studio endpoint |
| `MEETASSIST_LM_STUDIO_MODEL_ID` | `openai/lmstudio-community/meta-llama-3.1-8b-instruct` | Model to use |
| `MEETASSIST_WHISPER_MODEL_SIZE` | `small.en` | Whisper model: `tiny.en` / `base.en` / `small.en` / `medium.en` |
| `MEETASSIST_WHISPER_DEVICE` | `auto` | `cpu` / `cuda` / `auto` |
| `MEETASSIST_AUDIO_DEVICE_NAME` | `BlackHole 2ch` | Loopback device name |
| `MEETASSIST_AUDIO_FALLBACK_TO_MIC` | `true` | Fall back to mic if BlackHole not found |
| `MEETASSIST_OUTPUT_DIR` | `outputs` | Where meeting sessions are saved |
| `MEETASSIST_NOTION_TOKEN` | _(empty)_ | Notion integration token (optional) |
| `MEETASSIST_NOTION_DATABASE_ID` | _(empty)_ | Notion database ID (optional) |
| `MEETASSIST_GITHUB_TOKEN` | _(empty)_ | GitHub personal access token (optional) |
| `MEETASSIST_GITHUB_REPO` | _(empty)_ | GitHub repo in `owner/repo` format (optional) |

---

## Usage

### Interactive REPL
```bash
meet
```
Then type natural language commands:
```
Meet ❯ Record the standup for 30 minutes and create tasks when done
Meet ❯ Transcribe outputs/2026-08-20_standup/audio.wav
Meet ❯ Show me yesterday's meeting summary
```

### Direct flags (no agent needed)
```bash
# Record for 45 minutes, then auto-transcribe, summarise, and create tasks
meet --record 2700

# Transcribe an existing audio file
meet --transcribe outputs/2026-08-20_standup/audio.wav

# List all past meeting sessions
meet --list

# Override Whisper model for this run
meet --whisper medium.en --record 3600

# Verbose logging
meet -v
```

### Python module
```bash
python -m meet_assistant
```

---

## Output Structure

Every meeting session is saved in its own folder:

```
outputs/
└── 2026-08-20_standup/
    ├── audio.wav          # raw recording
    ├── transcript.txt     # timestamped speech-to-text
    ├── summary.md         # bullets + decisions + blockers
    └── tasks.md           # checkbox list with owners and deadlines
```

**Example `tasks.md`:**
```markdown
---
meeting: "2026-08-20_standup"
generated: "2026-08-20T10:30:00"
total_tasks: 3
---

## Action Items

- [ ] **Alice** — Review and merge PR #42 _(by 2026-08-21)_
- [ ] **Bob** — Update deployment documentation _(by 2026-08-22)_
- [ ] **unknown** — Follow up with design team
```

---

## Optional Integrations

### Notion
1. Create a Notion integration at [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Share your database with the integration
3. Set `MEETASSIST_NOTION_TOKEN` and `MEETASSIST_NOTION_DATABASE_ID` in `.env`

### GitHub Issues
1. Create a personal access token with `repo` scope at [github.com/settings/tokens](https://github.com/settings/tokens)
2. Set `MEETASSIST_GITHUB_TOKEN` and `MEETASSIST_GITHUB_REPO=owner/repo` in `.env`

When tokens are set, pass flags to the agent:
```
Meet ❯ Create tasks from the last meeting and push to GitHub
```

---

## Running Tests

```bash
# All tests (excluding E2E)
pytest -m "not e2e"

# Specific module
pytest tests/test_transcriber.py -v

# E2E tests (requires microphone access)
pytest -m e2e -v
```

---

## Project Structure

```
meet_assistant/
├── core/
│   ├── audio_capture.py   # BlackHole + sounddevice recording
│   ├── transcriber.py     # faster-whisper engine
│   ├── summarizer.py      # LiteLLM → local LLM
│   └── task_writer.py     # markdown / Notion / GitHub output
├── tools/                 # auto-discovered @tool functions
│   ├── capture.py         # start_recording, stop_recording, recording_status
│   ├── transcribe.py      # transcribe_audio
│   ├── summarize.py       # summarize_transcript
│   ├── tasks.py           # create_tasks
│   ├── meeting.py         # run_full_pipeline, process_recording
│   └── storage.py         # list_meetings, get_meeting
├── agent.py               # smolagents CodeAgent wired to LM Studio
├── cli.py                 # meet command entry point
└── settings.py            # all config via MEETASSIST_* env vars
```

---

## License

MIT
