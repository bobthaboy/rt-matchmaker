from dataclasses import dataclass
from RhythmTyperAPI.models import Play
from discord import Member


@dataclass
class MatchState:
    hand1: list
    hand2: list
    available_maps: list
    flip: bool
    casual: bool
    is_achievements: dict
    start_time: float
    chooser: Member | None = None
    turn: int = 0
    player1_hp: int = 1_000_000
    player2_hp: int = 1_000_000


@dataclass
class Score:
    user: Member
    play: Play
    score: int
    damage: int | None = None
