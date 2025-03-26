import asyncio
import aiosqlite
import datetime
import random

DATABASE = 'playtime.db'

async def main():
    async with aiosqlite.connect(DATABASE) as db:
        # Create the playtime table if it doesn't exist
        await db.execute('''
            CREATE TABLE IF NOT EXISTS playtime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                playtime REAL,
                date TEXT
            )
        ''')
        # Create the goals table if it doesn't exist
        await db.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                user_id INTEGER PRIMARY KEY,
                goal REAL
            )
        ''')
        await db.commit()

        # Define dummy users with their IDs and usernames
        users = [
            {"id": 1037849676801638430, "username": "t3mite"},
            {"id": 1050582024638959656, "username": "charliecat999"},
            {"id": 1117914448745738444, "username": "sheepie0"}
        ]

        # Define a date range (e.g., the past 10 days)
        start_date = datetime.date.today() - datetime.timedelta(days=10)
        end_date = datetime.date.today()

        # Insert dummy data: for each user, the playtime increases cumulatively over the days.
        for user in users:
            cumulative_playtime = 0.0
            current_date = start_date
            while current_date <= end_date:
                # Generate a random increment between 1.0 and 5.0 hours
                increment = round(random.uniform(1.0, 5.0), 2)
                cumulative_playtime += increment
                date_str = current_date.strftime("%Y-%m-%d")
                await db.execute(
                    "INSERT INTO playtime (user_id, username, playtime, date) VALUES (?, ?, ?, ?)",
                    (user["id"], user["username"], cumulative_playtime, date_str)
                )
                current_date += datetime.timedelta(days=1)
            # Insert a dummy goal for the user: random goal between 30 and 50 hours
            dummy_goal = round(random.uniform(30.0, 50.0), 2)
            await db.execute(
                "INSERT OR REPLACE INTO goals (user_id, goal) VALUES (?, ?)",
                (user["id"], dummy_goal)
            )
        await db.commit()

    print("Dummy data and goals inserted successfully.")

if __name__ == '__main__':
    asyncio.run(main())
