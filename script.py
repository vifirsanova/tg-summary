import tomllib, argparse, json, asyncio, sys
from pathlib import Path
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import InputPeerChannel, InputMessagesFilterEmpty
from datetime import datetime, timedelta

async def load_config(config_path):
    """Load configuration from TOML config file"""
    try:
        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
        return (
            config['telegram']['api_id'],
            config['telegram']['api_hash'],
            config['telegram']['phone_number'],
            config['chat']['entity']
        )
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

async def get_chat_history(client, chat_entity):
    """Fetch chat history for the last 24 hours"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    messages_data = []
    offset_id = 0
    sender_cache = {}  # Cache for sender information

    try:
        chat = await client.get_entity(chat_entity)
    except Exception as e:
        print(f"Error accessing chat: {e}")
        sys.exit(1)
    
    while True:
        try:
            messages = await client(SearchRequest(
                peer=chat,
                limit=100,
                min_date=start_time,
                max_date=end_time,
                offset_id=offset_id,
                filter=InputMessagesFilterEmpty(),
                q = '',
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
        except Exception as e:
            print(f"Error fetching messages: {e}")
            break

        if not messages.messages:
            break

        # Process messages in batch
        batch_messages = [msg for msg in messages.messages if start_time.isoformat() <= msg.date.isoformat() <= end_time.isoformat()]
        
        # Pre-fetch sender entities
        sender_ids = {msg.sender_id for msg in batch_messages 
                     if msg.sender_id and msg.sender_id not in sender_cache}
        if sender_ids:
            try:
                senders = await client.get_entity(sender_ids)
                sender_cache.update({s.id: s for s in senders})
            except Exception as e:
                print(f"Warning: Couldn't fetch some senders: {e}")

        # Process messages with cached senders
        for msg in batch_messages:
            sender = sender_cache.get(msg.sender_id) if msg.sender_id else None
            messages_data.append({
                "sender": {
                    "username": sender.username if sender else None,
                    "name": getattr(sender, 'first_name', None),
                    "surname": getattr(sender, 'last_name', None)
                },
                "date": msg.date.isoformat(),
                "text": msg.message
            })

        if len(messages.messages) < 100:  # Reached the end
            break
            
        offset_id = messages.messages[-1].id
        await asyncio.sleep(0.5)  # Rate limiting

    return messages_data

async def main():
    """Main async function to run the script"""
    parser = argparse.ArgumentParser(description='Fetch Telegram chat history from last 24 hours')
    parser.add_argument('-c', '--config', default='config.toml',
                       help='Path to config file (default: config.toml)')
    parser.add_argument('-o', '--output', default='telegram_history.json',
                       help='Output file path (default: telegram_history.json)')
    args = parser.parse_args()

    api_id, api_hash, phone_number, chat_entity = await load_config(args.config)
    
    try:
        async with TelegramClient('session_name', api_id, api_hash) as client:
            await client.start(phone_number)
            messages_data = await get_chat_history(client, int(chat_entity))
            
            # Ensure output directory exists
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(messages_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Saved {len(messages_data)} messages to {output_path}")
    except Exception as e:
        print(f"Error during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

"""
### Example Usage:

1. **Basic usage with default paths**:
   ```bash
   python script.py
   ```
   - Uses `config.toml` in current directory
   - Saves output to `telegram_history.json` in current directory

2. **Custom config path**:
   ```bash
   python3 script.py -c /path/to/custom_config.toml
   ```

3. **Custom output path**:
   ```bash
   python3 script.py -o /custom/path/output.json
   ```

4. **Both custom config and output**:
   ```bash
   python3 script.py -c ~/telegram/configs/my_config.toml -o ~/telegram/data/history.json
   ```

### Example config.toml:
```toml
[telegram]
api_id = "123456"
api_hash = "abcdef1234567890abcdef1234567890"
phone_number = "+1234567890"

[chat]
entity = "@mygroup"  # Can be @username, +phone, or numeric ID
```
"""
