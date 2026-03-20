# 🤖 Slack Buddy

A tiny 3D pixel art desktop mascot that lives on your screen and notifies you whenever you get a Slack DM or @mention.

![Slack Buddy](assets/sprite.svg)

## Features

- **Cute 3D pixel art robot** that bobs and blinks on your desktop
- **Speech bubbles** pop up with message previews when you get a DM or mention
- **Wiggle animation** to grab your attention
- **Drag to reposition** anywhere on your screen
- **Always on top** — sits over all your windows
- **Demo mode** to try it without connecting to Slack

---

## Quick Start

### 1. Install Python

Download and install Python 3.10+ from [python.org](https://www.python.org/downloads/).

### 2. Install dependencies

Open Terminal and navigate to this project folder, then run:

\`\`\`bash
pip3 install -r requirements.txt
\`\`\`

> **Note:** On macOS you may also need to install Cairo for SVG rendering:
> \`\`\`bash
> brew install cairo
> \`\`\`
> If you don't have Homebrew, install it first from [brew.sh](https://brew.sh).

### 3. Try Demo Mode (no Slack needed)

Test the buddy without any Slack setup:

\`\`\`bash
python3 slack_buddy.py --demo
\`\`\`

You should see the little robot appear in the bottom-right corner of your screen with demo notifications popping up.

### 4. Set Up Slack

To receive real Slack notifications, you need to create a Slack App:

#### a) Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **"Create New App"** → **"From scratch"**
3. Name it \`Slack Buddy\` and pick your workspace
4. Click **Create App**

#### b) Enable Socket Mode

1. In the left sidebar, go to **Socket Mode**
2. Toggle it **ON**
3. Give the token a name like \`slack-buddy-socket\` and click **Generate**
4. Copy the \`xapp-...\` token — this is your **App Token**

#### c) Set Bot Permissions

1. Go to **OAuth & Permissions** in the left sidebar
2. Under **Bot Token Scopes**, add these:
   - \`channels:history\` — read messages in public channels
   - \`groups:history\` — read messages in private channels
   - \`im:history\` — read direct messages
   - \`mpim:history\` — read group DMs
   - \`users:read\` — look up usernames
   - \`channels:read\` — look up channel names
   - \`groups:read\` — look up private channel names

#### d) Subscribe to Events

1. Go to **Event Subscriptions** in the left sidebar
2. Toggle it **ON**
3. Under **Subscribe to bot events**, add:
   - \`message.im\` — DMs to the bot
   - \`message.channels\` — messages in public channels
   - \`message.groups\` — messages in private channels
   - \`app_mention\` — when someone @mentions the bot
4. Click **Save Changes**

#### e) Install the App

1. Go to **Install App** in the left sidebar
2. Click **Install to Workspace** and authorize
3. Copy the \`xoxb-...\` token — this is your **Bot Token**

#### f) Update config.json

Open \`config.json\` and paste in your tokens:

\`\`\`json
{
  "SLACK_BOT_TOKEN": "xoxb-your-actual-token",
  "SLACK_APP_TOKEN": "xapp-your-actual-token"
}
\`\`\`

#### g) Invite the bot to channels

In Slack, invite your bot to any channel where you want it to detect @mentions:

\`\`\`
/invite @Slack Buddy
\`\`\`

### 5. Run Slack Buddy

\`\`\`bash
python3 slack_buddy.py
\`\`\`

The robot will appear on your screen. When someone DMs you or @mentions you in Slack, it will wiggle and show you the message!

---

## Controls

| Action | How |
|--------|-----|
| **Move the buddy** | Click and drag |
| **Quit** | Right-click the buddy |

---

## Troubleshooting

**"No module named tkinter"**
On some systems, tkinter needs to be installed separately:
\`\`\`bash
# macOS (with Homebrew Python)
brew install python-tk
\`\`\`

**Buddy doesn't appear / is invisible**
Some macOS versions handle transparency differently. The app tries multiple transparency methods automatically.

**No notifications showing**
- Make sure your bot is invited to the channels you want to monitor
- Check that Socket Mode is enabled in your Slack app settings
- Verify your tokens in \`config.json\` are correct

---

## Project Structure

\`\`\`
slack-buddy/
├── slack_buddy.py       # Main application
├── config.json          # Your Slack tokens (don't commit this!)
├── requirements.txt     # Python dependencies
├── assets/
│   ├── sprite.svg       # Idle sprite (3D pixel art robot)
│   └── sprite_alert.svg # Alert sprite (excited, arm raised)
└── README.md            # You are here
\`\`\`

---

## License

MIT — do whatever you want with it! 🎉
