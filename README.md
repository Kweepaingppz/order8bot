# Dummy Telegram E-commerce Bot

This is a dummy Telegram e-commerce bot that allows users to view products, add them to a cart, and go through a simulated checkout process.

## Setup and Running Instructions

Follow these steps to get your dummy bot up and running:

### 1. Get Your Telegram Bot Token

To run this bot, you need a Telegram Bot Token. If you don't have one, follow these steps:

1.  Open Telegram and search for **BotFather**.
2.  Start a chat with BotFather and send the command `/newbot`.
3.  Follow the instructions: choose a name for your bot and then a username (must end with 'bot', e.g., `MyAwesomeStoreBot`).
4.  BotFather will provide you with an HTTP API Token. It looks something like `1234567890:ABCDEF1234567890abcdef1234567890`.

### 2. Configure the Bot Token

1.  You will find a file named `.env` in the bot's directory.
2.  Open this `.env` file.
3.  Replace `your_telegram_bot_token_here` with the actual token you received from BotFather.

    Example `.env` file content:
    ```
    BOT_TOKEN=1234567890:ABCDEF1234567890abcdef1234567890
    ```

### 3. Run the Bot

Once the token is configured, you can run the bot. Make sure you have Python 3 installed.

1.  Navigate to the bot's directory in your terminal.
2.  Install the required Python libraries (if you haven't already):
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the bot:
    ```bash
    python dummy_bot.py
    ```

The bot should now be running. You can open Telegram, search for your bot by its username, and start interacting with it by sending the `/start` command.

## Important Notes

*   **Dummy Data:** This bot uses dummy product data and images. The images are expected to be in a `dummy_images` folder relative to the bot script.
*   **In-memory Storage:** User carts and order data are stored in memory and will be lost if the bot is stopped or restarted. For a production application, a database would be required.
*   **No Real Payment:** The checkout process is simulated and does not involve actual payment processing.

