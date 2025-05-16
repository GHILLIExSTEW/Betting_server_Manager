import aiomysql
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def init_mysql_db():
    # Get MySQL connection details from environment variables
    MYSQL_HOST = os.getenv('MYSQL_HOST')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
    MYSQL_DB = os.getenv('MYSQL_DB')

    if not all([MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB]):
        print("Error: Missing required MySQL environment variables")
        return

    try:
        # Connect to MySQL server
        conn = await aiomysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )

        async with conn.cursor() as cursor:
            # Create database if it doesn't exist
            await cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB}")
            await cursor.execute(f"USE {MYSQL_DB}")

            # Read and execute schema.sql
            with open('schema.sql', 'r') as f:
                schema_sql = f.read()
                for statement in schema_sql.split(';'):
                    if statement.strip():
                        await cursor.execute(statement)

            # Read and execute fix_bets_table.sql
            with open('fix_bets_table.sql', 'r') as f:
                fix_sql = f.read()
                for statement in fix_sql.split(';'):
                    if statement.strip():
                        await cursor.execute(statement)

            await conn.commit()
            print("MySQL database initialized successfully!")

    except Exception as e:
        print(f"Error initializing MySQL database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(init_mysql_db()) 