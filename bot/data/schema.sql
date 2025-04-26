-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    balance DECIMAL(10, 2) DEFAULT 1000.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create guilds table
CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    guild_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create guild_users table
CREATE TABLE IF NOT EXISTS guild_users (
    guild_id BIGINT REFERENCES guilds(guild_id),
    user_id BIGINT REFERENCES users(user_id),
    units_balance DECIMAL(10, 2) DEFAULT 1000.00,
    lifetime_units DECIMAL(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);

-- Create games table
CREATE TABLE IF NOT EXISTS games (
    game_id VARCHAR(255) PRIMARY KEY,
    league VARCHAR(100) NOT NULL,
    home_team VARCHAR(255) NOT NULL,
    away_team VARCHAR(255) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    status VARCHAR(50) DEFAULT 'scheduled',
    score JSONB,
    odds JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create bets table
CREATE TABLE IF NOT EXISTS bets (
    bet_serial SERIAL PRIMARY KEY,
    guild_id BIGINT REFERENCES guilds(guild_id),
    user_id BIGINT REFERENCES users(user_id),
    game_id VARCHAR(255) REFERENCES games(game_id),
    bet_type VARCHAR(50) NOT NULL,
    selection VARCHAR(255) NOT NULL,
    units DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    result VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create transactions table
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id SERIAL PRIMARY KEY,
    guild_id BIGINT REFERENCES guilds(guild_id),
    user_id BIGINT REFERENCES users(user_id),
    amount DECIMAL(10, 2) NOT NULL,
    type VARCHAR(50) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create unit_records table
CREATE TABLE IF NOT EXISTS unit_records (
    record_id SERIAL PRIMARY KEY,
    guild_id BIGINT REFERENCES guilds(guild_id),
    user_id BIGINT REFERENCES users(user_id),
    year INT NOT NULL,
    month INT NOT NULL,
    units DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (guild_id, user_id, year, month)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_games_league ON games(league);
CREATE INDEX IF NOT EXISTS idx_games_status ON games(status);
CREATE INDEX IF NOT EXISTS idx_bets_status ON bets(status);
CREATE INDEX IF NOT EXISTS idx_bets_user ON bets(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_unit_records_user ON unit_records(user_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_guilds_updated_at
    BEFORE UPDATE ON guilds
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_guild_users_updated_at
    BEFORE UPDATE ON guild_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_games_updated_at
    BEFORE UPDATE ON games
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bets_updated_at
    BEFORE UPDATE ON bets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 