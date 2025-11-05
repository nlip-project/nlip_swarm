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

#### Configuration

The translation agent reads the following environment variables (all optional):

- `OLLAMA_URL`: Base URL for the Ollama server (default `http://localhost:11434`).
- `OLLAMA_MODEL`: Actual model the Agents are running on (default `llama3.2:3b`) 
- `NLIP_TRANSLATION_PIVOT_LOCALE`: Language used for internal reasoning (default `en`).
- `NLIP_TRANSLATION_DEFAULT_LOCALE`: Locale assumed when detection fails (default `en`).

The translation agent targets the `llama3.1` model by default; pass `model="..."` when constructing `OllamaTranslationAgent` if you need to pick a different model.
