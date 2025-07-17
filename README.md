# Telegram Chat Summary Bot

A Telegram bot that generates chat summaries using Google's Gemma-1.5b language model with 8-bit quantization.

<img width="540" height="513" alt="image" src="https://github.com/user-attachments/assets/bc1d9a25-2e38-484b-9b1d-d704efc50786" />

## Features

- Generates chat summaries for periods:
  - Last 24 hours
  - Last 3 days
  - Last week
- Optimized for Russian language conversations
- 8-bit quantization for reduced memory usage
- Keyboard interface
- Message storage in memory

## Hardware Requirements

| Configuration       | Minimum Requirements          | Recommended                  |
|---------------------|-------------------------------|------------------------------|
| With GPU (CUDA)     | NVIDIA GPU (4GB VRAM)         | RTX 3060/T4 or better        |
| CPU-only            | 16GB RAM                      | 32GB RAM + AVX2 support      |
| Disk Space          | 5GB free                      | 10GB SSD                     |

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/vifirsanova/tg-summary.git
   cd tg-summary
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create `config.toml`:
   ```toml
   [telegram]
   bot_token = "your_bot_token_here"  # Get from @BotFather

   [model]
   name = "google/gemma-1.5b-it"
   quantize = true    # Enable 8-bit quantization
   device = "auto"    # "auto", "cuda" or "cpu"
   dtype = "float16"  # "float16" or "float32"
   ```

4. Create prompt files:
   ```bash
   mkdir prompts
   echo "Ты помощник для генерации кратких выжимок чатов на русском языке." > prompts/system_prompt.txt
   echo "Проанализируй все сообщения... (paste full prompt)" > prompts/summary_prompt.txt
   ```

## Usage

1. Start the bot:
   ```bash
   python3 bot.py
   ```

2. In Telegram:
   - Send `/start` to initialize the bot
   - Send `/summary` and select time period
   - Wait for the выжимка (typically 10-30 seconds)

## Support

For issues or questions, please [open an issue](https://github.com/vifirsanova/tg-summary/issues)
