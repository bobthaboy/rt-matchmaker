import json
from RhythmTyperAPI.client import RhythmTyperClient
from RhythmTyperAPI.models import Play
from scorev2 import calculate_score
from time import sleep
from datetime import datetime
import asyncio
from discord import Object, NotFound
from discord.ext import commands
from bot_config import bot

rt = RhythmTyperClient()

with open("data/maps.json", "r") as f:
    maps: dict = json.load(f)


def get_mod_type(play: Play) -> str:
    if "DT" in play.mods or "NC" in play.mods:
        return "DT"
    if "HT" in play.mods or "DC" in play.mods:
        return "HT"
    return "NM"


def grab_maps() -> None:
    # THIS CODE GRABS ALL THE BEATMAPS
    print("Grabbing maps...")
    beatmaps = []

    command = rt.get_beatmaps()
    sleep(1)

    beatmaps.extend(command.beatmaps)

    while True:
        command = rt.get_beatmaps(cursor=command.next_cursor)
        sleep(1)

        beatmaps.extend(command.beatmaps)

        if not command.has_more:
            break

    track_mods = ["HT", "NM", "DT"]
    playable_maps = []
    for beatmap in beatmaps:
        for dif in beatmap.difficulties:
            for mod in track_mods:

                length = dif.length
                if mod == "HT":
                    length /= 0.75
                elif mod == "DT":
                    length /= 1.5

                if mod == "HT":
                    sr = dif.star_rating_ht
                elif mod == "DT":
                    sr = dif.star_rating_dt
                else:
                    sr = dif.star_rating

                playable_maps.append({
                    "beatmap_id": beatmap.beatmap_id,
                    "artist": beatmap.beatmap_artist,
                    "title": beatmap.beatmap_title,
                    "mapper": beatmap.mapper,
                    "difficulty": dif.difficulty_name,
                    "mod": mod,
                    "star_rating": sr,
                    "length": length,
                    "url": beatmap.background_image_url
                })

    with open("data/maps.json", "w") as f:
        json.dump(playable_maps, f, indent=4)


async def add_maps(adding: list) -> None:
    print("Grabbing maps...")
    beatmaps = []
    command = rt.get_beatmaps(status="all")
    await asyncio.sleep(1)

    beatmaps.extend(command.beatmaps)

    while True:
        command = rt.get_beatmaps(cursor=command.next_cursor, status="all")
        await asyncio.sleep(1)

        beatmaps.extend(command.beatmaps)

        if not command.has_more:
            break

    track_mods = ["HT", "NM", "DT"]
    playable_maps = []
    for beatmap in beatmaps:
        if beatmap.beatmap_id not in adding:
            continue
        for dif in beatmap.difficulties:
            for mod in track_mods:

                length = dif.length
                if mod == "HT":
                    length /= 0.75
                elif mod == "DT":
                    length /= 1.5

                if mod == "HT":
                    sr = dif.star_rating_ht
                elif mod == "DT":
                    sr = dif.star_rating_dt
                else:
                    sr = dif.star_rating

                playable_maps.append({
                    "beatmap_id": beatmap.beatmap_id,
                    "artist": beatmap.beatmap_artist,
                    "title": beatmap.beatmap_title,
                    "mapper": beatmap.mapper,
                    "difficulty": dif.difficulty_name,
                    "mod": mod,
                    "star_rating": sr,
                    "length": length,
                    "url": beatmap.background_image_url
                })

    with open("data/maps.json", "r") as f:
        maps = json.load(f)

    maps.extend(playable_maps)

    with open("data/maps.json", "w") as f:
        json.dump(maps, f, indent=4)


def get_damage_multiplier(turn: int) -> float | int:
    if turn < 3:
        return 1
    else:
        return turn * 0.5 + 0.5


def get_play_score(play: Play) -> int:
    jc = play.judgements
    judgements = f"{jc.perfect}/{jc.good}/{jc.ok}"
    max_combo = (
            jc.perfect
            + jc.good
            + jc.ok
            + jc.miss
    )

    return calculate_score(
        judgements=judgements,
        misses=jc.miss,
        combo=play.combo,
        max_combo=max_combo
    )


def update_elo(winner_id: int, loser_id: int, k=32) -> None:
    winner_id = str(winner_id)
    loser_id = str(loser_id)

    with open("data/elo.json", "r") as f:
        elo: dict = json.load(f)

    winner_old_rating = elo.setdefault(winner_id, 1000)
    loser_old_rating = elo.setdefault(loser_id, 1000)

    winner_expected = 1 / (
            1 + 10 ** ((loser_old_rating - winner_old_rating) / 400)
    )
    loser_expected = 1 / (
            1 + 10 ** ((winner_old_rating - loser_old_rating) / 400)
    )

    elo[winner_id] = winner_old_rating + k * (1 - winner_expected)
    elo[loser_id] = loser_old_rating + k * (0 - loser_expected)

    update_logs(winner_id, winner_old_rating, elo[winner_id], loser_id, loser_old_rating, elo[loser_id])

    with open("data/elo.json", "w") as f:
        json.dump(elo, f, indent=4)


def update_logs(winner_id: str, winner_old_rating: int, winner_new_rating: int, loser_id: str, loser_old_rating: int,
                loser_new_rating: int) -> None:
    with open("data/logs.json", "r") as f:
        logs = json.load(f)

    last_id = logs[-1]["id"]

    logs.append({
        "id": last_id + 1,
        "winner": {
            "id": int(winner_id),
            "old_rating": winner_old_rating,
            "new_rating": winner_new_rating,
        },
        "loser": {
            "id": int(loser_id),
            "old_rating": loser_old_rating,
            "new_rating": loser_new_rating,
        },
        "timestamp": datetime.now().isoformat(),
    })

    with open("data/logs.json", "w") as f:
        json.dump(logs, f, indent=4)


def is_fc(play: Play, max_notes: int) -> str | None:
    if play.grade == "SS":
        return " **Perfect!**"
    if play.combo == max_notes:
        return " **FC**"
    else:
        return None


def olc_peepee_logs(play1: Play, play2: Play, notes: int) -> None:
    with open("data/olc_peepee.json", "r") as f:
        olc_logs: list = json.load(f)

    plays = [play1, play2]
    for play in plays:
        score = get_play_score(play)
        jc = play.judgements
        judgements = f"{jc.perfect}/{jc.good}/{jc.ok}"
        misses = f"{jc.miss}"
        combo = f"{play.combo}/{notes}"
        olc_logs.extend([[score, judgements, misses, combo]])

    with open("data/olc_peepee.json", "w") as f:
        json.dump(olc_logs, f, indent=4)


def cmd_log(log: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {log}")


async def average_sr(player_id: str) -> float | int | None:
    sr = 0
    count = 0
    user = rt.get_user_profile(player_id)
    await asyncio.sleep(1)
    plays = user.top_plays
    for play in plays:
        mod = get_mod_type(play)

        for beatmap in maps:
            if beatmap["beatmap_id"] == play.mapset_id and beatmap["difficulty"] == play.difficulty_name and beatmap[
                "mod"] == mod:
                sr += beatmap["star_rating"] * (play.acc / 95)
                count += 1
                break

    if count == 0:
        return None

    return sr / count


async def andrew_resolve(msg) -> None:
    bug_report = 1453643294977294419
    suggestions = 1453652931046932603
    andrew = 673247785101033473

    if msg.author.id == andrew:
        parent = getattr(msg.channel, "parent", None)
        if "?" not in msg.content:

            if getattr(parent, "id", None) == bug_report:
                if "fixed" in msg.content.lower():
                    await msg.channel.send("This post has been automatically marked as resolved.")
                    resolved_tag = Object(id=1477065300980531261)
                    await msg.channel.edit(applied_tags=[resolved_tag])

            if getattr(parent, "id", None) == suggestions:
                if "added" in msg.content.lower() or "done" in msg.content.lower():
                    await msg.channel.send("This post has been automatically marked as resolved.")
                    resolved_tag = Object(id=1477064650582524036)
                    await msg.channel.edit(applied_tags=[resolved_tag])


async def forum_scraper(ctx, channel, new_tag) -> None:
    found = []
    for thread in channel.threads:
        if any(tag.id == new_tag for tag in thread.applied_tags):
            try:
                message = await thread.fetch_message(thread.id)
            except NotFound:
                message = None

            if message:
                reactions = getattr(message, "reactions", None)
                if reactions:
                    max_reaction = max((reaction.count for reaction in message.reactions), default=0)
                else:
                    max_reaction = 0
            else:
                max_reaction = 0

            found.append((thread, max_reaction))

    found_ids = {thread.id for thread, _ in found}
    async for thread in channel.archived_threads(limit=None):
        if thread in found_ids:
            continue
        if any(tag.id == new_tag for tag in thread.applied_tags):
            try:
                message = await thread.fetch_message(thread.id)
            except NotFound:
                message = None

            if message:
                reactions = getattr(message, "reactions", None)
                if reactions:
                    max_reaction = max((reaction.count for reaction in message.reactions), default=0)
                else:
                    max_reaction = 0
            else:
                max_reaction = 0

            found.append((thread, max_reaction))
        if len(found) == 100:
            break

    found.sort(key=lambda r: r[1], reverse=True)
    found = found[:10]
    message = "I am only grabbing the first 100 I see. There is likely more than 100. Here is the top 10:\n"
    for i, (thread, count) in enumerate(found, start=1):
        message += f"{i}. {count} - {thread.jump_url}\n"

    await ctx.reply(message)


@commands.cooldown(1, 3600, commands.BucketType.default)
@bot.command(name="suggestions")
async def suggestions(ctx) -> None:
    channel = bot.get_channel(1453652931046932603)
    new_tag = 1477067810822815754
    await forum_scraper(ctx, channel, new_tag)


@commands.cooldown(1, 3600, commands.BucketType.default)
@bot.command(name="bugs")
async def bug_reports(ctx) -> None:
    channel = bot.get_channel(1453643294977294419)
    new_tag = 1477067879789760662
    await forum_scraper(ctx, channel, new_tag)
