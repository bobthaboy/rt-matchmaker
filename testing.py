import json
from utility import add_maps, cmd_log
from discord.ext import commands
from match_commands import active_matches
from bot_config import bot
from RhythmTyperAPI.client import RhythmTyperClient

rt = RhythmTyperClient()


@commands.is_owner()
@bot.command(name="debug")
async def debug(ctx) -> None:
    print()
    cmd_log(f"debug command")
    print("----------------")
    print("Matches:")
    for i, (user, battle) in enumerate(active_matches.items(), start=1):
        player1 = await bot.fetch_user(user)
        if battle[0]:
            print(i, player1.name, battle[0].name, battle[2])
        else:
            print(i, player1.name, battle[0], battle[2])
    print("----------------")


# @commands.is_owner()
# @bot.command(name="reload")
# async def reload(ctx):
#     await bot.reload_extension("cogs.commands")
#     await ctx.send("Reloaded!")

@commands.is_owner()
@bot.command(name="update")
async def add_vouched(ctx, *args) -> None:
    with open("data/vouched.json", "r") as f:
        vouched = json.load(f)

    if args:
        adding = {
            arg: vouched.get(arg, {}).get("title")
            for arg in args
        }

    else:
        adding = {
            bid: data["title"]
            for bid, data in vouched.items()
            if len(data["votes"]) >= 5
        }

    beatmaps = list(adding)

    # for beatmap in beatmaps:
    #     test = vouched.pop(beatmap, None)

    await add_maps(beatmaps)

    message = "Added beatmaps:\n"
    for beatmap_id, title in adding.items():
        if not title:
            message += f"https://rhythmtyper.net/beatmap/{beatmap_id}\n"
        else:
            message += f"[{title}](https://rhythmtyper.net/beatmap/{beatmap_id})\n"

    await ctx.reply(message, suppress_embeds=True)

    with open("data/vouched.json", "w") as f:
        json.dump(vouched, f, indent=4)


@commands.is_owner()
@bot.command(name="ping")
async def ping(ctx) -> None:
    await ctx.reply(ctx.author.name + " pong!")
    # nuzzy = await bot.fetch_user(318505902468628480)
    #
    # state = MatchState(
    #     hand1=[],
    #     hand2=[],
    #     available_maps=[],
    #     flip=True,
    #     casual=False,
    #     is_achievements={},
    #     chooser=ctx.author,
    #     turn=2,
    #     player1_hp=564_535,
    #     player2_hp=799_069
    # )
    #
    # beatmap = {
    #     "beatmap_id": "8jrilfywyxre",
    #     "artist": "steelplus ft. Kitsui Akira",
    #     "title": "Emerald Lakeside (Action)",
    #     "mapper": "HexagridIndustry",
    #     "difficulty": "\"MAPPER:PIGER-<. SONG:STEELPLUS FT. KITSUI AKIRA - EMERALD LAKESIDE_,. 6.00*/3:38|+_\"",
    #     "mod": "NM",
    #     "star_rating": 6.001360048424729,
    #     "length": 218.667,
    #     "url": "https://storage.googleapis.com/rhythm-typer.firebasestorage.app/beatmaps/8jrilfywyxre/bg_0_bg1.png?v=2"
    # }
    #
    # play1 = Play(
    #     score_id="1234567890",
    #     beatmap_id="987654321",
    #     beatmap_title="Random Access Memories",
    #     beatmap_artist="Daft Punk",
    #     difficulty="Expert",
    #     pp=287.42,
    #     acc=98.73,
    #     score=1023456,
    #     combo=1842,
    #     grade="S",
    #     mods=["HD", "HR"],
    #     timestamp=datetime(2026, 8, 12, 17, 20, 34),
    #     perfect=1543,
    #     good=87,
    #     ok=12,
    #     misses=3,
    #     star_rating=6.42,
    #     length=214.7,
    #     od=9,
    #     bpm=178,
    #     mapper="RandomMapper",
    # )
    #
    # play2 = Play(
    #     score_id="1234567890",
    #     beatmap_id="987654321",
    #     beatmap_title="Random Access Memories",
    #     beatmap_artist="Daft Punk",
    #     difficulty="Expert",
    #     pp=287.42,
    #     acc=91.73,
    #     score=1023456,
    #     combo=1842,
    #     grade="S",
    #     mods=["HD", "HR"],
    #     timestamp=datetime(2026, 8, 12, 17, 20, 34),
    #     perfect=1143,
    #     good=87,
    #     ok=12,
    #     misses=3,
    #     star_rating=6.42,
    #     length=214.7,
    #     od=9,
    #     bpm=178,
    #     mapper="RandomMapper",
    # )
    #
    # play1_score = get_play_score(play1)
    # play2_score = get_play_score(play2)
    # damage = play1_score - play2_score
    #
    # score1 = Score(
    #     user=ctx.author,
    #     play=play1,
    #     score=play1_score,
    #     damage=damage
    # )
    #
    # score2 = Score(
    #     user=nuzzy,
    #     play=play2,
    #     score=play2_score
    # )
    #
    # await ctx.send(embed=round_embed(state, score1, score2, 1, beatmap))

# from RhythmTyperAPI.client import RhythmTyperClient
# from time import sleep
# import json
#
# rt = RhythmTyperClient()
#
# for item in rt.get_user_profile("erzUUNuTTygEdnWK01MEZDQ8cZ23").top_plays:
#     print(item)
#
# # with open("maps.json", "r") as f:
# #     maps = json.load(f)
# #
# # beatmap_stuff = []
# # for beatmap in maps:
# #     if beatmap["mod"] != "NM":
# #         continue
# #
# #     beatmap_stuff.append(beatmap)
# #
# # beatmap_stuff.sort(key=lambda x: x["star_rating"], reverse=True)
# # beatmap_stuff = beatmap_stuff[:25]
# # for beatmap in beatmap_stuff:
# #     difficulty = f"[{beatmap["difficulty"]}]"
# #     star_rating = f"{beatmap["star_rating"]:.2f}"
# #     print(beatmap["title"], difficulty, star_rating)
