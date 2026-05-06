# NLIP Swarm Backend

Multi‑agent backend for the NLIP protocol, built on FastAPI. It exposes
an HTTP NLIP endpoint that fans out to multiple specialized agents for
text, translation, image understanding, and audio (Whisper) processing.

This README describes the current code layout (including the newer
coordinator/agent architecture) and how to run and exercise it locally.

All model access in this backend is local. No OpenAI or Cerebras API keys are required.

---

## High‑Level Architecture

- **Frontend → Coordinator**  
  Clients send NLIP messages over HTTP to a coordinator server
  (FastAPI) at `/nlip`. The coordinator maintains per‑browser sessions
  via cookies.

- **Coordinator → Agents**  
  The coordinator is an NLIP agent (`CoordinatorNlipAgent`) that can
  discover and call other NLIP agents via tools:

  - `connect_to_server(url)`
  - `send_to_server(url, message)`
  - `get_all_capabilities()`

  It discovers agent endpoints from `app.system.config.DEFAULT_AGENT_ENDPOINTS`.

- **Agents as FastAPI apps**  
  Each logical agent (basic LLM, translation, image recognition, text)
  is wrapped in a small FastAPI app using
  `app.http_server.nlip_session_server.NlipSessionServer`. All expose:

  - `POST /nlip` – process an `NLIP_Message` and return another.
  - `GET /health` – simple health check.

- **Process topology**  
  `app.system.main` uses `MountSpec` to:

  - Start the coordinator over HTTP on `http://0.0.0.0:8024/nlip`.
  - Register the agent apps in‑process behind `mem://` URLs so the
    coordinator can reach them without extra network hops.

---

## Code Layout

Top‑level in `backend/`:

- `app/`
  - `agents/`
    - `base.py` – generic tool‑using LLM `Agent` built on `litellm`.
    - `nlip_agent.py` – NLIP‑aware agent base class (specializes `Agent` for NLIP messages).
    - `coordinator_nlip_agent.py` – coordinator agent with tools to talk to other NLIP servers.
    - `translation.py` – `TranslationNlipAgent` using a local LLM (`TRANSLATION_MODEL`) with `googletrans` as fallback.
    - `imageRecognition.py` – `ImageRecognitionNlipAgent` using Ollama’s image model (e.g. `llava`).
    - `textAgent.py` – `LLamaTextAgent` wrapper around the Ollama text model for NLIP text tasks.
    - `sound.py` – `SoundAgent` for Whisper‑based ASR plus optional translation.
  - `servers/`
    - `basic_server.py` – wraps a generic `Agent` in a `NlipSessionServer`.
    - `coordinator_server.py` – exposes the `CoordinatorNlipAgent` as HTTP `/nlip`.
    - `translate_server.py` – NLIP translation server using `TranslationNlipAgent`.
    - `image_server.py` – NLIP image recognition server using `ImageRecognitionNlipAgent`.
    - `text_server.py` – NLIP text server using `LLamaTextAgent`.
  - `http_server/`
    - `nlip_session_server.py` – reusable FastAPI `NlipSessionServer` + `SessionManager` abstraction with cookie‑based sessions and `/nlip` + `/health` routes.
  - `http_client/`
    - `nlip_async_client.py` – async client that can talk to HTTP URLs or in‑process `mem://` endpoints via `httpx.ASGITransport`.
  - `system/`
    - `config.py` – defines `MOUNT_URLS` and `DEFAULT_AGENT_ENDPOINTS`.
    - `mount_spec.py` – utility that starts HTTP servers or registers in‑process apps for `mem://` URLs.
    - `main.py` – main entrypoint that wires coordinator + agents and runs them.
  - `deprecated/`
    - Original “supervisor” stack (`supervisor.py`, `api.py`, `routes/`) that used a monolithic app at `/nlip` with its own translation and image logic. Kept for reference; some pieces are out of sync with the current agents.
  - `_logging.py` – logging configuration used throughout.
  - `__init__.py` – defines `MEM_APP_TBL`, the registry for in‑process apps.

Other top‑level files:

- `run.py` – legacy uvicorn launcher (`app.main:app`, currently not wired into the new coordinator stack).
- `requirements.txt` – backend Python dependencies.
- `pyproject.toml` – project metadata (`nlip-swarm-registrar`).
- `tests/` – pytest suite for routes, translation/image flow, and sound agent.

---

## HTTP Endpoints

### Coordinator Server (current main entrypoint)

When you run `app.system.main`, it mounts the coordinator server at:

- `POST /nlip` – accept an `NLIP_Message` and return a response message.
- `GET /health` – liveness probe.

By default the coordinator listens on `http://0.0.0.0:8024`, so the full
URLs are:

- `http://localhost:8024/nlip`
- `http://localhost:8024/health`

### Agent Servers

Each agent server also exposes `/nlip` and `/health`, but the usual way
to talk to them is via the coordinator and its tools.

Within a single process (via `MountSpec`) they are mounted on `mem://`
URLs so the coordinator can talk to them without opening extra ports:

- Basic: `mem://basic/nlip`
- Translate: `mem://translate/nlip`
- Image: `mem://image/nlip`
- Text: `mem://text/nlip` (used by `text_server`)

The mapping from logical names to URLs is in `app.system.config.MOUNT_URLS`.

---

## NLIP Message Format

The backend is designed around the `NLIP_Message` shape from the
`nlip_sdk.nlip` package. At a high level, an NLIP message carries a list
of sub‑messages, each describing one piece of content with a format and
label.

Each sub‑message is a JSON object with:

- `format` (string) – mime‑like hint for the content. Common values:
  - `text/plain` – plain text user messages
  - `image/base64` – base64‑encoded image payloads
  - `audio` – audio submessages used by the sound agent
- `content` (string or object) – payload (text, base64, or nested dict).
- `label` (string) – semantic tag such as:
  - `translation:<locale>` – a translation into `<locale>`
  - `analysis:<locale>` – analysis/observation text in `<locale>`
  - task tags like `task.translate.*` or `task.text.*`

A typical payload (abridged) looks like:

```json
{
  "messages": [
    { "format": "text/plain", "content": "How are my crops?", "label": "user" },
    { "format": "image/base64", "content": "<raw-base64>", "label": "image" },
    { "format": "text/plain", "content": "How are my crops? (en)", "label": "translation:en" },
    { "format": "text/plain", "content": "Leaf rust detected (en)", "label": "analysis:en" }
  ]
}
```

Agents and tests expect the above conventions when matching and
producing messages. If you change the format or labeling scheme, you’ll
need to update consumers and tests accordingly.

---

## Agents and Flows

### Coordinator NLIP Agent

Defined in `app.agents.coordinator_nlip_agent.CoordinatorNlipAgent`.

- Maintains a registry of connected NLIP servers (`sessions`).
- Tools:
  - `connect_to_server(url)` – create an `NlipAsyncClient` for `<url>/nlip` and store it.
  - `send_to_server(url, message)` – send a text message over NLIP and return the extracted text.
  - `get_all_capabilities()` – ask each connected server “What are your NLIP Capabilities?” and aggregate responses.
- When asked about its own capabilities (“What are your NLIP
  Capabilities?”), it must call `get_all_capabilities()` first, then
  summarize the reported capabilities from each server.

The coordinator server in `app.servers.coordinator_server` wraps this
agent in a `SessionManager` and exposes it over HTTP.

### Translation Agent

Defined in `app.agents.translation.TranslationNlipAgent`.

- Uses a local LLM model (`TRANSLATION_MODEL`) when configured; falls back to `googletrans` for development/fallback scenarios.
- Exposes a single tool:

  ```python
  async def get_translation(text: str, target_locale: str) -> str | None
  ```

- Intended to handle NLIP messages tagged with translation tasks, such as
  `subformat: "task.translate.*"`.
- On success, returns localized text; on error, returns `None` and logs
  the error.

The `translate_server` module wires this agent into an NLIP server that
accepts `NLIP_Message` instances on `/nlip` and returns translated texts.

### Text Agent

Defined in `app.agents.textAgent.LLamaTextAgent`.

- Talks to a local Ollama instance:
  - `OLLAMA_URL` (default `http://localhost:11434`)
  - `OLLAMA_TEXT_MODEL` (default `llama3.2:3b`)
- `handle(NLIP_Message)`:
  - Extracts relevant text from the NLIP message if:
    - `format == AllowedFormats.text`, or
    - `format == AllowedFormats.generic` and `subformat` starts with `task.text`.
  - Sends a prompt to Ollama’s `POST /api/generate` endpoint.
  - Wraps the model’s response as a new text NLIP message with label `llama_response`.

`app.servers.text_server` exposes this as an NLIP HTTP server.

### Image Recognition Agent

Defined in `app.agents.imageRecognition.ImageRecognitionNlipAgent`.

- Uses Ollama’s image endpoint (`/api/generate`) with an image‑capable
  model (default `OLLAMA_IMAGE_MODEL="llava"`).
- Tool:

  ```python
  async def recognize_image(encodedImage: str, prompt: Optional[str] = None) -> Optional[str]
  ```

- Takes base64‑encoded image bytes (`encodedImage`) and an optional
  textual prompt, returns an English description string or `None` on error.

`app.servers.image_server` wraps this agent for `/nlip` access.

### Audio / Sound Agent

Defined in `app.agents.sound.SoundAgent`.

- Converts NLIP audio submessages into localized text via:
  1. Whisper HTTP server for ASR.
  2. Optional translation through a translation helper (see the
     translation agent / tests for expected behavior).
- Main configuration (all optional):
  - `WHISPER_URL` – base URL for the Whisper server (default `http://localhost:9002`).
  - `WHISPER_MODEL` – model name (`large-v3` by default).
  - `WHISPER_TIMEOUT` – seconds to wait for Whisper (default `90`).
- Input: one or more submessages with `format: "audio"` and nested
  content describing base64 or raw bytes.
- Output: a structure containing the final text, chosen language, and
  metadata about per‑sample segments.

The sound agent is currently used directly by tests and is not wired as
its own FastAPI server in `app.servers`, but it follows the same NLIP
message conventions.

---

## Local Whisper Server (openai‑whisper)

The sound agent expects an HTTP server that implements an
OpenAI‑compatible transcription endpoint at `/v1/audio/transcriptions`.

This repository includes a small FastAPI wrapper (`backend/scripts/whisper_server.py`)
and a helper script `start-whisper.sh` that uses the official
`openai-whisper` package.

1. **Install system + Python dependencies**

   - Install ffmpeg (required by Whisper):

     ```bash
     # Ubuntu / Debian
     sudo apt update && sudo apt install ffmpeg

     # Arch Linux
     sudo pacman -S ffmpeg

     # macOS (Homebrew)
     brew install ffmpeg

     # Windows (Chocolatey)
     choco install ffmpeg

     # Windows (Scoop)
     scoop install ffmpeg
     ```

   - Install the Python deps (includes `openai-whisper` and PyTorch):

     ```bash
     pip install -r backend/requirements.txt
     ```

2. **Start the local Whisper server** (run from the `backend/` directory)

   ```bash
   ./start-whisper.sh --model large-v3 --port 9002
   ```

   Flags:

   - `--model`: any model supported by Whisper (`tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3`, or `turbo`).
   - `--device`: optional torch device override (e.g. `--device cuda`).
   - `--port`: HTTP port to bind (default `9002`).

3. **Smoke‑test the endpoint**

   ```bash
   curl -X POST http://localhost:9002/v1/audio/transcriptions \
     -F "model=large-v3" \
     -F "audio=@backend/tests/speed-talking.wav"
   ```

   You should receive JSON containing the transcript, language, and segments.

Leave the server running while you exercise the backend; the sound agent
uses `WHISPER_URL` to reach it.

---

## Running Locally

### 1. Install dependencies

From the repository root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start PostgreSQL

The backend requires a running PostgreSQL 15 instance. The easiest way locally:

```bash
docker run -d --name nlip-db -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=nlip_db \
  postgres:15
```

Then set the connection URL in your environment (or `backend/.env`):

```bash
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/nlip_db
```

The backend creates all tables automatically on first start.

### 3. Start Ollama for text/image agents (optional but recommended)

If you want the text and image agents to use local models via Ollama:

   ```bash
   ollama serve &
   ollama pull llama3.2:3b
   ```

   Set `OLLAMA_URL` if your server listens somewhere other than `http://localhost:11434`.

### 4. Launch the Whisper sidecar

See the "Local Whisper Server" section above for full setup. From the `backend/` directory run:

   ```bash
   ./start-whisper.sh
   ```

   Leave this process running on `http://localhost:9002`.

### 5. Run the multi‑agent backend

The current multi‑agent setup is started via `app.system.main`:

```bash
cd backend
python -m app.system.main
```

This will:

- Start the coordinator server on `http://0.0.0.0:8024` (HTTP `/nlip` and `/health`).
- Register the basic, translate, image, and text agents as in‑process `mem://` endpoints.

### 6. Exercise the NLIP endpoint

Send an NLIP JSON payload to the coordinator:

```bash
curl -X POST http://localhost:8024/nlip \
  -H "Content-Type: application/json" \
  -d '{ "format": "text", "content": "hola", "label": "task.translate.es" }'
```

Or construct full NLIP messages using the `nlip_sdk` Python package and
post their JSON representation.

For image or audio flows, include `image/base64` or `audio` submessages
in the NLIP payload as described above.

### 7. Run the tests

From the repository root (or `backend/`):

```bash
pytest backend/tests
```

- Unit tests stub out external services so they can run without Whisper
  or Ollama.
- Integration tests are marked with `@pytest.mark.integration` and
  expect live external services (Ollama, Whisper). Some translation‑related
  tests target the older Ollama‑based translation helper; keep that in
  mind if you modify the translation agent.

---

## Authentication

The coordinator exposes user-facing auth endpoints on the same port as `/nlip`:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/signup` | Create account. Body: `{ "email": str, "password": str, "name": str }` |
| POST | `/login` | Authenticate. Body: `{ "email": str, "password": str }`. Sets `session_id` cookie. |
| POST | `/logout` | Clear the session cookie. |
| GET | `/me` | Return the current user's profile. |
| PUT | `/me` | Update profile fields: `name`, `location`, `phone_number`, `country_code`, `avatar_uri`. |

Sessions are tracked via an HTTP cookie (`session_id`). Include credentials (`credentials: "include"` in fetch, or `-c cookiejar` in curl) on every request.

Passwords are stored as bcrypt hashes via `passlib[bcrypt]`.

---

## Conversation History

Every NLIP exchange is persisted to PostgreSQL. The coordinator exposes REST endpoints for retrieving and managing that history:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/conversations` | List conversations for the authenticated user. |
| POST | `/conversations` | Create a named conversation. Body: `{ "title": str }` |
| GET | `/conversations/{id}/messages` | Paginated message history for a conversation. |
| POST | `/conversations/{id}/archive` | Archive a conversation. |

To continue an existing conversation, include `conversation_id` in the NLIP message metadata. If omitted, the last active conversation for the session is reused; a new one is created automatically if none exists.

---

## Environment Variables

All configuration is read from environment variables (or a `backend/.env` file). The authoritative list is in `app/system/config.py`.

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | (required) | PostgreSQL async URL, e.g. `postgresql+asyncpg://postgres:postgres@localhost:5432/nlip_db` |
| `OLLAMA_URL` | (required) | LLM endpoint base URL, e.g. `http://localhost:11434` |
| `OLLAMA_MODEL` | (required) | Default LLM model name, e.g. `ai/llama3.2:3B-Q4_0` |
| `OLLAMA_IMAGE_MODEL` | `ai/ministral3` | Vision model for image description |
| `OLLAMA_TIMEOUT` | `60.0` | LLM request timeout in seconds |
| `OLLAMA_TEXT_MODEL` | — | Override model for the text agent specifically |
| `TEXT_TOOL_MODEL` | — | Override model for the text tool |
| `TEXT_TOOL_API_BASE` | — | Override API base URL for the text tool |
| `WHISPER_URL` | `http://localhost:9002` | Whisper-compatible STT endpoint |
| `WHISPER_ENDPOINT` | `/v1/audio/transcriptions` | Whisper API path |
| `WHISPER_MODEL` | `large-v3` | Whisper model name |
| `WHISPER_TIMEOUT` | `90.0` | Whisper request timeout in seconds |
| `TRANSLATION_URL` | — | Override translation service base URL |
| `TRANSLATION_MODEL` | — | Override translation model name |
| `NLIP_COORD_URL` | `http://0.0.0.0:8024` | Coordinator URL (used for self-reference) |
| `NLIP_BASIC_URL` | `http://basic:8025` | Basic agent URL |
| `NLIP_TRANSLATE_URL` | `http://translate:8026` | Translation agent URL |
| `NLIP_TEXT_URL` | `http://text:8027` | Text agent URL |
| `NLIP_IMAGE_URL` | `http://image:8028` | Image agent URL |
| `NLIP_SOUND_URL` | `http://sound:8029` | Sound agent URL |
| `NLIP_LOG_LEVEL` | `INFO` | Log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `CORS_ALLOW_ORIGINS` | — | Comma-separated allowed CORS origins |
| `CORS_ALLOW_ORIGIN_REGEX` | `.*` | CORS origin regex (used when `CORS_ALLOW_ORIGINS` is unset) |

---

## Legacy (Deprecated) Stack

The `app/deprecated/` tree contains the original NLIP supervisor
implementation that exposed a single FastAPI app with:

- `POST /nlip` – session‑aware NLIP endpoint.
- `GET /health` – health check.

Key files there:

- `supervisor.py` – translation + image flow, including English pivot logic.
- `api.py` – `NLIP_Application` / `NLIP_Session` abstractions and FastAPI setup.
- `routes/nlip.py` and `routes/health.py` – route handlers for NLIP and health.

This stack previously used an Ollama‑based `OllamaTranslationAgent` and
`LlavaImageRecognitionAgent`. Parts of that design are now implemented
separately in the new agent modules. The deprecated code is kept for
reference and for tests that still target the older behavior, but the
recommended entrypoint going forward is the coordinator‑based
multi‑agent stack described above.

