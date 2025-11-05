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