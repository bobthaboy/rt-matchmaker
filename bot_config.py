from discord import Intents
from discord.ext import commands

intents = Intents.default()
intents.members = True  # noqa
intents.message_content = True  # noqa

bot = commands.Bot(command_prefix="!", intents=intents, owner_id=266086182650118144, help_command=None)
