import discord
from discord.ext import commands

class Showcase(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='showcase')
    async def showcase(self, ctx: commands.Context, *, msg):
        args = msg.split(' ')
        uid = args[0]
        char = ''
        if len(args) > 1: char = args[1]
        print(uid, char)