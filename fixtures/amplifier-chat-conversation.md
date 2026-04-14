# Synthetic Conversation: Building Amplifier Chat

This is a synthetic conversation history representing a user asking an agent
to build a browser-based chat UI for Amplifier. It is used as test input for
the intent-analyzer agent.

---

**User:** I want a web-based chat interface for Amplifier. Right now I can only
use the CLI terminal, and I want something I can open in a browser. Think a
simple chat window — type a message, send it, see the LLM response.

**Agent:** I can build that. A few questions to scope this:

1. Should this be a standalone app or a plugin to the existing `amplifierd` server?
2. Any preference on frontend framework?
3. Do you need session history (browse old conversations) or just single-session?

**User:** Plugin to amplifierd — I don't want a separate server. Keep the
frontend dead simple, no build step. And yes, I want to see old conversations
and pick up where I left off.

**Agent:** Got it. Here's what I'm thinking:

- **Backend:** FastAPI router that mounts as an amplifierd plugin. Handles
  message streaming, session management, and a health endpoint.
- **Frontend:** Single HTML page using Preact + HTM (no build step, loaded from
  a CDN or vendored). Renders markdown in responses.
- **Sessions:** Stored on disk using amplifierd's existing session storage.
  I'll add a history endpoint that lists past sessions.
- **Port:** amplifierd runs on 8410 by default, so the chat UI will be at
  `http://localhost:8410/chat/`.

Sound right?

**User:** Yes. One more thing — I want to pin important conversations so they
don't get lost in the history. And slash commands would be nice — like `/help`,
`/clear`, `/status`.

**Agent:** Added to the plan:

- **Pinning:** Pin/unpin conversations via an API. Pinned ones float to the top
  of the session list.
- **Slash commands:** `/help` shows available commands, `/clear` resets the
  session, `/status` shows connection info. Processed client-side, sent to a
  dedicated `/chat/command` endpoint.

Let me start building.

**Agent:** I've set up the project structure:

```
amplifier-chat/
├── src/chat_plugin/
│   ├── __init__.py       # Plugin entry, create_router()
│   ├── routes.py         # FastAPI route handlers
│   ├── commands.py       # Slash command processing
│   ├── config.py         # Plugin settings
│   ├── session_history.py # Disk-based session discovery
│   ├── pin_storage.py    # Pin state persistence
│   └── static/
│       ├── index.html    # Single-page Preact UI
│       └── vendor.js     # Preact + HTM runtime
├── pyproject.toml
└── tests/
```

The plugin registers itself via the `amplifierd.plugins` entry point, so
amplifierd auto-discovers it on startup.

**User:** How does the streaming work? I want to see tokens appear as they come
in, not wait for the full response.

**Agent:** The `/chat/` page opens a streaming connection. When you send a
message, the backend forwards it to the Amplifier session which calls the LLM
provider. The provider streams tokens back, and I relay them to the browser via
server-sent events. The frontend appends each chunk to the response bubble in
real time.

**User:** What about the health check?

**Agent:** Two endpoints:

- `GET /chat/health` — returns `{"status": "ok"}`. For monitoring.
- `GET /ready` — returns `{"ready": true}` once the server is fully started.
  Used by DTU readiness probes.

**User:** Good. What about the session history UI? How does that look?

**Agent:** The sidebar shows a list of past sessions, newest first. Each entry
shows the first user message as a preview and a timestamp. Pinned sessions have
a pin icon and always appear at the top. Clicking a session loads its messages
into the main chat area.

The API backing this:

- `GET /chat/api/sessions/history` — lists all sessions with metadata
- `GET /chat/api/sessions/pins` — returns pinned session IDs
- `POST /chat/api/sessions/{id}/pin` — pin a session
- `DELETE /chat/api/sessions/{id}/pin` — unpin a session
- `GET /chat/api/sessions/revisions` — change detection for live refresh

**User:** Looks good. Let me know when it's ready to try.

**Agent:** Done. The plugin is working. Here's what you get:

1. **Chat UI** at `http://localhost:8410/chat/` — type a message, hit Enter or
   click Send, see the response stream in.
2. **Markdown rendering** in responses (code blocks, bold, lists).
3. **Session history** in the left sidebar with timestamps and previews.
4. **Pinning** — click the pin icon on any session.
5. **Slash commands** — type `/help` in the input to see what's available.
6. **Health endpoint** at `/chat/health`.

To run it:

```bash
uv tool install amplifier-chat[standalone]
amplifier-chat --port 8410
```

Then open `http://localhost:8410/chat/` in your browser.

**User:** One question — does this work on mobile? Like if I open it on my
phone?

**Agent:** The layout is responsive — flexbox-based, so it adapts to narrow
screens. The sidebar collapses on mobile widths. It's not extensively
mobile-tested though, so I'd call it "should work" rather than "fully
optimized."

**User:** That's fine for now. And dark mode?

**Agent:** Not implemented yet. The current UI uses a light theme. Dark mode
would be a follow-up — it'd need a toggle button and CSS custom properties for
the color scheme.

**User:** OK, we can add that later. Ship it.