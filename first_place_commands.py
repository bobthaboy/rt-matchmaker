from RhythmTyperAPI.client import RhythmTyperClient
from datetime import datetime, timezone, timedelta, time
from asyncio import sleep
import json
from bot_config import bot
from discord.ext import tasks
from collections import Counter
from discord import Embed
from utility import cmd_log

rt = RhythmTyperClient()


async def grab_maps():
    print("Grabbing maps...")
    beatmaps = []

    command = rt.get_beatmaps()
    await sleep(1)

    beatmaps.extend(command.beatmaps)

    while True:
        command = rt.get_beatmaps(cursor=command.next_cursor)
        await sleep(1)

        beatmaps.extend(command.beatmaps)

        if not command.has_more:
            break

    i = 0
    playable_maps = {}
    for beatmap in beatmaps:
        for difficulty in beatmap.difficulties:
            i += 1
            playable_maps[i] = {
                "mapset_id": beatmap.mapset_id,
                "difficulty": difficulty.difficulty_name,
                "beatmap": beatmap
            }

    return playable_maps


def is_dt(leaderboard):
    mods = ["DT", "NC"]
    user_mods = leaderboard.mods
    for mod in mods:
        if mod in user_mods:
            return True
    return False


async def initialize():
    with open("data/first_place_scores.json", "r") as f:
        score_data = json.load(f)

    now = datetime.now(timezone.utc)

    with open("data/last_checked.txt", "w") as f:
        json.dump(now.isoformat(), f, indent=4)

    playable_maps = await grab_maps()
    for i, mapset in playable_maps.items():
        print(f"{i}/{len(playable_maps)}")
        perfect = False
        tied = False

        leaderboard = rt.beatmap_leaderboard(mapset["mapset_id"], mapset["difficulty"])
        await sleep(1)
        first = leaderboard[0]
        dt = is_dt(first)

        if first.score == leaderboard[1].score:
            tied = True

            if first.accuracy == 100 and dt:
                perfect = True

        jc = first.judgements
        notes = jc.perfect + jc.good + jc.ok + jc.miss

        score_data[i] = {
            "mapset_id": mapset["mapset_id"],
            "artist": mapset["beatmap"].beatmap_artist,
            "title": mapset["beatmap"].beatmap_title,
            "difficulty": mapset["difficulty"],
            "mapper": mapset["beatmap"].mapper,
            "notes": notes,
            "perfect": perfect,
            "tied": tied
        }

        if perfect:
            score_data[i]["play"] = None
        else:
            score_data[i]["play"] = {
                "player": first.username,
                "player_id": first.user_id,
                "score": first.score,
                "accuracy": first.accuracy,
                "dt": dt,
                "pp": first.pp,
                "combo": first.combo,
                "timestamp": first.timestamp.isoformat()
            }

    with open("data/first_place_scores.json", "w") as f:
        json.dump(score_data, f, indent=4)


async def add_maps():
    with open("data/first_place_scores.json", "r") as f:
        score_data = json.load(f)

    now = datetime.now(timezone.utc)

    with open("data/last_checked.txt", "w") as f:
        json.dump(now.isoformat(), f, indent=4)

    played_beatmaps = [(score["mapset_id"], score["difficulty"]) for score in score_data.values()]
    playable_maps = await grab_maps()
    for mapset in playable_maps.values():
        if (mapset["mapset_id"], mapset["difficulty"]) in played_beatmaps:
            continue

        i = len(score_data)
        perfect = False
        tied = False

        leaderboard = rt.beatmap_leaderboard(mapset["mapset_id"], mapset["difficulty"])
        await sleep(1)
        first = leaderboard[0]
        dt = is_dt(first)

        if first.score == leaderboard[1].score:
            tied = True

            if first.accuracy == 100 and dt:
                perfect = True

        jc = first.judgements
        notes = jc.perfect + jc.good + jc.ok + jc.miss

        score_data[i] = {
            "mapset_id": mapset["mapset_id"],
            "artist": mapset["beatmap"].beatmap_artist,
            "title": mapset["beatmap"].beatmap_title,
            "difficulty": mapset["difficulty"],
            "mapper": mapset["beatmap"].mapper,
            "notes": notes,
            "perfect": perfect,
            "tied": tied
        }

        if perfect:
            score_data[i]["play"] = None
        else:
            score_data[i]["play"] = {
                "player": first.username,
                "player_id": first.user_id,
                "score": first.score,
                "accuracy": first.accuracy,
                "dt": dt,
                "pp": first.pp,
                "combo": first.combo,
                "timestamp": first.timestamp.isoformat()
            }

    with open("data/first_place_scores.json", "w") as f:
        json.dump(score_data, f, indent=4)


@bot.command(name="unique")
async def rank_placements(ctx, page: int = 1):
    if page < 1:
        return

    with open("data/first_place_scores.json", "r") as f:
        score_data = json.load(f)

    scores = [score["play"] for score in score_data.values() if score["play"]]
    players = Counter(score["player"] for score in scores)
    total = sum(players.values())

    cursor = (page - 1) * 10
    leaderboard = players.most_common()[cursor:cursor + 10]
    if not leaderboard:
        return
    message = ""
    for i, (player, count) in enumerate(leaderboard, start=1):
        percentage = count / total * 100
        message += f"{i + cursor}. {player} - {percentage:.2f}% ({count})\n"

    embed = Embed(
        title=f"Unqiue #1 Scores Count",
        description=message
    )

    await ctx.reply(embed=embed)


@bot.command(name="targets")
async def oldest_uniques(ctx, page: int = 1):
    if page < 1:
        return

    with open("data/first_place_scores.json", "r") as f:
        score_data = json.load(f)

    scores = [score for score in score_data.values() if score["play"]]
    scores = sorted(scores, key=lambda x: datetime.fromisoformat(x["play"]["timestamp"]))

    cursor = (page - 1) * 10
    leaderboard = scores[cursor:cursor + 10]
    if not leaderboard:
        return

    message = ""
    for beatmap in leaderboard:
        play = beatmap["play"]
        dt = ""
        if play["dt"]:
            dt = "**+DT**"
        date = datetime.fromisoformat(play["timestamp"]).strftime("%Y-%m-%d")

        message += (f"{date}: "
                    f"[{beatmap['title']} [{beatmap['difficulty']}] ({beatmap['mapper']})]"
                    f"(https://rhythmtyper.net/beatmap/{beatmap['mapset_id']})\n")
        message += (f"**{play["player"]}** {play["score"]:,} {dt} {play["accuracy"]:.2f}% "
                    f"({play["combo"]}x/{beatmap["notes"]}x) {int(play["pp"])}pp\n\n")

    embed = Embed(
        title=f"Oldest Unique #1 Scores",
        description=message
    )

    await ctx.reply(embed=embed)


hourly_times = [
    time(hour=h, tzinfo=timezone.utc)
    for h in range(24)
]


@tasks.loop(time=hourly_times)
async def look_for_new():
    cmd_log("Looking for new...")
    with open("data/first_place_scores.json", "r") as f:
        score_data = json.load(f)

    scores = [score["play"] for score in score_data.values() if score["play"]]
    players = {score["player_id"] for score in scores}

    for player in players:
        user_recents = rt.get_user_profile(player).recent_activity
        await sleep(1)

        for item in user_recents:
            if item.type == "lost_first_place":
                play_id = next(
                    (play_id for play_id, play in score_data.items()
                     if play["difficulty"] == item.difficulty
                     and play["mapset_id"] == item.beatmap_id),
                    None
                )

                if not play_id:
                    await add_maps()
                    play_id = next(
                        (play_id for play_id, play in score_data.items()
                         if play["difficulty"] == item.difficulty
                         and play["mapset_id"] == item.beatmap_id),
                        None
                    )

                play_id = str(play_id)

                try:
                    timestamp = datetime.fromisoformat(score_data[play_id]["play"]["timestamp"])
                except TypeError:
                    continue

                if item.timestamp <= timestamp + timedelta(seconds=5):
                    continue

                cheaters = ["notsmurfingong", "andyjiang"]
                if item.taken_by_username in cheaters:
                    continue

                mapset_id = score_data[play_id]["mapset_id"]
                difficulty = score_data[play_id]["difficulty"]

                leaderboard = rt.beatmap_leaderboard(mapset_id, difficulty)
                await sleep(1)
                first = leaderboard[0]
                dt = is_dt(first)

                if first.score == leaderboard[1].score:
                    score_data[play_id]["tied"] = True

                    if first.accuracy == 100 and dt:
                        score_data[play_id]["perfect"] = True
                        score_data[play_id]["play"] = None
                        continue

                score_data[play_id]["play"] = {
                    "player": first.username,
                    "player_id": first.user_id,
                    "score": first.score,
                    "accuracy": first.accuracy,
                    "dt": dt,
                    "pp": first.pp,
                    "combo": first.combo,
                    "timestamp": first.timestamp.isoformat()
                }

    with open("data/first_place_scores.json", "w") as f:
        json.dump(score_data, f, indent=4)
