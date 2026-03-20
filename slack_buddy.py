#!/usr/bin/env python3
"""
Slack Buddy — A tiny 3D pixel art desktop mascot that notifies you
of Slack DMs and @mentions.

Usage:
    python3 slack_buddy.py

Requires:
    pip install slack-sdk websocket-client cairosvg Pillow
"""

import os
import sys
import json
import time
import threading
import textwrap
from pathlib import Path

# GUI
import tkinter as tk
from tkinter import font as tkfont

# Image handling
from PIL import Image, ImageTk
import cairosvg
import io

# Slack
from slack_sdk.web import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ASSETS_DIR = Path(__file__).parent / "assets"
CONFIG_FILE = Path(__file__).parent / "config.json"

# Sprite size on screen
SPRITE_WIDTH = 120
SPRITE_HEIGHT = 140

# Where the buddy sits (bottom-right corner)
MARGIN_RIGHT = 40
MARGIN_BOTTOM = 60

# Animation timing (ms)
BOB_INTERVAL = 80
BOB_AMPLITUDE = 6
BLINK_INTERVAL = 3500
BLINK_DURATION = 150
ALERT_DURATION = 8000  # how long the speech bubble stays
WIGGLE_DURATION = 600


# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------

def load_config():
    """Load Slack tokens from config.json."""
    if not CONFIG_FILE.exists():
        print("\n⚠️  No config.json found!")
        print("   Please create config.json with your Slack tokens.")
        print("   See README.md for setup instructions.\n")
        # Create a template
        template = {
            "SLACK_BOT_TOKEN": "xoxb-your-bot-token-here",
            "SLACK_APP_TOKEN": "xapp-your-app-token-here"
        }
        CONFIG_FILE.write_text(json.dumps(template, indent=2))
        print(f"   A template has been created at: {CONFIG_FILE}")
        sys.exit(1)

    config = json.loads(CONFIG_FILE.read_text())

    if "your-" in config.get("SLACK_BOT_TOKEN", "your-"):
        print("\n⚠️  Please update config.json with your real Slack tokens.")
        print("   See README.md for setup instructions.\n")
        sys.exit(1)

    return config


# ---------------------------------------------------------------------------
# SVG → PIL Image helper
# ---------------------------------------------------------------------------

def load_svg(filename, width=SPRITE_WIDTH, height=SPRITE_HEIGHT):
    """Load an SVG file and return a PIL Image with transparency."""
    svg_path = ASSETS_DIR / filename
    png_data = cairosvg.svg2png(
        url=str(svg_path),
        output_width=width,
        output_height=height,
    )
    return Image.open(io.BytesIO(png_data)).convert("RGBA")


# ---------------------------------------------------------------------------
# Desktop Buddy Window
# ---------------------------------------------------------------------------

class SlackBuddy:
    def __init__(self):
        # --- Root window (transparent, always on top, no decorations) ---
        self.root = tk.Tk()
        self.root.title("Slack Buddy")
        self.root.overrideredirect(True)          # no title bar
        self.root.attributes("-topmost", True)     # always on top
        self.root.attributes("-alpha", 1.0)
        self.root.config(bg="black")

        # macOS transparency
        try:
            self.root.attributes("-transparentcolor", "black")
        except tk.TclError:
            # Fallback for macOS — use wm attributes
            try:
                self.root.wm_attributes("-transparent", True)
                self.root.config(bg="systemTransparent")
            except tk.TclError:
                pass

        # Screen dimensions
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Window size (big enough for sprite + bubble)
        self.win_w = 400
        self.win_h = 300
        x = screen_w - self.win_w - MARGIN_RIGHT
        y = screen_h - self.win_h - MARGIN_BOTTOM
        self.root.geometry(f"{self.win_w}x{self.win_h}+{x}+{y}")

        # --- Canvas ---
        self.canvas = tk.Canvas(
            self.root,
            width=self.win_w,
            height=self.win_h,
            bg="black",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        # macOS transparent canvas
        try:
            self.canvas.config(bg="systemTransparent")
        except tk.TclError:
            pass

        # --- Load sprites ---
        self.sprite_idle = load_svg("sprite.svg")
        self.sprite_alert = load_svg("sprite_alert.svg")
        self.current_sprite = self.sprite_idle

        self.tk_image = ImageTk.PhotoImage(self.current_sprite)

        # Sprite position (center-bottom of canvas)
        self.sprite_x = self.win_w // 2
        self.sprite_y = self.win_h - SPRITE_HEIGHT // 2 - 10
        self.sprite_base_y = self.sprite_y

        self.sprite_id = self.canvas.create_image(
            self.sprite_x, self.sprite_y,
            image=self.tk_image,
            anchor=tk.CENTER,
        )

        # --- Speech bubble (hidden initially) ---
        self.bubble_visible = False
        self.bubble_bg = None
        self.bubble_text_id = None
        self.bubble_tail = None

        # --- Animation state ---
        self.bob_offset = 0
        self.bob_direction = 1
        self.is_alerting = False
        self.wiggle_step = 0

        # --- Dragging support ---
        self._drag_data = {"x": 0, "y": 0}
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)

        # --- Right-click to quit ---
        self.canvas.bind("<ButtonPress-2>", lambda e: self.quit())
        self.canvas.bind("<ButtonPress-3>", lambda e: self.quit())

        # --- Start animations ---
        self._animate_bob()

        # --- Notification queue ---
        self.notification_queue = []
        self._check_queue()

    # ----- Dragging -----
    def _on_drag_start(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag_motion(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    # ----- Animations -----
    def _animate_bob(self):
        """Gentle bobbing idle animation."""
        if not self.is_alerting:
            self.bob_offset += self.bob_direction
            if abs(self.bob_offset) >= BOB_AMPLITUDE:
                self.bob_direction *= -1

            new_y = self.sprite_base_y + self.bob_offset
            self.canvas.coords(self.sprite_id, self.sprite_x, new_y)

        self.root.after(BOB_INTERVAL, self._animate_bob)

    def _set_sprite(self, image):
        """Swap the displayed sprite image."""
        self.current_sprite = image
        self.tk_image = ImageTk.PhotoImage(image)
        self.canvas.itemconfig(self.sprite_id, image=self.tk_image)

    # ----- Speech Bubble -----
    def _show_bubble(self, text):
        """Display a speech bubble above the character."""
        self._hide_bubble()
        self.bubble_visible = True

        # Wrap text
        wrapped = textwrap.fill(text, width=32)
        lines = wrapped.split("\n")

        # Bubble dimensions
        char_w = 7
        line_h = 16
        pad_x = 14
        pad_y = 10
        text_w = max(len(line) for line in lines) * char_w
        text_h = len(lines) * line_h
        bw = text_w + pad_x * 2
        bh = text_h + pad_y * 2

        # Position above sprite
        bx = self.sprite_x - bw // 2
        by = self.sprite_base_y - SPRITE_HEIGHT // 2 - bh - 18

        # Rounded rectangle background
        r = 12
        self.bubble_bg = self._rounded_rect(
            bx, by, bx + bw, by + bh, r,
            fill="white", outline="#ddd", width=1
        )

        # Tail triangle
        tx = self.sprite_x
        ty = by + bh
        self.bubble_tail = self.canvas.create_polygon(
            tx - 8, ty,
            tx + 8, ty,
            tx, ty + 10,
            fill="white", outline="#ddd", width=1,
        )

        # Text
        self.bubble_text_id = self.canvas.create_text(
            bx + pad_x, by + pad_y,
            text=wrapped,
            anchor=tk.NW,
            fill="#333",
            font=("SF Pro", 11) if sys.platform == "darwin" else ("Segoe UI", 10),
        )

    def _hide_bubble(self):
        """Remove the speech bubble."""
        if self.bubble_bg:
            self.canvas.delete(self.bubble_bg)
            self.bubble_bg = None
        if self.bubble_text_id:
            self.canvas.delete(self.bubble_text_id)
            self.bubble_text_id = None
        if self.bubble_tail:
            self.canvas.delete(self.bubble_tail)
            self.bubble_tail = None
        self.bubble_visible = False

    def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        """Draw a rounded rectangle on the canvas."""
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    # ----- Notifications -----
    def notify(self, message):
        """Queue a notification (thread-safe)."""
        self.notification_queue.append(message)

    def _check_queue(self):
        """Check for queued notifications from the Slack thread."""
        if self.notification_queue and not self.is_alerting:
            msg = self.notification_queue.pop(0)
            self._trigger_alert(msg)
        self.root.after(500, self._check_queue)

    def _trigger_alert(self, message):
        """Play the alert animation with speech bubble."""
        self.is_alerting = True

        # Switch to alert sprite
        self._set_sprite(self.sprite_alert)

        # Show bubble
        self._show_bubble(message)

        # Wiggle animation
        self._wiggle(steps_left=8)

        # Reset after duration
        self.root.after(ALERT_DURATION, self._end_alert)

    def _wiggle(self, steps_left=8):
        """Quick wiggle animation."""
        if steps_left <= 0:
            self.canvas.coords(self.sprite_id, self.sprite_x, self.sprite_base_y)
            return

        import random
        dx = random.randint(-4, 4)
        dy = random.randint(-2, 2)
        self.canvas.coords(
            self.sprite_id,
            self.sprite_x + dx,
            self.sprite_base_y + dy - 6
        )
        self.root.after(WIGGLE_DURATION // 8, lambda: self._wiggle(steps_left - 1))

    def _end_alert(self):
        """Return to idle state."""
        self._set_sprite(self.sprite_idle)
        self._hide_bubble()
        self.is_alerting = False

    # ----- Lifecycle -----
    def quit(self):
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ---------------------------------------------------------------------------
# Slack Listener
# ---------------------------------------------------------------------------

def start_slack_listener(buddy, config):
    """Connect to Slack via Socket Mode and listen for DMs / mentions."""
    bot_token = config["SLACK_BOT_TOKEN"]
    app_token = config["SLACK_APP_TOKEN"]

    web_client = WebClient(token=bot_token)

    # Get our own bot user ID so we can detect @mentions
    auth = web_client.auth_test()
    bot_user_id = auth["user_id"]
    print(f"✅ Connected to Slack as <@{bot_user_id}>")

    # Cache for user names
    user_cache = {}

    def get_username(user_id):
        if user_id not in user_cache:
            try:
                result = web_client.users_info(user=user_id)
                user_cache[user_id] = result["user"]["real_name"] or result["user"]["name"]
            except Exception:
                user_cache[user_id] = user_id
        return user_cache[user_id]

    def get_channel_name(channel_id):
        try:
            result = web_client.conversations_info(channel=channel_id)
            ch = result["channel"]
            return ch.get("name", "DM")
        except Exception:
            return "DM"

    def handle_event(client: SocketModeClient, req: SocketModeRequest):
        """Process incoming Slack events."""
        # Acknowledge immediately
        client.send_socket_mode_response(
            SocketModeResponse(envelope_id=req.envelope_id)
        )

        if req.type != "events_api":
            return

        event = req.payload.get("event", {})
        event_type = event.get("type")

        # Skip messages from the bot itself
        if event.get("user") == bot_user_id:
            return
        if event.get("bot_id"):
            return

        sender_id = event.get("user", "")
        sender_name = get_username(sender_id) if sender_id else "Someone"
        channel_id = event.get("channel", "")
        text = event.get("text", "")

        # --- Direct Messages ---
        if event_type == "message" and event.get("channel_type") == "im":
            # Truncate long messages
            preview = text[:80] + "…" if len(text) > 80 else text
            buddy.notify(f"💬 DM from {sender_name}:\n\"{preview}\"")
            print(f"📩 DM from {sender_name}: {preview}")
            return

        # --- @Mentions in channels ---
        if event_type == "message" and f"<@{bot_user_id}>" in text:
            channel_name = get_channel_name(channel_id)
            preview = text.replace(f"<@{bot_user_id}>", "@you")
            preview = preview[:80] + "…" if len(preview) > 80 else preview
            buddy.notify(f"📢 #{channel_name} — {sender_name}:\n\"{preview}\"")
            print(f"📢 Mentioned in #{channel_name} by {sender_name}")
            return

        # --- App mentions (if subscribed) ---
        if event_type == "app_mention":
            channel_name = get_channel_name(channel_id)
            preview = text.replace(f"<@{bot_user_id}>", "@you")
            preview = preview[:80] + "…" if len(preview) > 80 else preview
            buddy.notify(f"📢 #{channel_name} — {sender_name}:\n\"{preview}\"")
            print(f"📢 App mention in #{channel_name} by {sender_name}")
            return

    # Start Socket Mode client in a background thread
    socket_client = SocketModeClient(
        app_token=app_token,
        web_client=web_client,
    )
    socket_client.socket_mode_request_listeners.append(handle_event)

    print("🔌 Connecting to Slack (Socket Mode)...")
    socket_client.connect()
    print("🟢 Listening for DMs and @mentions!\n")
    print("   💡 Right-click the buddy to quit.")
    print("   💡 Drag the buddy to reposition it.\n")


# ---------------------------------------------------------------------------
# Demo mode (no Slack connection — for testing the sprite)
# ---------------------------------------------------------------------------

def run_demo(buddy):
    """Cycle through demo notifications every few seconds."""
    import random

    demo_messages = [
        "💬 DM from Sarah:\n\"Hey, got a minute?\"",
        "📢 #engineering — Alex:\n\"@you Can you review this PR?\"",
        "💬 DM from Jordan:\n\"The deploy looks good 🚀\"",
        "📢 #general — Pat:\n\"@you lunch today?\"",
        "💬 DM from Morgan:\n\"Quick question about the API...\"",
    ]

    def send_demo():
        msg = random.choice(demo_messages)
        buddy.notify(msg)
        buddy.root.after(random.randint(6000, 12000), send_demo)

    buddy.root.after(2000, send_demo)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    demo_mode = "--demo" in sys.argv

    if not demo_mode:
        config = load_config()

    # Create the desktop buddy
    buddy = SlackBuddy()

    if demo_mode:
        print("🎮 Running in DEMO mode (no Slack connection)")
        print("   Right-click the buddy to quit.\n")
        run_demo(buddy)
    else:
        # Start Slack listener in background thread
        slack_thread = threading.Thread(
            target=start_slack_listener,
            args=(buddy, config),
            daemon=True,
        )
        slack_thread.start()

    # Run the GUI (blocks until quit)
    buddy.run()


if __name__ == "__main__":
    main()
