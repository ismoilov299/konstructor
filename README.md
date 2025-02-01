# Bot Constructor

A multi-bot Telegram framework with support for various bot types including media downloader, anonymous messaging, GPT chat, and movie search bots.

## Available Bots

### 1. Media Downloader Bot (kino_bot)
- Downloads content from YouTube, Instagram, and TikTok
- Supports multiple formats and quality selection
- Progress tracking and status updates

### 2. Anonymous Messaging Bot (annon_bot)
- Allows anonymous message sending
- Message forwarding functionality
- Privacy-focused communication

### 3. GPT Chat Bot (chat_gpt_bot)
- Integration with GPT model
- Natural language conversations
- Smart response generation

### 4. Movie Search Bot (leomatch)
- Movie and TV show search functionality
- Media information retrieval
- User preferences handling

## Project Structure

```
konstructor/
├── modul/
│   └── clientbot/
│       └── handlers/
│           ├── annon_bot/      # Anonymous messaging bot
│           ├── chat_gpt_bot/   # GPT chat bot
│           ├── kino_bot/       # Media downloader bot
│           ├── leomatch/       # Movie search bot
│           └── refs/          # Reference handlers
├── bot_api/
│   ├── models.py
│   └── views.py
└── handlers/
    ├── admin_panel.py
    ├── callback_queries.py
    ├── cancel_state.py
    ├── download.py
    ├── main.py
    └── state_handlers.py
```

## Setup & Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- Telegram Bot Tokens (one for each bot)
- OpenAI API key (for GPT bot)

### Environment Setup

Create `.env` file:
```env
# Main bot token
BOT_TOKEN=your_main_bot_token

# Other configurations
ADMINS=["admin_id_1", "admin_id_2"]
DATABASE_URL=postgresql://user:password@localhost/dbname
OPENAI_API_KEY=your_openai_api_key  # For GPT bot
```

### Installation Steps

1. Clone repository:
```bash
git clone https://github.com/ismoilov299/konstructor.git
cd konstructor
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Setup database:
```bash
alembic upgrade head
```

## Bot Usage

### Media Downloader Bot
- Send video links from YouTube, Instagram, or TikTok
- Select quality/format
- Receive downloaded content

### Anonymous Bot
- Start bot with `/start`
- Use `/send` command to send anonymous message
- Follow bot instructions

### GPT Chat Bot
- Start conversation with `/start`
- Ask questions or chat naturally
- Use special commands for specific functions

### Movie Search Bot
- Search movies with `/search`
- Get movie information
- Save favorites

## Development

### Adding New Bot
1. Create new folder in `handlers/`
2. Implement bot logic
3. Add bot token to `.env`
4. Register handlers in `main.py`


## License

[MIT](LICENSE)

## Contact

Ismoilov - [@GitHub](https://github.com/ismoilov299)

Project Link: [https://github.com/ismoilov299/konstructor](https://github.com/ismoilov299/konstructor)
