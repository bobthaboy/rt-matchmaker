import json
from discord.ext import commands
import asyncio
from match_commands import active_matches, cleanup_match
from bot_config import bot
from RhythmTyperAPI.client import RhythmTyperClient

rt = RhythmTyperClient()

with open("data/users.json", "r") as f:
    users: dict = json.load(f)


@bot.command(name="pair", aliases=["register"])
async def pair(ctx, url: str | None = None, arg: str | None = None) -> None:
    bob = await bot.fetch_user(266086182650118144)

    if ctx.author == bob:
        users[url] = arg

        with open("data/users.json", "w") as f:
            json.dump(users, f, indent=4)

        await ctx.reply("Donezo.")
        return

    user = users.get(str(ctx.author.id))
    if user:
        await ctx.reply("You are paired to an account.")
        return

    if not url:
        await ctx.reply("can you pls post your profile link after the command ty")
        return

    user_id = url.rsplit("/", 1)[-1]
    await ctx.send(f"now we wait for {bob.mention} to run this command.\n"
                   f"`!pair {ctx.author.id} {user_id}`")


@bot.command(name="vouch", aliases=["submit"])
async def vouch(ctx, *args) -> None:
    user_id = str(ctx.author.id)
    user = users.get(user_id)

    if not user:
        await ctx.reply("Sorry, only players in the system may submit maps. Try `!pair`.")
        return

    if not args:
        await ctx.reply("Try `!vouch <map_url>`.")
        return

    with open("data/vouched.json", "r") as f:
        vouched = json.load(f)

    with open("data/maps.json", "r") as f:
        beatmaps: list[dict] = json.load(f)

    bids = set()
    for beatmap in beatmaps:
        bids.add(beatmap["beatmap_id"])

    for url in args:
        map_id = url.rsplit("/", 1)[-1]

        if map_id in bids:
            await ctx.reply("This map is already featured.")
            return

        if map_id not in vouched:
            beatmap = rt.get_beatmap(map_id)
            await asyncio.sleep(1)
            title = f"{beatmap.beatmap_artist} - {beatmap.beatmap_title} ({beatmap.mapper})"

            vouched[map_id] = {
                "votes": [],
                "title": title
            }

        user_list = vouched[map_id]["votes"]

        if ctx.author.id in user_list:
            await ctx.reply("You've already vouched for this map.")
            return

        user_list.append(ctx.author.id)

    with open("data/vouched.json", "w") as f:
        json.dump(vouched, f, indent=4)

    await ctx.message.add_reaction("👍")


@bot.command(name="vouched", aliases=["submitted"])
async def vouched_list(ctx, page: int = 1):
    if page < 1:
        return

    with open("data/vouched.json", "r") as f:
        vouched = json.load(f)

    vouched = dict(
        sorted(vouched.items(), key=lambda item: len(item[1]["votes"]), reverse=True)
    )

    cursor = (page - 1) * 10
    vouched = dict(list(vouched.items())[cursor:cursor + 10])

    message = ""
    for beatmap_id, data in vouched.items():
        votes = len(data["votes"])
        message += f"{votes}: [{data['title']}](https://rhythmtyper.net/beatmap/{beatmap_id})\n"

    await ctx.reply(message, suppress_embeds=True)


@bot.command(name="matches")
async def matches_log(ctx, *args) -> None:
    args = [arg for arg in args]
    player1 = ctx.author
    player2 = None
    page = 1

    if len(args) > 3:
        return

    converter = commands.MemberConverter()
    if len(args) == 3:
        try:
            page = int(args[-1])
            player1 = await converter.convert(ctx, args[0])
            player2 = await converter.convert(ctx, args[1])
        except ValueError:
            return
        except commands.MemberNotFound:
            return

    if len(args) == 2:
        try:
            page = int(args[-1])
            player2 = await converter.convert(ctx, args[0])
        except ValueError:
            try:
                player1 = await converter.convert(ctx, args[0])
                player2 = await converter.convert(ctx, args[1])
            except commands.MemberNotFound:
                return
        except commands.MemberNotFound:
            return

    if len(args) == 1:
        try:
            page = int(args[0])
        except ValueError:
            try:
                player2 = await converter.convert(ctx, args[0])
            except commands.MemberNotFound:
                return

    if len(args) == 0 or not player2:
        await ctx.reply("I need a user to compare against.")
        return

    if page < 1:
        return

    with open("data/logs.json", "r") as f:
        user_logs = json.load(f)

    ids = [player1.id, player2.id]
    user_logs = [log for log in user_logs if log["winner"]["id"] in ids and log["loser"]["id"] in ids]
    user_logs.reverse()

    cursor = (page - 1) * 10
    short_logs = user_logs[cursor:cursor + 10]

    if not user_logs:
        await ctx.reply("No matches found.")
        return

    wins = len([log for log in user_logs if log["winner"]["id"] == player1.id])
    message = (f"{player1.name} vs {player2.name}\n"
               f"({len(user_logs)} Matches) [{wins}W:{len(user_logs) - wins}L]\n")

    for i, log in enumerate(short_logs, start=1):
        date = log["timestamp"][:10]
        winner = log["winner"]
        loser = log["loser"]

        if winner["id"] == player1.id:
            result = "Win"
            change = int(winner["new_rating"] - winner["old_rating"])
            change = f"+{change}"
            player1_usr = f"**{player1.name} ({int(winner['old_rating'])})**"
            player2_usr = f"{player2.name} ({int(loser['old_rating'])})"
            order = f"{player1_usr} - {player2_usr}"
        else:
            result = "Loss"
            change = int(loser["new_rating"] - loser["old_rating"])
            player1_usr = f"**{player1.name} ({int(loser['old_rating'])})**"
            player2_usr = f"{player2.name} ({int(winner['old_rating'])})"
            order = f"{player2_usr} - {player1_usr}"

        message += f"{i + cursor}. [{date}] {order} **{result}** ({change})\n"

    await ctx.reply(message)


@bot.command(name="history")
async def history_log(ctx, *args) -> None:
    args = [arg for arg in args]
    page = 1
    user = ctx.author
    if len(args) > 2:
        return

    if len(args) == 2:
        try:
            page = int(args[1])
        except ValueError:
            return

    if len(args) == 1:
        try:
            page = int(args[0])
        except ValueError:
            converter = commands.MemberConverter()
            try:
                user = await converter.convert(ctx, args[0])
            except commands.MemberNotFound:
                return

    if page < 1:
        return

    with open("data/logs.json", "r") as f:
        user_logs = json.load(f)

    user_logs = [log for log in user_logs if log["winner"]["id"] == user.id or log["loser"]["id"] == user.id]
    user_logs.reverse()
    if not user_logs:
        await ctx.reply("No matches found.")
        return

    cursor = (page - 1) * 10
    user_logs = user_logs[cursor:cursor + 10]

    message = ""
    players = {}
    for i, log in enumerate(user_logs, start=1):
        date = log["timestamp"][:10]
        winner = log["winner"]
        loser = log["loser"]

        if winner["id"] == user.id:
            opponent = loser
            result = "Win"
            change = int(winner["new_rating"] - winner["old_rating"])
            change = f"+{change}"
        else:
            opponent = winner
            result = "Loss"
            change = int(loser["new_rating"] - loser["old_rating"])

        if not players.get(opponent["id"]):
            players[opponent["id"]] = await bot.fetch_user(opponent["id"])

        message += (f"{i + cursor}. [{date}] **{result}** [{change}] - "
                    f"{players[opponent['id']].name} ({int(opponent['old_rating'])})\n")

    await ctx.reply(message)


@bot.command(name="help", aliases=["command", "commands"])
async def command_list(ctx, command=None) -> None:
    all_commands = {"match": "`!match *@user [flag]`\n"
                             "Challenges user to a ranked match.\n"
                             "Default flag is NM & DT.\n"
                             "Accepted flags:\n"
                             "'nm' -> NM\n"
                             "'ht' -> NM & HT\n"
                             "'htdt' -> NM, HT, & DT",
                    "casual": "`!casual *@user [flag]`\n"
                              "Challenges user to an unranked match.\n"
                              "Default flag is NM & DT.\n"
                              "Accepted flags:\n"
                              "'nm' -> NM\n"
                              "'ht' -> NM & HT\n"
                              "'htdt' -> NM, HT, & DT",
                    "forfeit": "`!forfeit`\n"
                               "Lose the match.",
                    "cancel": "`!cancel`\n"
                              "Exit your current running command match.",
                    "queue": "`!queue [flag]`\n"
                             "Ping users within 100 elo for a ranked match.\n"
                             "Default flag is NM & DT.\n"
                             "Accepted flags:\n"
                             "'nm' -> NM\n"
                             "'ht' -> NM & HT\n",
                    "profile": "`!profile [@user]`"
                               "Shows various user stats.",
                    "lb": "`!lb [page]`\n"
                          "Shows everyone's rank and elo.",
                    "echo": "`!echo`\n"
                            "Toggles whether you are pinged for !queue.",
                    "pair": "`!pair *profile_url`\n"
                            "Connects your Discord account to your RT account.",
                    "vouch": "`!vouch *beatmap_url [beatmap_url...]`\n"
                             "Vote for unranked map(s) to appear in draft.",
                    "history": "\n"
                               "`!history [@user] [page]`\n"
                               "Shows the history of your own or user's matches.",
                    "matches": "`!matches *@user1 [@user2] [page]`\n"
                               "Shows the history between you and another or two users.",
                    "vouched": "`!vouched [page]`\n"
                               "Shows a list of all voted maps.",
                    "achievements": "`!achievements [@user]`\n"
                                    "Shows all of your or a user's achievements.",
                    "titles": "`!titles [@user] or [title #]`\n"
                              "See a list of your or a user's titles, or set your own title.",
                    "unique": "`!unique [page]`\n"
                              "Shows a leaderboard for unique first place scores.",
                    "targets": "`!targets [page]`\n"
                               "Shows all unique first places scores sorted by oldest."
                    }

    if not command:
        message = "Please type `!help [command]` for the specific command you want to learn about.\n\n"
        message += ", ".join(sorted(all_commands.keys()))
        await ctx.reply(message)
        return

    if command.lower() not in all_commands:
        await ctx.reply("I do not see this command. If this is a mistake, ping Bob.")
        return

    await ctx.reply(all_commands[command.lower()])


@bot.command(name="cancel", aliases=["abort", "quit", "stop"])
async def cancel_action(ctx) -> None:
    cur_match: tuple | None = active_matches.get(ctx.author.id)

    if cur_match is None:
        await ctx.reply("You aren't currently in a match.")
        return

    opponent, state, task = cur_match

    if not opponent:
        cleanup_match(ctx.author)
        await ctx.reply("Command canceled.")
        task.cancel()
        return

    if not state:
        cleanup_match(ctx.author, opponent)
        await ctx.reply("Command canceled.")
        task.cancel()
        return

    message = await ctx.send(
        f"{opponent.mention}, would you like to cancel the match with {ctx.author.name}?\n"
        "(No elo will be traded between this match.)"
    )

    await message.add_reaction("✅")
    await message.add_reaction("❌")

    def check(reaction, member):
        return (
                member == opponent
                and reaction.message.id == message.id
                and str(reaction.emoji) in ["✅", "❌"]
        )

    try:
        reaction, member = await bot.wait_for(
            "reaction_add",
            timeout=300.0,
            check=check
        )

        if str(reaction.emoji) == "❌":
            await ctx.reply(
                f"❌ Cancellation declined!"
            )
            return

    except asyncio.TimeoutError:
        await ctx.reply(
            f"⌛ User failed to respond in time."
        )
        return

    task.cancel()

    await ctx.send(
        f"The match between {ctx.author.mention} and {opponent.mention} has been canceled."
    )

    cleanup_match(ctx.author, opponent)


@bot.command(name="echo", aliases=["role"])
async def echo_role(ctx) -> None:
    role = ctx.guild.get_role(1535766560491442206)

    if role in ctx.author.roles:
        await ctx.reply("Removed you from the queue finder.")
        await ctx.author.remove_roles(role)
    else:
        user = users.get(str(ctx.author.id))
        if user:
            await ctx.reply("Added you to the queue finder.")
        else:
            await ctx.reply(f"Added you to the queue finder.\n\n"
                            "Hey, and, by the way, you're not actually linked so the queue wouldn't work anyway.\n"
                            "Run the `!pair` command!")
        await ctx.author.add_roles(role)
