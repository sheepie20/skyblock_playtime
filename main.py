import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
import matplotlib.pyplot as plt
import io
import datetime
from matplotlib.dates import DateFormatter
from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Connect to (or create) the SQLite database
conn = sqlite3.connect('playtime.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS playtime (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        playtime REAL,
        date TEXT
    )
''')
conn.commit()

@app_commands.command(name="submit", description="Submit your playtime for a given date")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(playtime="Playtime (as a float)", date="Date in format YYYY-MM-DD (optional)")
async def submit(interaction: discord.Interaction, playtime: float, date: str = None):
    # Use today's date if no date is provided
    if date is None:
        date = datetime.date.today().strftime("%Y-%m-%d")
    else:
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            await interaction.response.send_message("Date must be in format YYYY-MM-DD", ephemeral=True)
            return

    user_id = interaction.user.id
    username = interaction.user.name

    cursor.execute("INSERT INTO playtime (user_id, username, playtime, date) VALUES (?, ?, ?, ?)",
                   (user_id, username, playtime, date))
    conn.commit()

    await interaction.response.send_message(f"Playtime of {playtime} submitted for {username} on {date}.")

@app_commands.command(name="graph", description="Generate a line chart of total playtime aggregated by date")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def graph(interaction: discord.Interaction):
    # Retrieve aggregated playtime data for all dates (across all users)
    cursor.execute("SELECT date, SUM(playtime) FROM playtime GROUP BY date ORDER BY date")
    rows = cursor.fetchall()

    if not rows:
        await interaction.response.send_message("No playtime data available.", ephemeral=True)
        return

    # Separate dates and total playtime, converting dates to datetime objects
    dates = [datetime.datetime.strptime(row[0], "%Y-%m-%d") for row in rows]
    total_playtimes = [row[1] for row in rows]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, total_playtimes, marker='o', linestyle='-', color='blue')
    plt.xlabel("Date")
    plt.ylabel("Total Playtime (hours)")
    plt.title("Total Playtime by Date")
    plt.grid(True)
    plt.tight_layout()

    # Format the x-axis dates in "day abbreviated_month, year" format (e.g., "02 Nov, 2022")
    ax = plt.gca()
    ax.xaxis.set_major_formatter(DateFormatter('%d %b, %Y'))

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    file = discord.File(fp=buf, filename="graph.png")
    await interaction.response.send_message(file=file)

@app_commands.command(name="compare", description="Compare playtime between two users over time")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(user1="First user to compare", user2="Second user to compare")
async def compare(interaction: discord.Interaction, user1: discord.User, user2: discord.User):
    # Retrieve aggregated playtime for user1 by date
    cursor.execute("SELECT date, SUM(playtime) FROM playtime WHERE user_id = ? GROUP BY date", (user1.id,))
    rows1 = cursor.fetchall()

    # Retrieve aggregated playtime for user2 by date
    cursor.execute("SELECT date, SUM(playtime) FROM playtime WHERE user_id = ? GROUP BY date", (user2.id,))
    rows2 = cursor.fetchall()

    if not rows1 and not rows2:
        await interaction.response.send_message("No playtime data available for either user.", ephemeral=True)
        return

    # Create dictionaries for easy lookup: date -> playtime
    data1 = {row[0]: row[1] for row in rows1}
    data2 = {row[0]: row[1] for row in rows2}

    # Create a union of all dates and sort them
    all_dates_str = sorted(set(data1.keys()).union(set(data2.keys())))
    # Convert date strings to datetime objects for plotting
    all_dates = [datetime.datetime.strptime(date_str, "%Y-%m-%d") for date_str in all_dates_str]

    # For each date, get the playtime or default to 0 if no data exists
    playtimes1 = [data1.get(date_str, 0) for date_str in all_dates_str]
    playtimes2 = [data2.get(date_str, 0) for date_str in all_dates_str]

    plt.figure(figsize=(10, 5))
    plt.plot(all_dates, playtimes1, marker='o', linestyle='-', label=user1.name)
    plt.plot(all_dates, playtimes2, marker='o', linestyle='-', label=user2.name)
    plt.xlabel("Date")
    plt.ylabel("Total Playtime")
    plt.title("Playtime Comparison Over Time")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Format the x-axis dates for clarity
    ax = plt.gca()
    ax.xaxis.set_major_formatter(DateFormatter('%d %b, %Y'))

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    file = discord.File(fp=buf, filename="compare.png")
    await interaction.response.send_message(file=file)

@bot.event
async def on_ready():
    # Register the slash commands with the bot's command tree and sync with Discord
    bot.tree.add_command(submit)
    bot.tree.add_command(graph)
    bot.tree.add_command(compare)
    await bot.tree.sync()
    print(f"Logged in as {bot.user} and slash commands have been synced.")

bot.run(os.getenv("token"))
