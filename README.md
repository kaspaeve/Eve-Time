# Eve-Time Discord Bot

Eve-Time is a simple Discord bot created to fetch and display the current time in various time zones, including the Eve time (UTC).

## Table of Contents
- [Features](#features)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)

## Features
- Fetch the current UTC time (Eve time).
- Display the current time in various US time zones (CST, EST, PST, MST).

## Configuration

1. **Clone the repository:**
    ```bash
    git clone https://github.com/kaspaeve/Eve-Time.git
    ```

2. **Navigate to the project directory:**
    ```bash
    cd Eve-Time
    ```

3. **Create a `.env` file in the root directory** and add your Discord bot token and the ID of the allowed channel:
    ```env
    BOT_TOKEN=Your_Discord_Bot_Token
    ALLOWED_CHANNEL_ID=Your_Allowed_Channel_ID
    ```

## Running the Bot

1. **Execute the Python script:**
    ```bash
    python your_bot_script_name.py
    ```

Once the bot is running, use the `!time` command in the allowed channel to fetch and display the current time.

---

**Note:** Ensure you have the necessary Python packages installed and the environment properly set up to run the bot.
