import json
from RhythmTyperAPI.models import Play
from time import monotonic, time
import random
from discord import Member, Embed, Color, Thread, Reaction
from discord.ext import commands
from datetime import datetime, timezone, timedelta
import asyncio
from utility import update_elo, get_mod_type, get_play_score, get_damage_multiplier, olc_peepee_logs, cmd_log, \
    average_sr
from achievement_commands import achievements_check, achievement_qualified
from profile_commands import get_user_elo_formatted
from models import MatchState, Score
from bot_config import bot
from RhythmTyperAPI.client import RhythmTyperClient

rt = RhythmTyperClient()

with open("data/users.json", "r") as f:
    users: dict = json.load(f)

with open("data/maps.json", "r") as f:
    maps: dict = json.load(f)

active_matches = {}

mods = {"HT": "💤", "NM": "🟢", "DT": "⚡"}

grade_emotes = {"SS": "<:SS_:1537208565498908733>",
                "S": "<:S_:1537208566757331015>",
                "A": "<:A_:1537208567998980157>",
                "B": "<:B_:1537208569131307158>",
                "C": "<:C_:1537208570985058374>",
                "D": "<:D_:1537208572226703413>",
                "F": "<:F_:1537208574130917417>"}


# idk what type "thread" is
async def draft(ctx, target: Member, state: MatchState, thread) -> tuple[dict | None, MatchState]:
    if not state.available_maps:
        await thread.send(f"{ctx.author.mention} {target.mention} idk how you did it but apparently you tied.")
        cleanup_match(ctx.author, target)
        return None, state

    if not state.hand1:
        state.hand1 = random.sample(state.available_maps, 5)
        for beatmap in state.hand1:
            state.available_maps.remove(beatmap)

    if not state.hand2:
        state.hand2 = random.sample(state.available_maps, 5)
        for beatmap in state.hand2:
            state.available_maps.remove(beatmap)

    if state.flip:
        chooser = ctx.author
        watcher = target
        hand = state.hand1
    else:
        chooser = target
        watcher = ctx.author
        hand = state.hand2

    state.chooser = chooser
    maps_message = ""
    for i, beatmap in enumerate(hand, start=1):
        maps_message += f"{i}. {beatmap_formatting(beatmap)}\n"

    end_time = int(time()) + 300
    maps_message += f"\n-# ⏳ Forfeit in <t:{end_time}:R>"

    if state.chooser == ctx.author:
        hp = state.player1_hp
    else:
        hp = state.player2_hp

    hp = int(255 * hp / 1_000_000)

    embed = Embed(
        title=f"{chooser.name}'s Pick!",
        description=maps_message,
        color=Color.from_rgb(255 - hp, hp, 0)
    )
    embed.set_thumbnail(url=chooser.display_avatar.url)
    embed.set_footer(
        text="⚠️ If a match is played without NF, the match may not get recorded and this command will cancel.")

    message = await thread.send(embed=embed)

    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    for reaction in reactions:
        await message.add_reaction(reaction)

    def check(reaction, member):
        return (
                member == chooser
                and reaction.message.id == message.id
                and str(reaction.emoji) in reactions
        )

    try:
        reaction, member = await bot.wait_for(
            "reaction_add",
            timeout=300.0,
            check=check
        )

        selected = int(str(reaction.emoji)[0])
        # await message.delete()
        choice = hand[selected - 1]
        new_map = random.choice(state.available_maps)
        hand[selected - 1] = new_map
        state.available_maps.remove(new_map)

        await thread.send(
            f"**{choice['title']} ({choice['mapper']}) [{choice['difficulty']}] {mods[choice['mod']]} {choice['mod']}** chosen by {chooser.name}.\n"
            f"Please start the match immediately or else Andrew will die... :(\n"
            f"{ctx.author.mention} {target.mention}"
        )
        return choice, state

    except asyncio.TimeoutError:
        # await message.delete()
        winner = watcher
        loser = chooser

        timeout_message = (
            f"⌛ {chooser.mention} I waited 5 minutes for you to pick, this match is now considered deserted.\n"
            f"By default, the winner is {winner.mention}!\n\n")
        if not state.casual:
            with open("data/elo.json", "r") as f:
                elo: dict = json.load(f)

            winner_elo = elo.setdefault(str(winner.id), 1000)
            loser_elo = elo.setdefault(str(loser.id), 1000)

            update_elo(winner.id, loser.id)

            with open("data/elo.json", "r") as f:
                elo: dict = json.load(f)

            timeout_message += (
                f"{winner.name}: {int(winner_elo)} -> {int(elo[str(winner.id)])}↑ (+{abs(int(elo[str(winner.id)] - winner_elo))})\n"
                f"{loser.name}: {int(loser_elo)} -> {int(elo[str(loser.id)])}↓ (-{abs(int(loser_elo - elo[str(loser.id)]))})")

        await thread.send(timeout_message)
        cleanup_match(ctx.author, target)
        return None, state


def recent_condition(play: Play, pick: dict, minutes: int = 0) -> bool:
    condition = (
            play.beatmap_id == pick["beatmap_id"]
            and play.difficulty == pick["difficulty"]
            and get_mod_type(play) == pick["mod"]
    )

    if minutes:
        condition2 = play.timestamp > datetime.now(timezone.utc) - timedelta(minutes=minutes)
        condition = condition and condition2

    return condition


# idk what type "thread" is
async def ping_recent(ctx, length: float | int, target: Member, pick: dict, competitors: list[str], thread,
                      state: MatchState, play1: Play | None = None, play2: Play | None = None) -> tuple[
    Play | None, Play | None]:
    deadline = monotonic() + 600
    patience_deadline = None
    slowpoke = None
    patience = 0
    while True:
        if not play1 or not play2:
            play1 = rt.get_user_profile(competitors[0]).recent_plays[0]
            await asyncio.sleep(1)
            play2 = rt.get_user_profile(competitors[1]).recent_plays[0]
            await asyncio.sleep(1)

        play1_exists = recent_condition(play1, pick)
        play2_exists = recent_condition(play2, pick)

        if play1_exists and play2_exists:
            break

        if monotonic() >= deadline:
            if not play1_exists and not play2_exists:
                await thread.send((
                    f"{ctx.author.mention} {target.mention} I have been waiting for FIVE FUCKING MINUTES "
                    f"for you to finish this damn match. I'm not waiting any longer. Fuck your!!!\n")
                )
                cleanup_match(ctx.author, target)
                return None, None

            if play1_exists:
                winner = ctx.author
                loser = target
            else:
                winner = target
                loser = ctx.author

            message = (f"Was unable to find {loser.mention}'s play in recent.\n"
                       f"By default, the winner is {winner.mention}!\n\n")

            if not state.casual:
                with open("data/elo.json", "r") as f:
                    elo: dict = json.load(f)

                winner_elo = elo.setdefault(str(winner.id), 1000)
                loser_elo = elo.setdefault(str(loser.id), 1000)

                update_elo(winner.id, loser.id)

                with open("data/elo.json", "r") as f:
                    elo: dict = json.load(f)

                message += (
                    f"{winner.name}: {int(winner_elo)} -> {int(elo[str(winner.id)])}↑ (+{abs(int(elo[str(winner.id)] - winner_elo))})\n"
                    f"{loser.name}: {int(loser_elo)} -> {int(elo[str(loser.id)])}↓ (-{abs(int(loser_elo - elo[str(loser.id)]))})")

            await thread.send(message)
            cleanup_match(ctx.author, target)

            return None, None

        if (play1_exists or play2_exists) and not patience_deadline:
            await asyncio.sleep(10)

            if not play1_exists:
                play1 = rt.get_user_profile(competitors[0]).recent_plays[0]
                play1_exists = recent_condition(play1, pick)
                await asyncio.sleep(1)
            else:
                play2 = rt.get_user_profile(competitors[1]).recent_plays[0]
                play2_exists = recent_condition(play2, pick)
                await asyncio.sleep(1)

            if not play1_exists or not play2_exists:
                if not recent_condition(play1, pick):
                    slowpoke = ctx.author
                else:
                    slowpoke = target

            if slowpoke:
                await thread.send((
                    f"{slowpoke.mention}, hey buddy? I've been waiting, and I don't think your score sent.\n"
                    "Your opponent doesn't need to redo theirs, but you do. Go, do it now! I just reset your timer.\n"
                    "Or you can just `!cancel` the match.")
                )
                deadline += length + 60
                patience_deadline = monotonic() + length + 60
                patience += 1

        if patience_deadline:
            if monotonic() >= patience_deadline:
                if patience < 2:
                    await thread.send((
                        f"{slowpoke.mention}, hey buddy? I've been waiting, and I don't think your score sent.\n"
                        "Last chance. Go, do it now! I just reset your timer.\n"
                        "Or you can just `!cancel` the match.")
                    )
                    deadline += length + 60
                    patience_deadline = monotonic() + length + 30
                    patience += 1
                else:
                    deadline = -1

        if not recent_condition(play1, pick, 10):
            await asyncio.sleep(5)
            play1 = rt.get_user_profile(competitors[0]).recent_plays[0]

        if not recent_condition(play2, pick, 10):
            await asyncio.sleep(5)
            play2 = rt.get_user_profile(competitors[1]).recent_plays[0]

    return play1, play2


# idk what type "thread" is
async def results(ctx, pick: dict, competitors: list[str], target: Member, state: MatchState, thread) -> None:
    while True:
        if pick is None:
            return
        length = pick["length"]
        await asyncio.sleep(length)

        play1, play2 = await ping_recent(ctx, length, target, pick, competitors, thread, state)
        if not play1 or not play2:
            return

        play1_score = get_play_score(play1)
        play2_score = get_play_score(play2)

        state.turn += 1

        dmg_mult = get_damage_multiplier(state.turn)

        score1 = Score(
            user=ctx.author,
            play=play1,
            score=play1_score
        )

        score2 = Score(
            user=target,
            play=play2,
            score=play2_score
        )

        if play1_score > play2_score:
            damage = play1_score - play2_score
            state.player2_hp -= int(damage * dmg_mult)
            score1.damage = damage
        else:
            damage = play2_score - play1_score
            state.player1_hp -= int(damage * dmg_mult)
            score2.damage = damage

        await thread.send(embed=round_embed(state, score1, score2, dmg_mult, pick))

        # Temp logger for olc to rework shit
        notes = play1.perfect + play1.good + play1.ok + play1.misses
        olc_peepee_logs(play1, play2, notes)

        if state.is_achievements["qualified"]:
            await achievements_check(ctx, ctx.author, thread, play1, play2, state.player1_hp, state.player2_hp, notes,
                                     state, state.is_achievements["player1_wins"])
            await achievements_check(ctx, target, thread, play2, play1, state.player2_hp, state.player1_hp, notes,
                                     state, state.is_achievements["player2_wins"])

        if state.player1_hp <= 0 or state.player2_hp <= 0:
            if state.player1_hp <= 0:
                winner = target
                loser = ctx.author
            else:
                winner = ctx.author
                loser = target

            if state.casual:
                await thread.send(f"**{winner.mention} beats {loser.mention}!**\n\n")
            else:
                with open("data/elo.json", "r") as f:
                    elo: dict = json.load(f)

                winner_elo = elo.setdefault(str(winner.id), 1000)
                loser_elo = elo.setdefault(str(loser.id), 1000)

                update_elo(winner.id, loser.id)

                with open("data/elo.json", "r") as f:
                    elo: dict = json.load(f)

                await thread.send(f"**{winner.mention} beats {loser.mention}!**\n\n"
                                  f"{winner.name}: {int(winner_elo)} -> {int(elo[str(winner.id)])}↑ (+{abs(int(elo[str(winner.id)] - winner_elo))})\n"
                                  f"{loser.name}: {int(loser_elo)} -> {int(elo[str(loser.id)])}↓ (-{abs(int(loser_elo - elo[str(loser.id)]))})")

            cleanup_match(ctx.author, target)
            return

        state.flip = not state.flip
        pick, state = await draft(ctx, target, state, thread)


# idk what type "task" is
async def load_draft(ctx, target: Member, task, casual: bool, flag: str | None) -> None:
    cmd_log(f"Matching {ctx.author.name} {target.name}.")

    try:
        players = [users[str(ctx.author.id)], users[str(target.id)]]
    except KeyError as e:
        new = await bot.fetch_user(int(e.args[0]))
        await ctx.reply(
            f"Hey, {new.mention} here wasn't added to the bot. Run the `!pair` command!"
        )
        cleanup_match(ctx.author, target)
        return

    player1_sr = await average_sr(players[0])
    player2_sr = await average_sr(players[1])
    if not player1_sr or not player2_sr:
        await ctx.reply(
            f"I was not able to find a user's plays"
        )
        return

    avg_sr = (player1_sr + player2_sr) / 2
    avg_sr = int(avg_sr * 100)
    sr_range = range(avg_sr - 120, avg_sr + 120)

    sr_range_maps = []
    flag_mods = ["NM"]

    if not flag:
        flag_mods.append("DT")
    else:
        if "ht" in flag.lower():
            flag_mods.append("HT")
        if "dt" in flag.lower():
            flag_mods.append("DT")

    for beatmap in maps:
        if beatmap['mod'] not in flag_mods:
            continue

        if beatmap['length'] < 60 or beatmap['length'] > 240:
            continue

        if int(beatmap['star_rating'] * 100) in sr_range:
            sr_range_maps.append(beatmap)

    with open("data/elo.json", "r") as f:
        elo: dict = json.load(f)

    player1_elo = elo.setdefault(str(ctx.author.id), 1000)
    player2_elo = elo.setdefault(str(target.id), 1000)

    if player1_elo != player2_elo:
        flip = player1_elo < player2_elo
    else:
        flip = random.choice([True, False])

    state = MatchState(
        hand1=[],
        hand2=[],
        available_maps=sr_range_maps,
        flip=flip,
        casual=casual,
        start_time=monotonic(),
        is_achievements=achievement_qualified(ctx.author, target, casual)
    )

    active_matches[ctx.author.id] = (target, state, task)
    active_matches[target.id] = (ctx.author, state, task)

    if isinstance(ctx.channel, Thread):
        thread = ctx.channel
    else:
        thread = await ctx.message.create_thread(
            name=f"{ctx.author.name} vs {target.name}",
            auto_archive_duration=60
        )

    await thread.send(f"{ctx.author.mention} vs {target.mention}!\n"
                      f"{ctx.author.name} SR: {player1_sr:.2f}*\n"
                      f"{target.name} SR: {player2_sr:.2f}*\n"
                      f"Calculated Difficulty Range: {(avg_sr - 120) / 100:.2f}~{(avg_sr + 120) / 100:.2f}*\n")

    cmd_log(f"Sending {ctx.author.name} {target.name} to draft.")
    map_pick, state = await draft(ctx, target, state, thread)
    if map_pick is None:
        return
    await results(ctx, map_pick, players, target, state, thread)


@bot.command(name="match")
async def match(ctx, target: Member, flag: str | None = None, casual: bool = False) -> None:
    task = asyncio.current_task()

    if target == ctx.author:
        await ctx.reply("You can't challenge yourself!")
        return

    if target.bot:
        await ctx.reply("Dumbfuck.")
        return

    if is_busy(ctx.author):
        await ctx.reply("You are busy right now.")
        return

    if is_busy(target):
        await ctx.reply("They are busy right now.")
        return

    active_matches[ctx.author.id] = (target, None, task)
    active_matches[target.id] = (ctx.author, None, task)

    if casual:
        message = await ctx.send(
            f"{target.name}, do you accept {ctx.author.name}'s challenge?"
        )
    else:
        message = await ctx.send(
            f"{target.name} ({get_user_elo_formatted(target)}), do you accept {ctx.author.name} ({get_user_elo_formatted(ctx.author)})'s challenge?"
        )

    await message.add_reaction("✅")
    await message.add_reaction("❌")

    cmd_log(f"Match request from {ctx.author.name} to {target.name}")

    def check(reaction, member):
        return (
                member == target
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
            cmd_log(f"Match {target.name} declined.")
            await ctx.reply(
                f"❌ Challenge declined!"
            )
            cleanup_match(ctx.author, target)
            return

    except asyncio.TimeoutError:
        cmd_log(f"Match {target.name} didn't respond.")
        await ctx.reply(f"⌛ User failed to respond in time.")
        cleanup_match(ctx.author, target)
        return

    await load_draft(ctx, target, task, casual, flag)


@bot.command(name="casual")
async def casual_match(ctx, target: Member, flag: str | None = None) -> None:
    await match(ctx, target, flag, casual=True)


@bot.command(name="forfeit", aliases=["ff", "concede", "resign"])
async def forfeit(ctx) -> None:
    cur_match: tuple | None = active_matches.get(ctx.author.id)

    if not cur_match:
        await ctx.reply("You aren't currently in a match.")
        return

    opponent, state, task = cur_match

    if state.casual:
        await ctx.reply(f"🏳️ {ctx.author.mention} forfeited. "
                        f"{opponent.mention} wins!")
        cleanup_match(ctx.author, opponent)
        task.cancel()

    message = await ctx.reply(
        f"Are you sure you would like to forfeit?\n"
        "(Elo WILL be traded between this match. If you wanted to cancel the match, type `!cancel`.)"
    )

    await message.add_reaction("✅")
    await message.add_reaction("❌")

    def check(reaction, member):
        return (
                member == ctx.author
                and reaction.message.id == message.id
                and str(reaction.emoji) in ["✅", "❌"]
        )

    try:
        reaction, member = await bot.wait_for(
            "reaction_add",
            timeout=60.0,
            check=check
        )

        if str(reaction.emoji) == "❌":
            await message.delete()
            return

    except asyncio.TimeoutError:
        await message.delete()
        return

    task.cancel()

    with open("data/elo.json", "r") as f:
        elo: dict = json.load(f)

    winner = opponent
    loser = ctx.author
    winner_elo = elo[str(opponent.id)]
    loser_elo = elo[str(ctx.author.id)]

    update_elo(opponent.id, ctx.author.id)

    with open("data/elo.json", "r") as f:
        elo: dict = json.load(f)

    await ctx.send(
        f"🏳️ {ctx.author.mention} forfeited. "
        f"{opponent.mention} wins!"
        f"{winner.name}: {int(winner_elo)} -> {int(elo[str(winner.id)])}↑ (+{abs(int(elo[str(winner.id)] - winner_elo))})\n"
        f"{loser.name}: {int(loser_elo)} -> {int(elo[str(loser.id)])}↓ (-{abs(int(loser_elo - elo[str(loser.id)]))})")

    cleanup_match(ctx.author, opponent)


@commands.cooldown(1, 900, commands.BucketType.user)
@bot.command(name="queue")
async def queue(ctx, flag: str | None = None) -> None:
    task = asyncio.current_task()
    user = users.get(str(ctx.author.id))

    if user is None:
        await ctx.reply(
            "Hey, you weren't added to the bot. Run the `!pair` command!"
        )
        return

    if is_busy(ctx.author):
        await ctx.reply("You are busy right now.")
        return

    with open("data/elo.json", "r") as f:
        elo = json.load(f)

    user_elo = elo.setdefault(str(ctx.author.id), 1000)
    role = ctx.guild.get_role(1535766560491442206)

    members = [member for member in ctx.guild.members if role in member.roles]
    echo_users = []
    for member in members:
        if member.id == ctx.author.id:
            continue
        user = users.get(str(member.id))
        if user is None:
            continue
        echo_elo = elo.setdefault(str(member.id), 1000)
        if abs(echo_elo - user_elo) <= 100:
            echo_users.append(member)

    if not echo_users:
        await ctx.reply("It appears no one is worthy enough to face you...")
        return

    echo_message = ("You were pinged because you had the Matchmaker role (`!echo`) "
                    f"and you were a worthy opponent for {ctx.author.name} ({get_user_elo_formatted(ctx.author)})! "
                    f"Take on the challenge?\n\n||")
    for member in echo_users:
        echo_message += f"{member.mention} "
    echo_message += "||"

    message = await ctx.reply(echo_message)

    active_matches[ctx.author.id] = (None, None, task)

    await message.add_reaction("✅")

    cmd_log(f"Queue request from {ctx.author.name}")

    def check(reaction: Reaction, member: Member):
        return (
                member in echo_users
                and not is_busy(member)
                and reaction.message.id == message.id
                and str(reaction.emoji) == "✅"
        )

    try:
        reaction, member = await bot.wait_for(
            "reaction_add",
            timeout=900.0,
            check=check
        )

        target = member

    except asyncio.TimeoutError:
        cmd_log(f"{ctx.author.name}'s queue timed out.")
        await ctx.reply(
            f"⌛ I waited for 15 minutes, but nobody came."
        )
        cleanup_match(ctx.author)
        return

    elo.setdefault(str(target.id), 1000)
    await ctx.reply(f"✅ Challenge accepted by {target.name} ({get_user_elo_formatted(target)})!")
    casual = False

    await load_draft(ctx, target, task, casual, flag)


def beatmap_formatting(beatmap: dict) -> str:
    seconds = int(beatmap['length'])
    minutes = seconds // 60
    seconds = seconds % 60

    length = f"{minutes}:{seconds:02d}"

    return (f"{mods[beatmap['mod']]} **{beatmap['mod']}** "
            f"[{beatmap['title']} [{beatmap['difficulty']}] ({beatmap['mapper']})]"
            f"(https://rhythmtyper.net/beatmap/{beatmap['beatmap_id']}) "
            f"{beatmap['star_rating']:.2f}* {length}")


def is_busy(member: Member) -> bool:
    return member.id in active_matches.keys()


def cleanup_match(player1: Member, player2: Member | None = None) -> None:
    active_matches.pop(player1.id, None)

    if player2:
        active_matches.pop(player2.id, None)


def health_bar(hp: int) -> str:
    max_hp = 1_000_000
    hp_block = "▉"
    hp_blank = "░"

    filled = round((hp / max_hp) * 13)
    filled = max(0, min(filled, 13))

    tank = hp_block * filled + hp_blank * (13 - filled)

    color = 33
    if filled <= 3:
        color = 31
    if filled >= 9:
        color = 32

    return f"[{color}m{tank}[0m"


def round_embed(state: MatchState, score1: Score, score2: Score, dmg_mult: float | int, beatmap: dict) -> Embed:
    beatmap_message = beatmap_formatting(beatmap)

    damage = 0
    winner = score1
    loser = score2
    winner_hp = state.player1_hp
    loser_hp = state.player2_hp
    if score1.damage:
        damage = score1.damage
    elif score2.damage:
        damage = score2.damage
        winner_hp = state.player2_hp
        loser_hp = state.player1_hp
        winner = score2
        loser = score1

    winner_hp = max(winner_hp, 0)
    loser_hp = max(loser_hp, 0)
    damage = f"{int(damage * dmg_mult):,}"

    notes = winner.play.perfect + winner.play.good + winner.play.ok + winner.play.misses

    if winner.play.grade == "SS":
        winner_grade = f"{grade_emotes[winner.play.grade]} "
    else:
        winner_grade = f"{grade_emotes[winner.play.grade]}"

    if loser.play.grade == "SS":
        loser_grade = f"{grade_emotes[loser.play.grade]} "
    else:
        loser_grade = f"{grade_emotes[loser.play.grade]}"

    winner_combo = f"{winner.play.combo}x/{notes}x "
    loser_combo = f"{loser.play.combo}x/{notes}x "

    if winner.play.misses:
        winner_combo += f"[ {winner.play.misses}<:miss:1537210464080240740>]"
    else:
        winner_combo += f"**FC!**"

    if loser.play.misses:
        loser_combo += f"[ {loser.play.misses}<:miss:1537210464080240740>]"
    else:
        loser_combo += f"**FC!**"

    embed = Embed(
        title=f"Round {state.turn}. Damage multiplier: {dmg_mult}x",
        description=beatmap_message
    )

    embed.add_field(
        name=winner.user.name,
        value=f"```ansi\n"
              f"{health_bar(winner_hp)}\n"
              f"{winner_hp:,} HP\n"
              f"```",
        inline=True
    )

    embed.add_field(
        name=loser.user.name,
        value=(f"```ansi\n"
               f"{health_bar(loser_hp)}\n"
               f"{loser_hp:,} HP [1;31m(-{damage})[0m\n"
               "```"),
        inline=True
    )

    embed.add_field(
        name="",
        value="",
        inline=True
    )

    embed.add_field(
        name=winner.user.name,
        value=f"{winner_grade}{winner.score:,}",
        inline=True
    )

    embed.add_field(
        name="Accuracy",
        value=f"{winner.play.acc:.2f}%",
        inline=True
    )

    embed.add_field(
        name="Combo",
        value=winner_combo,
        inline=True
    )

    embed.add_field(
        name=loser.user.name,
        value=f"{loser_grade}{loser.score:,}",
        inline=True
    )

    embed.add_field(
        name="Accuracy",
        value=f"{loser.play.acc:.2f}%",
        inline=True
    )

    embed.add_field(
        name="Combo",
        value=loser_combo,
        inline=True
    )

    embed.set_thumbnail(
        url=beatmap['url'])

    return embed
