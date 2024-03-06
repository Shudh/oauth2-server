import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Use the DATABASE_URL environment variable
DATABASE_URI = os.getenv("DATABASE_URL")

if not DATABASE_URI:
    raise ValueError("No DATABASE_URL set for Flask application")

engine = create_engine(DATABASE_URI)

def add_password_hash_column():
    # Define your SQL statement for adding a new column
    alter_table_statement = text("""
        ALTER TABLE oauth_user
        ADD COLUMN IF NOT EXISTS password_hash VARCHAR(128);
    """)

    with engine.connect() as connection:
        try:
            # Execute the SQL statement
            connection.execute(alter_table_statement)
            print("Column 'password_hash' added successfully.")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    add_password_hash_column()
