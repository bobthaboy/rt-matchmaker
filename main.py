from utility import cmd_log
from discord.ext import commands
import asyncio
from bot_config import bot
import achievement_commands  # noqa
import match_commands  # noqa
import profile  # noqa
import testing  # noqa
import misc  # noqa
import first_place_commands  # noqa


@bot.event
async def on_ready() -> None:
    cmd_log("Matchmaker is running!")
    first_place_commands.look_for_new.start()


@bot.event
async def on_command_error(ctx, error) -> None:
    match error:
        case commands.CommandNotFound():
            pass
        case commands.MemberNotFound():
            pass
        case commands.MissingRequiredArgument():
            pass
        case commands.CommandOnCooldown():
            message = await ctx.reply(
                f"You're on cooldown. Try again in {int(error.retry_after / 60) + 1} minute(s)."
            )
            await asyncio.sleep(5)
            await message.delete()


with open("data/token.txt", "r") as f:
    token = f.read()

bot.run(token)
