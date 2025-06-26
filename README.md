# Telegram Translator Channel Bot 🤖

A simple Telegram bot for posting bilingual content to your Telegram channel with language toggle buttons.  
Built with [aiogram 3](https://docs.aiogram.dev/en/latest/), supports text, photo, and video posts.

---

## 🚀 Features

- Admin sends posts in Russian and English.
- Bot publishes Russian version to the Telegram channel.
- Toggle button switches between 🇷🇺 Russian and 🇬🇧 English versions.
- Supports:
  - Text messages
  - Photo with caption
  - Video with caption
- Posts saved to SQLite database.
- Can run as a systemd service on Ubuntu server.

---

## 🛠 Requirements

- Python 3.10+
- Telegram Bot Token
- Telegram Channel (bot must be admin)
- Your Telegram User ID (admin rights)

---

## 📦 Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/lov3rick/translator_channel_bot.git
   cd translator_channel_bot
   ```

2. **Create a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**

   Create a `.env` file in the root:

   ```env
   BOT_TOKEN=your_telegram_bot_token
   CHANNEL_ID=@your_channel_username
   ADMIN_IDS=your_telegram_id
   ```

---

## ▶️ Run the Bot

To run manually:

```bash
python translator_channel_bot.py
```

To run on Ubuntu via systemd:

Create `/etc/systemd/system/translator_bot.service`:

```ini
[Unit]
Description=Telegram Translator Bot
After=network.target

[Service]
User=your_linux_user
WorkingDirectory=/path/to/translator_channel_bot
ExecStart=/path/to/translator_channel_bot/venv/bin/python /path/to/translator_channel_bot/translator_channel_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then reload and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable translator_bot.service
sudo systemctl start translator_bot.service
```

---

## 🧑‍💻 Author

Made with 💬 by [@lov3rick](https://t.me/withlov3rick)

---

## ⚠️ Note

Keep your `.env` file private — never commit it to public repositories.
