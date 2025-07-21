#!/bin/bash

# Default file paths
CONFIG_FILE="config.toml"
INPUT_JSON="telegram_history.json"
FORMATTED_HISTORY="formatted_history.txt"
SUMMARY_OUTPUT="telegram_summary.txt"

# Run the Telegram chat history scraper
echo "Fetching Telegram chat history..."
python3 script.py -c "$CONFIG_FILE" -o "$INPUT_JSON"

# Check if the chat history was successfully created
if [ ! -f "$INPUT_JSON" ]; then
    echo "Error: Failed to create chat history file $INPUT_JSON"
    exit 1
fi

# Format the JSON chat history using Python
echo "Preparing chat history for summarization..."
python3 - <<END
import json

with open('$INPUT_JSON', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('$FORMATTED_HISTORY', 'w', encoding='utf-8') as out:
    for msg in data:
        username = msg['sender']['username'] if msg['sender'] and msg['sender']['username'] else 'Unknown'
        out.write(f"{msg['date']} {username}: {msg['text']}\\n")
END

# Check if formatting succeeded
if [ ! -f "$FORMATTED_HISTORY" ]; then
    echo "Error: Failed to format chat history"
    exit 1
fi

# Run the summarizer
echo "Generating summary..."
python3 run_gemma.py "$FORMATTED_HISTORY" "$SUMMARY_OUTPUT"

# Check if summary was created
if [ -f "$SUMMARY_OUTPUT" ]; then
    echo -e "\nSummary Content:"
    cat "$SUMMARY_OUTPUT"
    echo -e "\nDone! Summary saved to $SUMMARY_OUTPUT"
else
    echo "Error: Failed to generate summary"
    exit 1
fi
