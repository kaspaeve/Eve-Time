# Eve-Time Discord Bot

Eve-Time is a simple Discord bot created to fetch and display the current time in various time zones, including the Eve time (UTC).

## Table of Contents
- [Features](#features)
- [Dependencies](#Dependencies)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)

## Features
- Fetch the current UTC time (Eve time).
- Display the current time in various US time zones (EST, CST, MST, PST).
- Enhanced error handling to gracefully handle unexpected issues and provide informative feedback.
- Integrated logging mechanism that tracks both regular and error activities, making debugging and tracking easier.

## Dependencies

To ensure that the bot runs smoothly, you must install a few dependencies. Here's a list of everything you'll need:

### 1. Discord.py 
This is the main library that allows our script to interact with the Discord API.
```bash
pip install discord.py
```

### 2. Datetime 
While it's a built-in module in Python, you might need it to handle date and time functionalities.

### 3. Pytz 
This library allows you to work with time zones.
```bash
pip install pytz
```

### 4. Python Decouple 
Useful for extracting configuration values from `.env` files.
```bash
pip install python-decouple
```

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
