# MultiLangTranslator Bot Deployment on Render

This guide provides instructions for deploying the MultiLangTranslator Bot on Render.

## 1. Environment Variables

Before deploying, ensure you set the following environment variables in your Render service settings:

- `ADMIN_ID`: Your Telegram Admin User ID.
- `TARGET_GROUP_ID`: The ID of the target Telegram group.
- `BOT_TOKEN`: Your Telegram Bot Token (obtained from BotFather).
- `PAYEER_ACCOUNT`: Your Payeer account ID.
- `BITCOIN_WALLET_ADDRESS`: Your Bitcoin wallet address.

## 2. Procfile

The `Procfile` specifies the command to run your application. Ensure it contains the following:

```
web: bash run_bot.sh
```

## 3. run_bot.sh

This script is responsible for starting the bot. Ensure it contains the following:

```bash
#!/bin/bash

# Ensure the script exits if any command fails
set -e

# Navigate to the bot's main directory
cd MultiLangTranslator

# Execute the main bot script
python3.11 main.py
```

## 4. Deployment Steps

1. **Create a new Web Service on Render:**
   - Connect your Git repository (where this bot's code is hosted).
   - Choose a unique name for your service.
   - Select `Python 3` as the runtime.
   - Set the `Build Command` to `pip install -r requirements.txt`.
   - Set the `Start Command` to `bash run_bot.sh`.

2. **Add Environment Variables:**
   - In the Render dashboard for your service, go to the `Environment` section.
   - Add all the environment variables listed in section 1 with their respective values.

3. **Deploy:**
   - Click `Deploy` to start the deployment process.

## 5. Important Notes

- **Webhook vs. Long Polling:** This bot is configured for long polling. Ensure no webhooks are set for your bot via BotFather or previous deployments, as this can cause conflicts.
- **Single Instance:** Ensure only one instance of the bot is running at any given time to avoid `Conflict` errors from Telegram.
- **Error Logging:** Bot errors will be logged to the console and sent to the `ADMIN_ID` via Telegram.

