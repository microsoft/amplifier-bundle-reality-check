# Amplifier Chat – Requirements Spec

Build me a browser-based chat interface for Amplifier. I want to be able to
have conversations with an LLM through a web UI instead of the terminal.

## Chat interface

- A single-page web app at `http://localhost:8410/chat/`.
- The main area is a message thread: user messages on one side, LLM responses
  on the other, in chronological order.
- At the bottom, a text input and a send button. Pressing Enter or clicking
  Send submits the message.
- LLM responses should stream token-by-token as they arrive — I want to see
  text appear in real time, not wait for the full response.
- Messages should render markdown: code blocks with syntax highlighting,
  bold, italic, lists, links, inline code.
- If the LLM is still generating a response, I should see some indication
  that it's thinking/streaming (a spinner, animated dots, whatever).

## Session history

- A sidebar (or panel) showing past conversations.
- Each entry shows a preview of the first message and a timestamp.
- Clicking a session loads its full message history into the main chat area.
- Newest sessions appear at the top.
- I can start a new conversation without losing old ones.

## Pinning

- I can pin a conversation so it sticks to the top of the session list.
- Pinned sessions have a visible indicator (icon, highlight, something).
- I can unpin a session to return it to its normal position.
- Pins persist across page refreshes / server restarts.

## Slash commands

- Typing `/` in the chat input should trigger command handling, not send a
  regular message.
- At minimum:
  - `/help` — shows available commands
  - `/clear` — clears or resets the current session
  - `/status` — shows connection info or server status

## Health and readiness

- `GET /chat/health` returns a JSON response indicating the service is up.
- The server should have a readiness signal so orchestration tools know when
  it's fully started and accepting requests.

## Technical constraints

- Backend: Python, FastAPI. It should run as a plugin on top of `amplifierd`
  — not a standalone server.
- Frontend: no build step. Inline JS is fine. Use something lightweight like
  Preact so it loads fast and the source is readable.
- Sessions are stored on disk (amplifierd's session directory), not in a
  database.
- The plugin is discovered automatically via entry points — no manual
  registration.

## Error handling

- If the LLM backend is unreachable or returns an error, the UI should show
  an error message in the chat thread — not silently fail or show a blank
  screen.
- Submitting an empty message should be a no-op or show a gentle validation
  hint, not crash.

## Nice to have

- Dark mode / light mode toggle.
- Voice input support (not critical for v1).
- Mobile-friendly layout (responsive, usable on a phone screen).
- Keyboard shortcuts (e.g., Escape to clear input, Up arrow to edit last
  message).

The bottom line: I want to open `http://localhost:8410/chat/`, type a
question, and get a streaming response — with session history and pinning
so I don't lose important conversations.
