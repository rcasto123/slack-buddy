# Slack Buddy

> Pixel art desktop mascot that surfaces Slack DMs and @mentions as on-screen notifications

![Status](https://img.shields.io/badge/status-active%20development-blue)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)

Slack Buddy is a lightweight desktop companion built with Python and Tkinter. A small 3D pixel art robot lives in the corner of your screen and animates whenever you receive a direct message or @mention in Slack, surfacing a speech bubble preview without requiring you to switch windows.

## Features

- **Animated sprite** — idle bob, blink, and wiggle animations rendered via SVG assets
- **Speech bubble notifications** — message previews pop up on DMs and @mentions via Slack Socket Mode
- **Always on top** — floats over all windows so you never miss a ping
- **Draggable** — click and drag to reposition anywhere on screen
- **Demo mode** — test animations and bubbles without a Slack connection
- **Minimal footprint** — single Python file, no Electron, no native frameworks

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| GUI | Tkinter (stdlib) |
| SVG rendering | CairoSVG |
| Image handling | Pillow |
| Slack connectivity | slack-sdk (Socket Mode) |

## Getting Started

```bash
# Install dependencies
pip3 install -r requirements.txt
```

On macOS, Cairo must be present for SVG rendering:

```bash
brew install cairo
```

```bash
# Try demo mode — no Slack credentials needed
python3 slack_buddy.py --demo

# Run with a live Slack connection
python3 slack_buddy.py
```

## Configuration

Slack Buddy reads credentials from `config.json` in the project root. A template is created automatically on first run if the file is missing.

```json
{
  "SLACK_BOT_TOKEN": "xoxb-...",
  "SLACK_APP_TOKEN": "xapp-..."
}
```

Do not commit `config.json` — it contains live Slack tokens.

### Creating a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app from scratch.
2. Under **Socket Mode**, enable it and generate an App Token (`xapp-...`).
3. Under **OAuth & Permissions**, add bot scopes: `channels:history`, `groups:history`, `im:history`, `mpim:history`, `users:read`, `channels:read`, `groups:read`.
4. Under **Event Subscriptions**, subscribe to bot events: `message.im`, `message.channels`, `message.groups`, `app_mention`.
5. Install the app to your workspace and copy the Bot Token (`xoxb-...`).
6. Invite the bot to any channel you want it to monitor: `/invite @Slack Buddy`.

## Controls

| Action | How |
|---|---|
| Move the buddy | Click and drag |
| Quit | Right-click the buddy |

## Project Structure

```
slack-buddy/
├── slack_buddy.py       # Main application
├── config.json          # Slack tokens (do not commit)
├── requirements.txt     # Python dependencies
└── assets/
    ├── sprite.svg       # Idle sprite
    └── sprite_alert.svg # Alert sprite
```

## License

MIT
