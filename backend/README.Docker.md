### Service Architecture

`compose.yaml` runs the following services:

| Service | Port | Role |
|---------|------|------|
| coordinator | 8024 (published) | Central NLIP router — the only service the frontend talks to |
| basic | 8025 (internal) | General LLM chat agent |
| translate | 8026 (internal) | Text translation agent |
| text | 8027 (internal) | Text generation agent |
| image | 8028 (internal) | Image description agent |
| sound | 8029 (internal) | Speech-to-text agent (via Whisper) |
| whisper | 9002 (internal) | Whisper ASR HTTP server |
| db | 5432 (published) | PostgreSQL 15 database |
| frontend | 8081, 19000–19002 (published) | Expo dev server |

Agent services (basic, translate, text, image, sound) are built from `Dockerfile.agent-service` using the `SERVICE_ROLE=<role>` build argument. Each role strips unused agent and server code from the image, keeping individual images lean.

The coordinator is the only externally accessible NLIP endpoint. All other agents communicate over the internal Docker network.

### Building and running your application

When you're ready, start your application by running:
`docker compose up --build`.

The coordinator API will be available at http://localhost:8024.

### Deploying your application to the cloud

First, build your image, e.g.: `docker build -t myapp .`.
If your cloud uses a different CPU architecture than your development
machine (e.g., you are on a Mac M1 and your cloud provider is amd64),
you'll want to build the image for that platform, e.g.:
`docker build --platform=linux/amd64 -t myapp .`.

Then, push it to your registry, e.g. `docker push myregistry.com/myapp`.

Consult Docker's [getting started](https://docs.docker.com/go/get-started-sharing/)
docs for more detail on building and pushing.

### References
* [Docker's Python guide](https://docs.docker.com/language/python/)