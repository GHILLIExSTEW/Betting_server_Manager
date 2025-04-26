# Betting Server Manager

A commercial Discord bot for managing sports betting with real-time game data and odds.

## Features

- Real-time game data updates
- Live odds tracking
- Bet management
- User balance tracking
- Admin controls
- Caching system for performance
- Database persistence

## Purchase and Installation

1. Contact sales@yourcompany.com to purchase a license
2. After purchase, you will receive access to the repository
3. Clone the repository:
```bash
git clone https://github.com/GHILLIExSTEW/Betting_server_Manager.git
cd Betting_server_Manager
```

4. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

5. Install dependencies:
```bash
pip install -e .
```

6. Create a `.env` file with your configuration:
```env
DISCORD_TOKEN=your_discord_token
DATABASE_URL=postgresql://user:password@localhost:5432/betting_bot
REDIS_URL=redis://localhost:6379/0
LICENSE_KEY=your_purchased_license_key
```

7. Initialize the database:
```bash
python -m bot.db_manager
```

## Usage

Start the bot:
```bash
betting-bot
```

### Commands

- `/view_games` - View active games
- `/view_odds <game_id>` - View odds for a specific game
- `/bet <game_id> <amount> <team>` - Place a bet
- `/balance` - Check your balance
- `/leaderboard` - View top bettors

## Project Structure

```
.
├── api/                # API endpoints
├── views/             # View templates
├── web/              # Web interface
└── README.md         # This file
```

## License

This is a commercial product. Unauthorized use, copying, modification, or distribution is strictly prohibited. A valid license is required for use.