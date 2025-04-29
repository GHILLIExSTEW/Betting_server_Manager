# Discord Betting Bot

A Discord bot for managing sports betting and capper statistics.

## Features

- Place bets on sports games
- View betting statistics
- Manage cappers and their profiles
- Admin commands for server setup
- Team and league logo management

## Commands

- `/bet` - Place a new bet
- `/stats` - View betting statistics
- `/admin` - Server setup and management
- `/setid` - Set up a user as a capper
- `/remove_user` - Remove a user from the server
- `/load_logos` - Load team and league logos (Admin only)

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your Discord bot token:
   ```
   DISCORD_TOKEN=your_bot_token
   TEST_GUILD_ID=your_test_guild_id
   ```
4. Run the bot:
   ```bash
   python main.py
   ```

## Requirements

- Python 3.8+
- discord.py
- aiosqlite
- Pillow
- requests

## Project Structure

```
betting-bot/
├── commands/          # Command modules
├── services/          # Service modules
├── utils/            # Utility modules
├── config/           # Configuration files
├── assets/           # Image assets
│   ├── logos/        # Team logos
│   └── leagues/      # League logos
└── data/             # Database files
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.