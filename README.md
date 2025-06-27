# Telegram Translator Channel Bot 🤖

A Telegram bot that lets you post bilingual (RU ↔ EN) content in your channel and switch languages with a single inline button.
Built on aiogram 3, works with text, photos, and videos.

---

## 🚀 Features

- One-step workflow – send a Russian post, the bot auto-translates it to English.
- Preview dialog – bot shows the English draft and asks: ✅ Send • ✏️ Edit • ❌ Cancel.
- Inline toggle – subscribers can switch between 🇷🇺 RU and 🇬🇧 EN versions in-place.
- Rich media – supports:
- Pure text
- Photos with captions
- Videos with captions
- SQLite persistence – every post is stored locally.
- Ready for production – run it as a systemd service on Ubuntu.

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
python bot.py
```

To run on Ubuntu via systemd:

Create `/etc/systemd/system/translator_bot.service`:

```ini
[Unit]
Description=Telegram Translator Channel Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/translator_channel_bot
ExecStart=/opt/translator_channel_bot/venv/bin/python /opt/translator_channel_bot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then reload and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable translator_bot
sudo systemctl start  translator_bot
```

---

## 🧑‍💻 Author

Made with 💬 by [lov3rick](https://t.me/withlov3rick)

---

## ⚠️ Note

Keep your `.env` file private — never commit it to public repositories.
