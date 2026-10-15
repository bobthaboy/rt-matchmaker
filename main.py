from utility import cmd_log, andrew_resolve  # noqa
from discord.ext import commands
import asyncio
from bot_config import bot
import achievement_commands  # noqa
import match_commands  # noqa
import profile_commands  # noqa
import testing  # noqa
import misc  # noqa
import first_place_commands  # noqa


@bot.event
async def on_ready() -> None:
    cmd_log("Matchmaker is running!")
    if not first_place_commands.look_for_new.is_running():
        first_place_commands.look_for_new.start()
    channel = await bot.fetch_channel(1479928319947313162)
    await channel.send("Matchmaker online!")


@bot.event
async def on_message(ctx) -> None:
    # bobs_house = 1549352620114706483
    # mushroom = 1450490814764679392
    #
    # if ctx.channel.id == bobs_house and ctx.author.id == mushroom:
    #     await ctx.delete()
    #     return

    await andrew_resolve(ctx)
    await bot.process_commands(ctx)


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


async def cleanup():
    channel = await bot.fetch_channel(1479928319947313162)
    await channel.send("Bot going down.")
    print("Finished")
    await bot.close()


async def main():
    try:
        await bot.start(token)
    finally:
        await cleanup()


asyncio.run(main())
