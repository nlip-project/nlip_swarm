# Backend Endpoint

### /capabilities

GET endpoint to check what capabilities the manager has.

### /nlip

POST endpoint that acts as the connection to a frontend machine
accepting NLIP message requests as the body and returning NLIP
message responses from the swarm manager.

## Translation Agent

Accepts an NLIP `process` request and routes user messages through an
English pivot so downstream agents can reason in a single language:

1. Detect/receive the user locale.
2. Translate incoming text into English via the local Ollama instance.
3. Run domain logic (currently echoes the English text as a scaffold).
4. Translate the response back into the user's locale before returning it.

This keeps the internal prompts consistent while farmers in Uganda (or any
other locale) interact with the chatbot in their preferred language.

## Request Example:

{
"messagetype": "request",
"format": "generic",
"subformat": "task.translate.fr",
"label": "translate_req",
"content": "hello world"
}

### Response:

{
"messagetype": "response",
"format": "generic",
"subformat": "nlip.bundle",
"content": "ok",
"label": "translate_req",
"submessages": [
{
"format": "text",
"subformat": "english",
"content": "bonjour le monde",
"label": "translate_req"
}
]
}

### Request with Multiple SubMessages

{
"messagetype": "request",
"format": "generic",
"subformat": "nlip.bundle",
"content": "batch",
"submessages": [
{
"format": "generic",
"subformat": "task.translate.*",
"label": "line1",
"content": "tests de détection automatique"
},
{
"format": "generic",
"subformat": "task.translate.es",
"label": "line2",
"content": "Testing english to specific language"
}
]
}

### Bundled Response

#### Configuration

The translation agent reads the following environment variables (all optional):

- `OLLAMA_URL`: Base URL for the Ollama server (default `http://localhost:11434`).
- `OLLAMA_MODEL`: Actual model the Agents are running on (default `llama3.2:3b`)
- `NLIP_TRANSLATION_PIVOT_LOCALE`: Language used for internal reasoning (default `en`).
- `NLIP_TRANSLATION_DEFAULT_LOCALE`: Locale assumed when detection fails (default `en`).

The translation agent targets the `llama3.1` model by default; pass `model="..."` when constructing `OllamaTranslationAgent` if you need to pick a different model.

### Image flow

Images can be included in the same NLIP `process` payload as other messages. Each image message should be a message object with:

- format: `image/base64`
- content: the raw base64 image bytes (no data URI prefix)
- label: optional client label (server will add analysis/translation labels)

When the backend receives an image message it:

1. Preserves the session correlator token with the message.
2. Forwards the image base64 to the configured image recognition agent (LlavaImageRecognitionAgent) which POSTs to the Ollama image endpoint.
3. Receives an English analysis result (pivot locale) from the agent and appends it as an internal message labeled `analysis:<pivot_locale>` (pivot locale defaults to `en`).
4. Translates the analysis text back into the user's locale and returns it as a `analysis:<user_locale>` message.
5. Returns the full message list to the client, preserving correlator tokens on responses.

Note: the image agent expects plain base64 image data and uses the same HTTP/timeouts pattern as other agents (httpx, 60s default).

### Intended message format

The NLIP protocol uses a simple messages list. Each message is a JSON object with these fields:

- `format` (string): mime-like hint for the content. Common values:
  - `text/plain` — plain text user messages
  - `image/base64` — base64-encoded image payloads
- `content` (string): message payload (text or base64)
- `label` (string): semantic tag such as:
  - `translation:<locale>` — a translation into <locale>
  - `analysis:<locale>` — an analyzed/observed result in <locale>

Example payload shape (abridged):
{
"messages": [
{ "format": "text/plain", "content": "How are my crops?", "label": "user" },
{ "format": "image/base64", "content": "<raw-base64>", "label": "image" },
{ "format": "text/plain", "content": "How are my crops? (en)", "label": "translation:en" },
{ "format": "text/plain", "content": "Leaf rust detected (en)", "label": "analysis:en" },
{ "format": "text/plain", "content": "Kurundi imewe (lg)", "label": "analysis:lg" }
]
}

Service guarantees:

- The backend will attach translation/analysis labels and keep the pivot (default `en`) for internal reasoning.
- Session correlator tokens are preserved on forwarded and returned messages so clients can correlate responses.
- Tests and agents expect the `messages` list and the labeling conventions above; changing these requires updating tests and consumers.

## Audio / Sound Agent

Incoming NLIP audio submessages are routed to Whisper for ASR and then optionally
re-translated through Ollama so the final response matches the user's locale.

Environment variables for the sound agent (all optional):

- `WHISPER_URL`: Base URL for the Whisper HTTP server (default `http://localhost:9002`).
- `WHISPER_MODEL`: Model name sent to Whisper (default `large-v3`).
- `WHISPER_TIMEOUT`: Seconds to wait for Whisper before failing (default `90`).

### Local Whisper Server (openai-whisper)

Instead of relying on the `whisper.cpp` Docker image, we now reuse the official
openai-whisper package directly. The helper script `start-whisper.sh` wraps a
small FastAPI server (`backend/scripts/whisper_server.py`) that mimics
OpenAI's `POST /v1/audio/transcriptions` endpoint.

1. **Install the Python package and system dependencies**

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
     (If you prefer managing dependencies manually, run `pip install -U openai-whisper`
     as described in the official Whisper README.)

2. **Start the local Whisper server** (run from the `backend/` directory)

   ```bash
   ./start-whisper.sh --model large-v3 --port 9002
   ```

   Flags:

   - `--model`: any model supported by Whisper (`tiny`, `base`, `small`, `medium`,
     `large`, `large-v2`, `large-v3`, or `turbo`). Prefixes like `whisper-large-v3`
     are also accepted for compatibility with existing configs.
   - `--device`: optional torch device override (e.g. `--device cuda`).
   - `--port`: HTTP port to bind (default `9002`).

3. **Smoke-test the endpoint**
   ```bash
   curl -X POST http://localhost:9002/v1/audio/transcriptions \
     -F "model=large-v3" \
     -F "audio=@backend/tests/speed-talking.wav"
   ```
   You should receive JSON containing the transcript, language, and segments.

Leave the server running in the background while you exercise the backend—the
sound agent simply issues HTTP requests against `WHISPER_URL`.

### Running Locally

1. **Install dependencies**

   ```bash
   cd backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start Ollama for translation**

   ```bash
   ollama serve &
   ollama pull llama3.1
   ```

   Set `OLLAMA_URL` if your server listens somewhere other than `http://localhost:11434`.

3. **Launch the Whisper sidecar** (see the commands in the Audio/Sound Agent section above). From the `backend/` directory run:

   ```bash
   ./start-whisper.sh
   ```

   Leave this process running on `http://localhost:9002`.

4. **Run the FastAPI app**

   ```bash
   uvicorn backend.app.supervisor:app --reload --port 8000
   ```

   Relevant environment variables:

   - `OLLAMA_URL`, `NLIP_TRANSLATION_PIVOT_LOCALE`, `NLIP_TRANSLATION_DEFAULT_LOCALE`
   - `WHISPER_URL`, `WHISPER_MODEL`, `WHISPER_TIMEOUT`

5. **Exercise the NLIP endpoint**

   ```bash
   curl -X POST http://localhost:8000/nlip/ \
     -H "Content-Type: application/json" \
     -d '{ "format": "text", "content": "hola", "target_language": "en" }'
   ```

   For audio payloads, base64-encode the media into an `audio` submessage and post the same way.

6. **Run the test suite**
   ```bash
   pytest backend/tests
   ```
   The unit tests stub Whisper/Ollama, so they pass without the external services, but integration tests (marked `@pytest.mark.integration`) expect live servers.

### Running via Docker Compose

1. **Start the stack**

   ```bash
   docker compose up --build
   ```

2. **Launch Whisper in a separate terminal on the host**

   ```bash
   bash start-whisper.sh
   ```

   Leave that terminal open; the container keeps running until you `Ctrl+C`.

3. **Point the backend container at the host-side Whisper server**

   - Set `WHISPER_URL=http://host.docker.internal:9002` in your Compose env.
   - On Linux, add `extra_hosts: ["host.docker.internal:host-gateway"]` so the container can resolve the host gateway.

4. **Test sound agent with given WAV of someone talking**
   ```bash
   curl -X POST http://localhost:9002/v1/audio/transcriptions \
     -F "model=large-v3" \
     -F "audio=@backend/tests/speed-talking.wav"
   ```
   When you see a transcript, post the same file inside an NLIP request to the compose-hosted backend to exercise the full ASR → translation path.
