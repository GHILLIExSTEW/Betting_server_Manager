# Discord Betting Bot

A Discord bot for managing sports betting and capper statistics.

## Features

- **Capper Management**
  - `/setid` - Set up a user as a capper
  - `/remove_user` - Remove a user from the system

- **Betting System**
  - `/betting` - Place bets on games
  - `/stats` - View betting statistics and leaderboards

- **Admin Tools**
  - `/admin` - Server setup and management
  - `/load_logos` - Load team and league logos

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```
   DISCORD_TOKEN=your_bot_token
   TEST_GUILD_ID=your_test_guild_id
   ```
4. Run the bot:
   ```bash
   python betting-bot/main.py
   ```

## Requirements

- Python 3.8+
- Discord.py
- SQLite3
- Other dependencies listed in `requirements.txt`

## License

This project is licensed under the MIT License - see the LICENSE file for details.