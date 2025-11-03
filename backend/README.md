# Backend Endpoint

### /health

Simple health check for the app

### /process

Accepts an NLIP `process` request and routes user messages through an
English pivot so downstream agents can reason in a single language:

1. Detect/receive the user locale.
2. Translate incoming text into English via the local Ollama instance.
3. Run domain logic (currently echoes the English text as a scaffold).
4. Translate the response back into the user's locale before returning it.

This keeps the internal prompts consistent while farmers in Uganda (or any
other locale) interact with the chatbot in their preferred language.

#### Configuration

The translation agent reads the following environment variables (all optional):

- `OLLAMA_URL`: Base URL for the Ollama server (default `http://localhost:11434`).
- `NLIP_TRANSLATION_PIVOT_LOCALE`: Language used for internal reasoning (default `en`).
- `NLIP_TRANSLATION_DEFAULT_LOCALE`: Locale assumed when detection fails (default `en`).

The translation agent targets the `llama3.1` model by default; pass `model="..."` when constructing `OllamaTranslationAgent` if you need to pick a different model.
