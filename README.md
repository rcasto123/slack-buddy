# Slack Buddy

> Pixel art desktop mascot that surfaces Slack DMs and @mentions as animated on-screen notifications

![Status](https://img.shields.io/badge/status-active%20development-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

Slack Buddy is a single-file Python app that places a small pixel art robot in the bottom-right corner of your screen. It connects to Slack via Socket Mode and watches for direct messages and @mentions. When one arrives, the robot switches to an alert sprite, wiggles, and floats a speech bubble with the message preview — no window-switching required.

The entire UI is built on Tkinter (Python's standard library GUI toolkit), which means there's no Electron, no Chromium, and no native framework beyond Python itself.

---

## Features

- **Two animation states** — an idle sprite (`sprite.svg`) used during normal operation and an alert sprite (`sprite_alert.svg`) shown when a notification is active. SVGs are rendered to RGBA PIL images at startup using CairoSVG so they scale to any DPI without blurriness.
- **Idle bob animation** — continuous gentle vertical bobbing driven by a `tkinter.after` loop (`BOB_INTERVAL = 80 ms`, amplitude 6 px). The mascot alternates direction each time it reaches the amplitude boundary, creating a smooth floating effect.
- **Alert wiggle animation** — on notification arrival the mascot switches to the alert sprite and performs 8 steps of random-offset jitter (`±4 px` horizontal, `±2 px` vertical) over `WIGGLE_DURATION = 600 ms`. Each step is scheduled with `root.after` so it doesn't block the Tkinter event loop.
- **Speech bubble overlay** — a rounded rectangle drawn directly on the Canvas using a polygon with `smooth=True`. The bubble includes a downward-pointing tail triangle and renders word-wrapped text up to 32 characters per line. Platform-specific fonts are used automatically: SF Pro on macOS, Segoe UI on Windows/Linux.
- **Auto-dismiss** — the speech bubble and alert state clear automatically after `ALERT_DURATION = 8000 ms` (8 seconds), returning the mascot to the idle bob.
- **Notification queue** — notifications arriving while an alert is already active are queued in memory and displayed sequentially. The queue is drained via a 500 ms `root.after` polling loop (`_check_queue`), ensuring no messages are dropped during a burst.
- **Frameless, decoration-free window** — `overrideredirect(True)` removes the title bar. The window floats above all other windows via `-topmost True` with no taskbar entry.
- **Transparent background** — uses `-transparentcolor black` on Windows and a `systemTransparent` background fallback on macOS so the black canvas background disappears, leaving only the sprite and bubble visible.
- **Always on top** — the Tk window is created with `-topmost True`, so the buddy remains visible over full-screen apps and always-on-top windows on all three platforms.
- **Draggable** — left-click anywhere on the canvas to start dragging; the window repositions in real time as the cursor moves. The drag origin is captured on `ButtonPress-1` and the delta applied on `B1-Motion` with no movement threshold.
- **Right-click to quit** — both `ButtonPress-2` (middle) and `ButtonPress-3` (right) call `quit()`, which calls `root.quit()` then `root.destroy()` to exit cleanly.
- **Slack Socket Mode listener** — runs in a background `threading.Thread` (daemonized) so it never blocks the Tkinter main loop. Handles three event types: `message` with `channel_type: im` (direct messages), `message` containing the bot's user ID (channel @mentions), and `app_mention` events. Responds to each Socket Mode request with an immediate `SocketModeResponse` acknowledgement before processing.
- **Bot echo suppression** — events from the bot's own user ID or carrying a `bot_id` field are silently ignored to prevent notification loops.
- **Display name resolution** — sender user IDs are resolved to real names via `users.info` and cached in a dict for the session lifetime, avoiding repeated API calls.
- **Channel name resolution** — for channel @mention notifications, the channel name is resolved via `conversations.info` and displayed as `#channel-name`.
- **Message truncation** — previews are capped at 80 characters with a `…` suffix. The bot's own user ID is replaced with `@you` in mention text before display.
- **Demo mode** — run with `--demo` to skip all Slack configuration and cycle through five realistic fake notifications at random intervals between 6 and 12 seconds. Useful for testing sprite rendering, animations, and bubble layout without a Slack workspace.
- **Config template auto-generation** — if `config.json` is missing at launch, the app writes a filled-in template and exits with a clear error message, so users always know exactly what file to edit.

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.10+ |
| GUI framework | Tkinter | stdlib |
| SVG rendering | CairoSVG | 2.7+ |
| Image handling | Pillow | 10.0+ |
| Slack connectivity | slack-sdk (Socket Mode) | 3.27+ |
| WebSocket transport | websocket-client | 1.7+ |

**Platform notes:**
- **macOS** — Cairo must be installed separately: `brew install cairo`. The Python `cairosvg` wheel links against it dynamically.
- **Windows** — Cairo is bundled inside the `cairosvg` wheel on most Windows configurations. If you see a DLL error, install the [GTK+ runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer).
- **Linux** — install Cairo via your package manager: `sudo apt install libcairo2` (Debian/Ubuntu) or `sudo dnf install cairo` (Fedora).

---

## How It Works

```
config.json
    │
    ▼
load_config()  ─── missing/template → exit with instructions
    │
    ▼
SlackBuddy.__init__()
    ├── Tk window (frameless, transparent, always-on-top)
    ├── Canvas with sprite image item
    ├── _animate_bob()  ─── root.after(80ms) loop — vertical bob
    └── _check_queue()  ─── root.after(500ms) loop — drain notification queue

start_slack_listener()  ─── daemon thread
    ├── WebClient(bot_token)  ─── auth_test() → bot_user_id
    └── SocketModeClient(app_token)
            │
            ▼  on each event
        handle_event()
            ├── SocketModeResponse(ack)  ── immediate acknowledgement
            ├── filter bot messages
            ├── DM?       → buddy.notify("💬 DM from {name}:\"{preview}\"")
            ├── @mention? → buddy.notify("📢 #{channel} — {name}:\"{preview}\"")
            └── app_mention? → buddy.notify(...)

buddy.notify(message)
    └── notification_queue.append(message)

_check_queue() (every 500ms)
    └── if queue and not alerting → _trigger_alert(message)
            ├── _set_sprite(alert)
            ├── _show_bubble(message)
            ├── _wiggle(steps=8)
            └── root.after(8000, _end_alert)
                    └── _set_sprite(idle) + _hide_bubble()
```

The Slack listener runs in a background daemon thread. It calls `buddy.notify()` which is thread-safe because it only appends to a Python list; the Tkinter loop drains that list on the main thread via `root.after`, keeping all widget operations on the GUI thread.

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- **pip**
- A Slack workspace where you can create and install apps
- **Cairo** (for SVG rendering — see platform notes above)

### macOS — install Cairo first

```bash
brew install cairo
```

### Install Python dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install "slack-sdk>=3.27.0" "websocket-client>=1.7.0" "cairosvg>=2.7.0" "Pillow>=10.0.0"
```

### Run in demo mode (no Slack required)

```bash
python3 slack_buddy.py --demo
```

This cycles through five pre-written fake notifications at random 6–12 second intervals so you can verify the sprite, animations, and bubble layout before connecting to Slack.

### Run with a live Slack connection

```bash
python3 slack_buddy.py
```

On first run with no `config.json`, the app writes a template file and exits:

```
config.json has been created at: /path/to/slack-buddy/config.json
```

Edit the file with your tokens, then run again.

---

## Configuration

Slack Buddy reads `config.json` from the project root. Both fields are required.

```json
{
  "SLACK_BOT_TOKEN": "xoxb-your-bot-token-here",
  "SLACK_APP_TOKEN": "xapp-your-app-token-here"
}
```

| Field | Type | Description |
|---|---|---|
| `SLACK_BOT_TOKEN` | string | Bot User OAuth Token from your Slack app's OAuth & Permissions page. Starts with `xoxb-`. |
| `SLACK_APP_TOKEN` | string | App-Level Token with the `connections:write` scope, generated from your app's Basic Information / Socket Mode page. Starts with `xapp-`. |

**Do not commit `config.json`** — it contains live Slack tokens. It is already listed in `.gitignore`.

---

## Slack App Setup

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App → From scratch**. Name it (e.g., "Slack Buddy") and select your workspace.

2. Under **Settings → Socket Mode**, toggle Socket Mode **on**. When prompted to generate an App-Level Token, name it anything and add the scope `connections:write`. Copy the token — it starts with `xapp-1-`. This is your `SLACK_APP_TOKEN`.

3. Under **Features → OAuth & Permissions → Bot Token Scopes**, add:

   | Scope | Required for |
   |---|---|
   | `im:history` | Reading direct messages |
   | `im:read` | Listing DM channels |
   | `channels:history` | Reading channel messages (for @mention text) |
   | `groups:history` | Reading private channel messages |
   | `users:read` | Resolving sender display names via `users.info` |
   | `channels:read` | Resolving channel names via `conversations.info` |
   | `groups:read` | Resolving private channel names |

4. Under **Features → Event Subscriptions**, enable events and subscribe to these **Bot Events**:

   | Event | Trigger |
   |---|---|
   | `message.im` | Direct messages to the bot |
   | `app_mention` | @mentions of the bot in any channel |
   | `message.channels` | Channel messages (needed to catch @mentions via `message` type) |
   | `message.groups` | Private channel messages |

5. Click **Install to Workspace** (or **Reinstall** if already installed) and authorize. Copy the **Bot User OAuth Token** from the OAuth & Permissions page — it starts with `xoxb-`. This is your `SLACK_BOT_TOKEN`.

6. Paste both tokens into `config.json` and run `python3 slack_buddy.py`.

7. To receive @mention notifications in a channel, invite the bot: `/invite @YourBotName`.

---

## Controls

| Action | How |
|---|---|
| Move the buddy | Left-click and drag |
| Quit | Right-click (or middle-click) the buddy |

---

## Demo Mode

Run with the `--demo` flag to test the app without any Slack credentials:

```bash
python3 slack_buddy.py --demo
```

Demo mode skips `load_config()` entirely and starts a background thread that calls `buddy.notify()` with one of five pre-written messages every 6–12 seconds (randomized). It exercises the full animation and speech bubble pipeline:

```
"💬 DM from Sarah:\n\"Hey, got a minute?\""
"📢 #engineering — Alex:\n\"@you Can you review this PR?\""
"💬 DM from Jordan:\n\"The deploy looks good 🚀\""
"📢 #general — Pat:\n\"@you lunch today?\""
"💬 DM from Morgan:\n\"Quick question about the API...\""
```

Right-click the buddy to quit as usual.

---

## Project Structure

```
slack-buddy/
├── slack_buddy.py       # Entire application — ~350 lines
│                        #   SlackBuddy class (Tkinter window + animations)
│                        #   start_slack_listener() (background thread)
│                        #   run_demo() (fake notification loop)
│                        #   main() (entry point)
├── config.json          # Slack tokens — DO NOT COMMIT
├── requirements.txt     # Python dependencies
└── assets/
    ├── sprite.svg       # Idle pixel art robot sprite
    └── sprite_alert.svg # Alert pixel art robot sprite (eyes wide, antenna lit)
```

---

## License

MIT
