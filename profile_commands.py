import json
from bot_config import bot
from discord import Member, Embed, Color
from datetime import datetime, timedelta
from collections import Counter

achievements = {
    1: {"icon": "🌟", "name": "Shooting Star", "title": "Consistent",
        "description": "Achieve an SS on any map."},
    2: {"icon": "💎", "name": "Flawless Victory", "title": "Untouchable",
        "description": "Win a match without ever taking damage."},
    3: {"icon": "🦷", "name": "Skin of Your Teeth", "title": "Enduring",
        "description": "Go below 100,000 HP and win."},
    4: {"icon": "🩸", "name": "Punk's Not Dead", "title": "Enduring",
        "description": "Drop below 10,000 HP without dying."},
    5: {"icon": "⏱️", "name": "Overtime", "title": None,
        "description": "Make it past round 10."},
    6: {"icon": "👁️", "name": "You Are Not Prepared", "title": "Consistent",
        "description": "FC an opponent's pick when they don't."},
    7: {"icon": "🧠", "name": "Know Your Enemy", "title": None,
        "description": "Win a match off your opponent's pick."},
    8: {"icon": "⚔️", "name": "Art of War", "title": "Truly Worthy",
        "description": "Reach 50 wins against worthy opponents."},
    9: {"icon": "💥", "name": "Overkill", "title": "Mighty",
        "description": "Overkill your opponent by 500,000 HP."},
    10: {"icon": "⚡", "name": "Gotta Go Fast", "title": "Quick",
         "description": "Defeat your opponent in under 20 minutes."},
    11: {"icon": "🗿", "name": "Not Even Close", "title": "Mighty",
         "description": "Gap your opponent's score by at least 250,000."},
    12: {"icon": "🎰", "name": "RNGdle", "title": None,
         "description": "Have a \"777\" appear anywhere within your score."},
    13: {"icon": "📌", "name": "Pinprick", "title": None,
         "description": "Deal the final blow with a score difference of 20,000 or less."},
    14: {"icon": "⚖️", "name": "Perfectly Balanced", "title": None,
         "description": "Get the exact same score as your opponent."}
}


def get_user_rank(user: Member) -> tuple[int | str, int]:
    with open("data/elo.json", "r") as f:
        elo: dict = json.load(f)

    user_elo = elo.setdefault(str(user.id), 1000)

    play_counts = Counter()

    with open("data/logs.json", "r") as f:
        logs = json.load(f)

    for log in logs:
        play_counts[log["winner"]["id"]] += 1
        play_counts[log["loser"]["id"]] += 1

    leaderboard = []
    for player, score in elo.items():
        if play_counts[int(player)] < 10:
            continue
        leaderboard.append((player, score))

    leaderboard.sort(key=lambda x: x[1], reverse=True)

    rank = "--"
    for i, player in enumerate(leaderboard, start=1):
        if player[0] == str(user.id):
            rank = i
            break

    return rank, user_elo


def get_user_elo_formatted(user: Member) -> int | str:
    rank, elo = get_user_rank(user)
    if isinstance(rank, int):
        elo = int(elo)
    else:
        elo = f"{int(elo)}?"
    return elo


def user_profile_ui(user: Member, description: str, rank: int | str) -> Embed:
    if rank == 1:
        color = Color.from_rgb(255, 215, 0)
        badge = "🥇"
    elif rank == 2:
        color = Color.from_rgb(192, 192, 192)
        badge = "🥈"
    elif rank == 3:
        color = Color.from_rgb(205, 127, 50)
        badge = "🥉"
    else:
        color = Color.from_rgb(88, 101, 242)
        badge = ""

    with open("data/titles.json", "r") as f:
        titles_data = json.load(f)

    title = titles_data.get(str(user.id))
    username = user.name
    if title:
        username = f"{user.name}, The {title}"

    embed = Embed(
        title=f"{username}'s Profile {badge}",
        description=description,
        color=color
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    return embed


@bot.command(name="lb", aliases=["top", "leaderboard"])
async def elo_lb(ctx, page: int = 1) -> None:
    if page < 1:
        return

    play_counts = Counter()

    with open("data/logs.json", "r") as f:
        logs = json.load(f)

    for log in logs:
        play_counts[log["winner"]["id"]] += 1
        play_counts[log["loser"]["id"]] += 1

    with open("data/elo.json", "r") as f:
        elo: dict = json.load(f)

    leaderboard = []
    for user, score in elo.items():
        if play_counts[int(user)] < 10:
            continue

        member = await bot.fetch_user(user)
        leaderboard.append((member, score))
    leaderboard.sort(key=lambda x: x[1], reverse=True)

    cursor = (page - 1) * 10
    leaderboard = leaderboard[cursor:cursor + 10]
    if not leaderboard:
        return
    message = ""
    for i, user in enumerate(leaderboard, start=1):
        message += f"{i + cursor}. {int(user[1])} - {user[0].name}\n"
    await ctx.reply(message)


@bot.command(name="profile", aliases=["stats"])
async def check_profile(ctx, target: Member | None = None) -> None:
    cur_user = ctx.author
    if target:
        cur_user = target

    if cur_user.bot:
        await ctx.reply("Dumbfuck.")
        return

    with open("data/logs.json", "r") as f:
        logs = json.load(f)

    wins = 0
    losses = 0
    recent_wins = 0
    recent_losses = 0
    streak = 0
    best_streak = 0
    reset_streak = False
    best_win = {"user": "N/A", "rating": 0}
    worst_loss = {"user": "N/A", "rating": 10000}

    play_counts = Counter()

    for i, log in enumerate(logs, start=1):
        date = datetime.fromisoformat(log["timestamp"])

        if log["winner"]["id"] == cur_user.id:
            wins += 1
            streak += 1
            if reset_streak:
                streak = 1
                reset_streak = False
            if datetime.now() - date <= timedelta(days=30):
                recent_wins += 1
                ten_plays = play_counts[log["loser"]["id"]] >= 10
                if log["loser"]["old_rating"] > best_win["rating"] and ten_plays:
                    opponent = await bot.fetch_user(log["loser"]["id"])
                    best_win["rating"] = int(log["loser"]["old_rating"])
                    best_win["user"] = opponent.name

        if log["loser"]["id"] == cur_user.id:
            losses += 1
            reset_streak = True
            if best_streak < streak:
                best_streak = streak
            streak = 0
            if datetime.now() - date <= timedelta(days=30):
                recent_losses += 1
                ten_plays = play_counts[log["winner"]["id"]] >= 10
                if log["winner"]["old_rating"] < worst_loss["rating"] and ten_plays:
                    opponent = await bot.fetch_user(log["winner"]["id"])
                    worst_loss["rating"] = int(log["winner"]["old_rating"])
                    worst_loss["user"] = opponent.name

        play_counts[log["winner"]["id"]] += 1
        play_counts[log["loser"]["id"]] += 1

    if not best_win["rating"]:
        best_win["rating"] = "--"
    if worst_loss["rating"] == 10000:
        worst_loss["rating"] = "--"
    if best_streak < streak:
        best_streak = streak

    all_matches = wins + losses
    recent_matches = recent_wins + recent_losses

    with open("data/achievements.json", "r") as f:
        chievo_data = json.load(f)

    user_chievos = chievo_data.get(str(cur_user.id))

    if not user_chievos:
        user_chievos = []

    chievo_message = "Achievements: "
    for chievo_id, achievement in achievements.items():
        if chievo_id in user_chievos:
            chievo_message += f"{achievement['icon']} "
        else:
            chievo_message += "🔒 "

    rank, user_elo = get_user_rank(cur_user)
    embed = user_profile_ui(cur_user, chievo_message, rank)

    embed.add_field(
        name="Elo",
        value=get_user_elo_formatted(cur_user),
        inline=True
    )

    embed.add_field(
        name="Rank",
        value=f"# {rank}",
        inline=True
    )

    embed.add_field(
        name="Total Matches",
        value=f"{all_matches}",
        inline=True
    )

    if recent_matches:
        value = f"{recent_wins}W:{recent_losses}L {int(recent_wins / (recent_wins + recent_losses) * 100)}%"
    else:
        value = "N/A"

    embed.add_field(
        name="Recent",
        value=value,
        inline=True
    )

    if all_matches:
        value = f"{wins}W:{losses}L {int(wins / all_matches * 100)}%"
    else:
        value = "N/A"

    embed.add_field(
        name="Lifetime",
        value=value,
        inline=True
    )

    embed.add_field(
        name="",
        value="",
        inline=True
    )

    embed.add_field(
        name="Current Streak",
        value=f"{streak} Win(s)",
        inline=True
    )

    embed.add_field(
        name="Best Streak",
        value=f"{best_streak} Win(s)",
        inline=True
    )

    embed.add_field(
        name="",
        value="",
        inline=True
    )

    embed.add_field(
        name="Best Win",
        value=f"{best_win['user']}: {best_win['rating']}",
        inline=True
    )

    embed.add_field(
        name="Worst Loss",
        value=f"{worst_loss['user']}: {worst_loss['rating']}",
        inline=True
    )

    embed.set_thumbnail(url=cur_user.display_avatar.url)

    await ctx.send(embed=embed)
