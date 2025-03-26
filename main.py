import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite
import os
import csv
import pretty_help
import matplotlib.pyplot as plt
import io
import datetime
from matplotlib.dates import DateFormatter
from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.all()
status = discord.Status.idle

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    status=status,
    help_command=pretty_help.PrettyHelp(typing=False)
)

DATABASE = "playtime.db"

async def initialize_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS playtime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                playtime REAL,
                date TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                user_id INTEGER PRIMARY KEY,
                goal REAL
            )
        ''')
        await db.commit()

@app_commands.command(name="setgoal", description="Set your daily playtime goal (in hours)")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(goal="Your playtime goal (as a float, in hours)")
async def setgoal(interaction: discord.Interaction, goal: float):
    await interaction.response.defer()
    user_id = interaction.user.id

    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("INSERT INTO goals (user_id, goal) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET goal = ?",
                         (user_id, goal, goal))
        await db.commit()

    await interaction.followup.send(f"🎯 Playtime goal set to **{goal} hours**!")

@app_commands.command(name="remindme", description="Check if you've met your playtime goal today")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def remindme(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = interaction.user.id
    date_today = datetime.date.today().strftime("%Y-%m-%d")

    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT goal FROM goals WHERE user_id = ?", (user_id,))
        goal_row = await cursor.fetchone()

    if not goal_row:
        await interaction.followup.send("⚠️ You haven't set a playtime goal yet. Use `/setgoal` first!", )
        return

    goal = goal_row[0]

    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT SUM(playtime) FROM playtime WHERE user_id = ? AND date = ?", (user_id, date_today))
        playtime_row = await cursor.fetchone()
        total_playtime = playtime_row[0] if playtime_row[0] else 0

    if total_playtime >= goal:
        await interaction.followup.send(f"✅ You've reached your playtime goal of **{goal} hours** today! Great job! 🎉")
    else:
        remaining = goal - total_playtime
        await interaction.followup.send(f"⏳ You still need **{remaining:.2f} more hours** to reach your goal today. Keep going! 💪")

@app_commands.command(name="streak", description="Check your current playtime streak")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def streak(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = interaction.user.id

    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT DISTINCT date FROM playtime WHERE user_id = ? ORDER BY date DESC", (user_id,))
        rows = await cursor.fetchall()

    if not rows:
        await interaction.followup.send("You haven't submitted any playtime yet.", )
        return

    dates = [datetime.datetime.strptime(row[0], "%Y-%m-%d") for row in rows]

    streak_count = 1
    for i in range(len(dates) - 1):
        if (dates[i] - dates[i + 1]).days == 1:
            streak_count += 1
        else:
            break   

    await interaction.followup.send(f"🔥 {interaction.user.name}, your current playtime streak is **{streak_count} days**!")


@app_commands.command(name="submit", description="Submit your playtime for a given date")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(playtime="Playtime (in hours)", date="Date in format YYYY-MM-DD")
async def submit(interaction: discord.Interaction, playtime: float, date: str = None):
    await interaction.response.defer()
    if date is None:
        date = datetime.date.today().strftime("%Y-%m-%d")
    else:
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            await interaction.followup.send("Date must be in format YYYY-MM-DD", )
            return

    user_id = interaction.user.id
    username = interaction.user.name

    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("INSERT INTO playtime (user_id, username, playtime, date) VALUES (?, ?, ?, ?)",
                         (user_id, username, playtime, date))
        await db.commit()

    await interaction.followup.send(f"Playtime of {playtime} submitted for {username} on {date}.")

@app_commands.command(name="graph", description="Generate a line chart of total playtime aggregated by date")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    user="User to show playtime for (defaults to yourself). If omitted entirely, shows ALL users combined."
)
async def graph(interaction: discord.Interaction, user: discord.User = None):
    await interaction.response.defer()
    async with aiosqlite.connect(DATABASE) as db:
        if isinstance(user, discord.User):
            cursor = await db.execute(
                """SELECT date, SUM(playtime)
                       FROM playtime
                       WHERE user_id = ?
                       GROUP BY date
                       ORDER BY date""", (user.id,)
            )
        else:
            cursor = await db.execute(
                """SELECT date, SUM(playtime)
                       FROM playtime
                       GROUP BY date
                       ORDER BY date"""
            )
        rows = await cursor.fetchall()

    if not rows:
        await interaction.followup.send(
            "No playtime data available.", 
        )
        return

    dates = [datetime.datetime.strptime(row[0], "%Y-%m-%d") for row in rows]
    total_playtimes = [row[1] for row in rows]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, total_playtimes, marker='o', linestyle='-',
             color='blue', label=f"{user.name if isinstance(user, discord.User) else 'All Users'}")
    plt.xlabel("Date")
    plt.ylabel("Total Playtime (hours)")
    plt.title("Total Playtime by Date")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    ax = plt.gca()
    ax.xaxis.set_major_formatter(DateFormatter('%d %b, %Y'))

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    file = discord.File(fp=buf, filename="graph.png")
    await interaction.followup.send(file=file)

@app_commands.command(name="compare", description="Compare playtime between two users over time")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(user1="First user to compare", user2="Second user to compare")
async def compare(interaction: discord.Interaction, user1: discord.User, user2: discord.User):
    await interaction.response.defer()
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT date, SUM(playtime) FROM playtime WHERE user_id = ? GROUP BY date", (user1.id,))
        rows1 = await cursor.fetchall()

    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT date, SUM(playtime) FROM playtime WHERE user_id = ? GROUP BY date", (user2.id,))
        rows2 = await cursor.fetchall()

    if not rows1 and not rows2:
        await interaction.response.send_message("No playtime data available for either user.", )
        return

    data1 = {row[0]: row[1] for row in rows1}
    data2 = {row[0]: row[1] for row in rows2}

    all_dates_str = sorted(set(data1.keys()).union(set(data2.keys())))
    all_dates = [datetime.datetime.strptime(date_str, "%Y-%m-%d") for date_str in all_dates_str]

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

    ax = plt.gca()
    ax.xaxis.set_major_formatter(DateFormatter('%d %b, %Y'))

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    file = discord.File(fp=buf, filename="compare.png")
    await interaction.followup.send(file=file)

@app_commands.command(name="leaderboard", description="Show the top users with the most playtime")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(limit="Number of users to display (default: 10)")
async def leaderboard(interaction: discord.Interaction, limit: int = 10):
    await interaction.response.defer()
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT username, SUM(playtime) FROM playtime GROUP BY user_id ORDER BY SUM(playtime) DESC LIMIT ?", (limit,))
        rows = await cursor.fetchall()

    if not rows:
        await interaction.followup.send("No playtime data available.", )
        return

    leaderboard_message = "**🏆 Playtime Leaderboard 🏆**\n"
    for i, (username, total_playtime) in enumerate(rows, start=1):
        leaderboard_message += f"**{i}. {username}** - {total_playtime:.2f} hours\n"

    await interaction.followup.send(leaderboard_message)


@app_commands.command(name="exportdata", description="Download your playtime data as a CSV file")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(user="User to export data for (default: yourself)")
async def exportdata(interaction: discord.Interaction, user: discord.User = None):
    await interaction.response.defer()
    user_id = interaction.user.id
    if user:
        user_id = user.id
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT date, playtime FROM playtime WHERE user_id = ? ORDER BY date", (user_id,)) as cursor:
            rows = await cursor.fetchall()
    
    if not rows:
        await interaction.followup.send("No playtime data available to export.", )
        return
    
    filename = f"playtime_{user_id}.csv"
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Date", "Playtime (hours)"])
        writer.writerows(rows)
    
    await interaction.followup.send(file=discord.File(filename))
    os.remove(filename)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.CustomActivity(name='go outside.'))
    await initialize_db()
    bot.tree.add_command(submit)
    bot.tree.add_command(graph)
    bot.tree.add_command(compare)
    bot.tree.add_command(exportdata)
    bot.tree.add_command(streak)
    bot.tree.add_command(setgoal)
    bot.tree.add_command(remindme)
    await bot.tree.sync()
    await bot.load_extension("cogs.goal_checker")
    print(f"Logged in as {bot.user} and slash commands have been synced.")

bot.run(os.getenv("token"))
