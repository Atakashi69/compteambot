from discord.ext import commands, bridge

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @bridge.bridge_command(name='ping')
    async def ping(self, ctx):
        print(type(ctx))
        await ctx.respond(f"pong! **({round(self.bot.latency * 1000)}ms)**")
