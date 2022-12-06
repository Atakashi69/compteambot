from config import cfg
import discord
from discord.ext import bridge

from cmds import ping, top, showcase

bot = bridge.Bot(intents=discord.Intents.all(), command_prefix=cfg['prefix'])

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

bot.add_cog(ping.Ping(bot))
bot.add_cog(top.Top(bot))
bot.add_cog(showcase.Showcase(bot))

bot.run(cfg['token'])
