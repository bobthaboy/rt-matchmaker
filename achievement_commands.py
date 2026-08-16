import json
from RhythmTyperAPI.models import Play
from time import monotonic
from discord import Member
from discord.ext import commands
from collections import Counter
from models import MatchState
from utility import get_play_score, is_fc
from profile_commands import get_user_rank, user_profile_ui, achievements
from bot_config import bot


def achievement_qualified(user: Member, target: Member, casual: bool) -> dict:
    user_wins = 0
    target_wins = 0
    play_counts = Counter()

    with open("data/logs.json", "r") as f:
        logs = json.load(f)

    for log in logs:
        skill_range = abs(log["winner"]["old_rating"] - log["loser"]["old_rating"]) <= 100
        ten_plays = play_counts[log["loser"]["id"]] >= 10
        worthy_opponent = skill_range and ten_plays

        if log["winner"]["id"] == user.id and worthy_opponent:
            user_wins += 1

        if log["winner"]["id"] == target.id and worthy_opponent:
            target_wins += 1

        play_counts[log["winner"]["id"]] += 1
        play_counts[log["loser"]["id"]] += 1

    user_play_count = play_counts[user.id]
    target_play_count = play_counts[target.id]

    with open("data/elo.json", "r") as f:
        elo = json.load(f)

    user_elo = elo.setdefault(str(user.id), 1000)
    target_elo = elo.setdefault(str(target.id), 1000)

    skill_range = abs(user_elo - target_elo) <= 100

    qualified = user_play_count >= 10 and target_play_count >= 10 and not casual and skill_range
    qualified_dict = {"qualified": qualified,
                      "player1_wins": user_wins,
                      "player2_wins": target_wins}
    return qualified_dict


# idk what type "thread" is
async def achievements_check(ctx, user: Member, thread, play: Play, play2: Play, hp: int, hp2: int,
                             max_notes: int, state: MatchState, wins: int) -> None:
    new_chievos = []
    score = get_play_score(play)
    score2 = get_play_score(play2)

    if is_fc(play, max_notes) == " **Perfect!**":
        new_chievos.append(1)

    if hp == 1_000_000 and hp2 <= 0:
        new_chievos.append(2)

    if hp < 100_000 and hp2 <= 0:
        new_chievos.append(3)

    if 0 < hp < 10_000:
        new_chievos.append(4)

    if state.turn > 10:
        new_chievos.append(5)

    if is_fc(play, max_notes) != "" and is_fc(play2, max_notes) == "" and user != state.chooser:
        new_chievos.append(6)

    if state.chooser != user and hp2 <= 0:
        new_chievos.append(7)

    if wins == 49 and hp2 <= 0:
        new_chievos.append(8)

    if hp2 <= -500_000:
        new_chievos.append(9)

    if monotonic() <= state.start_time + 20 * 60 and hp2 <= 0:
        new_chievos.append(10)

    if (score - score2) >= 250_000:
        new_chievos.append(11)

    if "777" in str(score):
        new_chievos.append(12)

    if (score - score2) <= 20_000 and hp2 <= 0:
        new_chievos.append(13)

    if score == score2:
        new_chievos.append(14)

    if not new_chievos:
        return

    with open("data/achievements.json", "r") as f:
        chievo_data = json.load(f)

    user_chievos = chievo_data.get(str(user.id), [])

    for chievo in new_chievos:
        if chievo in user_chievos:
            continue

        message = (f"# Achievement Get!\n"
                   f"**{achievements[chievo]['icon']} {achievements[chievo]['name']}\n**"
                   f"\n"
                   f"{user.mention}")
        await thread.send(message)

        user_chievos.append(chievo)

    chievo_data[str(user.id)] = user_chievos

    with open("data/achievements.json", "w") as f:
        json.dump(chievo_data, f, indent=4)


@bot.command(name="achievements", aliases=["achievement"])
async def achievements_list(ctx, other: Member | None = None) -> None:
    with open("data/achievements.json", "r") as f:
        chievo_data = json.load(f)

    user = other or ctx.author
    user_chievos = chievo_data.get(str(user.id))

    if user_chievos is None:
        user_chievos = []

    description = ""
    locked = []
    for chievo_id, achievement in achievements.items():
        if chievo_id in user_chievos:
            description += f"**{achievement['icon']} {achievement['name']}:** {achievement['description']}\n"
        else:
            locked.append(chievo_id)

    if locked:
        description += f"\n\nLocked Achievements:\n"
        for chievo in locked:
            description += f"**🔒 {achievements[chievo]['name']}:** ???\n"

    rank, _ = get_user_rank(user)
    embed = user_profile_ui(user, description, rank)

    embed.set_footer(text=f"{len(user_chievos)}/{len(achievements)} Achievements collected.")

    await ctx.send(embed=embed)


@bot.command(name="titles", aliases=["title"])
async def titles_list(ctx, arg=None) -> None:
    user = ctx.author
    cursor = None

    if arg:
        try:
            cursor = int(arg)
            if cursor < 1:
                return

        except ValueError:
            converter = commands.MemberConverter()
            try:
                user = await converter.convert(ctx, arg)
            except commands.MemberNotFound:
                return

    with open("data/achievements.json", "r") as f:
        chievo_data = json.load(f)

    user_chievos = chievo_data.get(str(user.id))

    if user_chievos:
        user_titles = sorted({
            achievements[chievo]["title"]
            for chievo in user_chievos
            if achievements[chievo]["title"]
        })
    else:
        user_titles = []

    if not cursor:
        if not user_titles:
            if user == ctx.author:
                description = "You don't have any titles."
            else:
                description = f"{user.name} doesn't have any titles."
        else:
            description = f"Available Titles:\n"
            for i, title in enumerate(user_titles, start=1):
                description += f"{i}. {title}"

        rank, _ = get_user_rank(user)
        embed = user_profile_ui(user, description, rank)

        all_titles = {
            achievement["title"]
            for achievement in achievements.values()
            if achievement["title"]
        }

        embed.set_footer(text=f"{len(user_titles)}/{len(all_titles)} Titles collected.")

        await ctx.send(embed=embed)
        return

    if not user_titles:
        await ctx.reply("You don't have any titles.")
        return

    try:
        selected_title = user_titles[cursor - 1]
    except IndexError:
        return

    with open("data/titles.json", "r") as f:
        titles_data = json.load(f)

    titles_data[str(ctx.author.id)] = selected_title

    await ctx.reply(f"Successfully set your title to The {selected_title}!")

    with open("data/titles.json", "w") as f:
        json.dump(titles_data, f, indent=4)
