USE betting_bot;

-- Drop the existing bets table if it exists
DROP TABLE IF EXISTS bets;

-- Recreate the bets table with the correct schema
CREATE TABLE bets (
    bet_serial BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    league VARCHAR(50) NOT NULL,
    bet_type VARCHAR(50) NOT NULL,
    bet_details JSON NOT NULL,
    units FLOAT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    result VARCHAR(20) DEFAULT NULL,
    confirmed BOOLEAN DEFAULT 0,
    channel_id BIGINT,
    odds FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Recreate the index
CREATE INDEX idx_bets_guild_user ON bets(guild_id, user_id);
CREATE INDEX idx_bets_status ON bets(status); 