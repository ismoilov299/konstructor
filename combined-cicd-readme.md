# Telegram Bot Constructor CI/CD Template

CI/CD configuration for Django project with Aiogram Telegram bot integration.

## Project Structure
```
constructor/
├── .github/
│   └── workflows/
│       └── main.yml
├── scripts/
│   ├── deploy.sh
│   ├── start_django.sh
│   └── backup.sh
├── config/
│   ├── nginx.conf
│   ├── django.service
├── requirements.txt
└── README.md
```

## Quick Start

1. Create necessary directories:
```bash
mkdir -p .github/workflows scripts config
```

2. Copy all configuration files
3. Update settings with your project details
4. Add GitHub secrets
5. Push changes

## Configuration Files

### 1. GitHub Actions Workflow
[View workflow file](.github/workflows/main.yml)
- Automated testing
- Django migrations and static files
- Bot deployment
- Server configuration

### 2. Scripts
- [deploy.sh](scripts/deploy.sh): Main deployment script
- [start_django.sh](scripts/start_django.sh): Django server startup
- [start_bot.sh](scripts/start_bot.sh): Telegram bot startup
- [backup.sh](scripts/backup.sh): Database and media backup

### 3. Server Configs
- [nginx.conf](config/nginx.conf): Nginx web server configuration
- [django.service](config/django.service): Django service configuration
- [telegram-bot.service](config/telegram-bot.service): Bot service configuration

## Required GitHub Secrets

```
DJANGO_SECRET_KEY=your_django_secret_key
DATABASE_URL=postgresql://user:password@host:5432/dbname
BOT_TOKEN=your_telegram_bot_token
SERVER_HOST=your_server_ip
SERVER_USERNAME=your_ssh_username
SERVER_SSH_KEY=your_ssh_private_key
```

## Server Setup

1. Install dependencies:
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv nginx postgresql
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Setup Nginx:
```bash
sudo cp config/nginx.conf /etc/nginx/sites-available/django-bot
sudo ln -s /etc/nginx/sites-available/django-bot /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

4. Setup services:
```bash
sudo cp config/django.service /etc/systemd/system/
sudo cp config/telegram-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable django telegram-bot
sudo systemctl start django telegram-bot
```

## Development

Start Django development server:
```bash
./scripts/start_django.sh
```

Start Telegram bot:
```bash
./scripts/start_bot.sh
```

## Checking Status

```bash
# Django service status
sudo systemctl status django

# View logs
sudo journalctl -u django -f

```

## Support

For issues or questions, please open an issue in the repository.

## License

MIT
