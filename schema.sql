-- Create database if not exists
CREATE DATABASE IF NOT EXISTS betting_bot;
USE betting_bot;

-- Add bet_details column if it doesn't exist
ALTER TABLE bets ADD COLUMN IF NOT EXISTS bet_details JSON;

-- Guilds table
CREATE TABLE IF NOT EXISTS guilds (
    guild_id BIGINT PRIMARY KEY,
    guild_name VARCHAR(255) NOT NULL,
    commands_registered BOOLEAN DEFAULT FALSE,
    subscription_status VARCHAR(50) DEFAULT 'free',
    subscription_end_date TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    avatar_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Guild Users table (junction table)
CREATE TABLE IF NOT EXISTS guild_users (
    guild_id BIGINT,
    user_id BIGINT,
    is_admin BOOLEAN DEFAULT FALSE,
    is_capper BOOLEAN DEFAULT FALSE,
    units_balance FLOAT DEFAULT 0.0,
    lifetime_units FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Bets table
CREATE TABLE IF NOT EXISTS bets (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Unit Records table
CREATE TABLE IF NOT EXISTS unit_records (
    record_id INT AUTO_INCREMENT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    units FLOAT NOT NULL,
    total FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY unique_monthly_record (guild_id, user_id, year, month)
);

-- Games table
CREATE TABLE IF NOT EXISTS games (
    game_id VARCHAR(50) PRIMARY KEY,
    league VARCHAR(50) NOT NULL,
    home_team VARCHAR(255) NOT NULL,
    away_team VARCHAR(255) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL,
    score JSON,
    odds JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Team Logos table
CREATE TABLE IF NOT EXISTS team_logos (
    team_key VARCHAR(50) PRIMARY KEY,
    league VARCHAR(50) NOT NULL,
    logo_url VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- League Logos table
CREATE TABLE IF NOT EXISTS league_logos (
    league_key VARCHAR(50) PRIMARY KEY,
    logo_url VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- User Images table
CREATE TABLE IF NOT EXISTS user_images (
    user_id BIGINT PRIMARY KEY,
    image_url VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Bet Reactions table
CREATE TABLE IF NOT EXISTS bet_reactions (
    reaction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    bet_serial BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    emoji VARCHAR(32) NOT NULL,
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bet_serial) REFERENCES bets(bet_serial) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX idx_bets_guild_user ON bets(guild_id, user_id);
CREATE INDEX idx_bets_status ON bets(status);
CREATE INDEX idx_unit_records_guild_user ON unit_records(guild_id, user_id);
CREATE INDEX idx_games_league ON games(league);
CREATE INDEX idx_games_status ON games(status);
CREATE INDEX idx_team_logos_league ON team_logos(league);
CREATE INDEX idx_bet_reactions_bet ON bet_reactions(bet_serial);
CREATE INDEX idx_bet_reactions_user ON bet_reactions(user_id);
CREATE INDEX idx_bet_reactions_message ON bet_reactions(message_id);

-- Create views
CREATE VIEW monthly_stats AS
SELECT 
    gu.guild_id,
    gu.user_id,
    u.username,
    u.display_name,
    ur.year,
    ur.month,
    ur.units,
    ur.total,
    COUNT(b.bet_serial) as total_bets,
    SUM(CASE WHEN b.status = 'won' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN b.status = 'lost' THEN 1 ELSE 0 END) as losses
FROM guild_users gu
JOIN users u ON gu.user_id = u.user_id
LEFT JOIN unit_records ur ON gu.guild_id = ur.guild_id AND gu.user_id = ur.user_id
LEFT JOIN bets b ON gu.guild_id = b.guild_id AND gu.user_id = b.user_id
GROUP BY gu.guild_id, gu.user_id, ur.year, ur.month;

-- Create stored procedures
DELIMITER //

CREATE PROCEDURE update_monthly_totals(IN p_guild_id BIGINT, IN p_year INT, IN p_month INT)
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_user_id BIGINT;
    DECLARE v_total FLOAT;
    DECLARE cur CURSOR FOR 
        SELECT user_id, SUM(units) 
        FROM unit_records 
        WHERE guild_id = p_guild_id 
        AND year = p_year 
        AND month = p_month
        GROUP BY user_id;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    OPEN cur;
    read_loop: LOOP
        FETCH cur INTO v_user_id, v_total;
        IF done THEN
            LEAVE read_loop;
        END IF;
        
        UPDATE unit_records 
        SET total = v_total 
        WHERE guild_id = p_guild_id 
        AND user_id = v_user_id 
        AND year = p_year 
        AND month = p_month;
    END LOOP;
    CLOSE cur;
END //

DELIMITER ; 