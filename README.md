# Eve-Time Discord Bot

Eve-Time is a simple Discord bot created to fetch and display the current time in various time zones, including the Eve Online time (UTC).
![Example](https://img.originalsinners.org/CivU7/JUsIkICu01.png)

## Table of Contents
- [Features](#features)
- [Dependencies](#Dependencies)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Docker-Compose Deployment](#docker-compose-deployment)

## Features
- Fetch the current UTC time (Eve Online time).
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

## Docker-Compose Deployment

Deploying the Eve-Time bot using Docker and `docker-compose` simplifies the process by handling the dependencies and ensuring consistent behavior across different environments.

### Prerequisites:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Steps:

1. **Clone the repository**:

    ```
    git clone https://github.com/kaspaeve/Eve-Time.git
    ```

2. **Navigate to the project directory**:

    ```
    cd Eve-Time
    ```

3. **Ensure your `.env` file is set up** in the root directory with the necessary values:

    ```
    BOT_TOKEN=Your_Discord_Bot_Token
    ALLOWED_CHANNEL_ID=Your_Allowed_Channel_ID
    ```

4. **Use Docker Compose to build and start the bot**:

    ```
    docker-compose up --build -d
    ```

    The `--build` flag ensures that the Docker image is built using the provided Dockerfile, and the `-d` flag runs the container in detached mode.

5. **Check the bot logs (if necessary)**:

    ```
    docker-compose logs -f
    ```

    The `-f` flag lets you follow the logs in real-time.

6. **Stopping the bot**:

    ```
    docker-compose down
    ```

This approach ensures that your bot runs in an isolated environment, making it less susceptible to discrepancies between development and production environments.

## **Docker-Compose YML
```
services:
  eve-time-bot:
    image: kaspaeve/eve-time:latest
    build: 
      context: https://github.com/kaspaeve/Eve-Time.git
      dockerfile: Dockerfile
    environment:
      - BOT_TOKEN=your_bot_token
      - ALLOWED_CHANNEL_ID=your_allowed_channel_id
```
