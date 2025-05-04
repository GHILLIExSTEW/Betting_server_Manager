import sqlite3
import os

def init_db():
    # Ensure the data directory exists
    os.makedirs('betting-bot/data', exist_ok=True)
    
    # Connect to the database
    conn = sqlite3.connect('betting-bot/data/betting.db')
    cursor = conn.cursor()
    
    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS guild_settings")
    cursor.execute("DROP TABLE IF EXISTS unit_records")
    
    # Create guild_settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id INTEGER PRIMARY KEY,
        voice_channel_id INTEGER,
        yearly_channel_id INTEGER,
        is_active BOOLEAN DEFAULT TRUE,
        is_paid BOOLEAN DEFAULT FALSE,
        subscription_level TEXT DEFAULT 'free',
        embed_channel_1 INTEGER,
        embed_channel_2 INTEGER,
        command_channel_1 INTEGER,
        command_channel_2 INTEGER,
        daily_report_time TEXT,
        member_role INTEGER,
        bot_name_mask TEXT,
        bot_image_mask TEXT,
        guild_default_image TEXT,
        default_parlay_thumbnail TEXT,
        total_result_value REAL DEFAULT 0.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create unit_records table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS unit_records (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        monthly_result_value REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(guild_id, user_id, year, month)
    )
    """)
    
    # Insert test data for the two guilds
    cursor.execute("""
    INSERT OR REPLACE INTO guild_settings (guild_id, voice_channel_id, yearly_channel_id, is_active, is_paid, subscription_level)
    VALUES 
        (1328116926903353398, NULL, NULL, 1, 1, 'premium'),
        (1328126227013439601, NULL, NULL, 1, 1, 'premium')
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db() 