import discord
from discord.ext import commands, tasks
import aiosqlite
import datetime

DATABASE = 'playtime.db'

class GoalChecker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_goals.start()

    def cog_unload(self):
        self.check_goals.cancel()

    @tasks.loop(minutes=.01) 
    async def check_goals(self):
        today = datetime.date.today().strftime("%Y-%m-%d")
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT user_id, goal FROM goals") as cursor:
                goals = await cursor.fetchall()

            for user_id, goal in goals:
                async with db.execute(
                    "SELECT SUM(playtime) FROM playtime WHERE user_id = ? AND date = ?",
                    (user_id, today)
                ) as cursor:
                    row = await cursor.fetchone()
                total_playtime = row[0] if row and row[0] is not None else 0

                if total_playtime >= goal:
                    user = self.bot.get_user(user_id)
                    if user is None:
                        try:
                            user = await self.bot.fetch_user(user_id)
                        except Exception as e:
                            print(f"Failed to fetch user {user_id}: {e}")
                            continue

                    try:
                        await user.send(
                            f"Congratulations! You've reached your daily playtime goal of {goal} hours today "
                            f"with a total of {total_playtime:.2f} hours. Your goal has been cleared. Set a new one with `/setgoal` if you'd like!"
                        )
                    except Exception as e:
                        print(f"Failed to DM user {user_id}: {e}")

                    await db.execute("DELETE FROM goals WHERE user_id = ?", (user_id,))
            await db.commit()

    @check_goals.before_loop
    async def before_check_goals(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(GoalChecker(bot))
