import io
import asyncio
import time

import discord
from discord.ext import commands
from util.ginames import ginames

import json
import itertools
import datetime
import requests
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import as_completed
from requests_futures.sessions import FuturesSession


class Top(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='top')
    async def top(self, ctx: commands.Context, *, msg):
        args = msg.split(' ')
        charsIn = replaceChars([i for i in args if (not i.startswith('-') and not is_integer(i))])
        charsOut = replaceChars([i[1:] for i in args if i.startswith('-')])
        top_num = int(args[-1]) if is_integer(args[-1]) else 3
        top_num = min(max(1, top_num), 10)

        async with ctx.typing():
            file, embed = await getEmbed(charsIn, charsOut, top_num)
            await asyncio.sleep(0.1)

        if embed:
            await ctx.reply(file=file, embed=embed)
        else:
            await ctx.reply('Команд с выбраными персонажами не было найдено, либо первого персонажа нету в базе данных')

    @commands.slash_command(name='top', description='Топ команд с выбраными персонажами')
    async def top_slash(self, ctx: discord.ApplicationContext,
                        characters: discord.Option(str, "Персонажи, которых надо включить в подбор команд (Перечислять через пробел)", required=True),
                        excharacters: discord.Option(str, "Персонажи, которых надо исключить из подбора команд (Перечислять через пробел)", required=False),
                        top_num: discord.Option(int, "Количество команд, которое надо отобразить (по умолчанию 3)", required=False, default=3, min_value=1, max_value=10)):
        charsIn = replaceChars(characters.split(' '))
        charsOut = []
        if excharacters:
            charsOut = replaceChars(excharacters.split(' '))

        message = await ctx.respond('Ваш запрос обрабатывается, это займёт некоторое время :clock8:')

        file, embed = await getEmbed(charsIn, charsOut, top_num)
        if embed:
            await message.edit_original_response(content='', file=file, embed=embed)
        else:
            await message.edit_original_response(content='Команд с выбраными персонажами не было найдено, либо первого персонажа нету в базе данных')


async def getEmbed(charsIn: list, charsOut: list, top_num: int):
    keys_array, dps_array = await getSimulations(charsIn, charsOut, top_num)
    if len(keys_array) == 0:
        return None, None
    top_num = min(top_num, len(keys_array)) #top_num = maximum available comps

    with io.BytesIO() as image_binary:
        img = await getTopImage(keys_array, dps_array, top_num)
        img.save(image_binary, 'PNG')
        image_binary.seek(0)
        file = discord.File(fp=image_binary, filename='image.png')

    if top_num == 1:
        team_name = 'команда'
    elif top_num < 5:
        team_name = 'команды'
    else:
        team_name = 'команд'

    description = ''
    for i in range(len(keys_array)):
        description += f'{i + 1}. https://gcsim.app/v3/viewer/share/{keys_array[i]} [{round(dps_array[i])}]\n'

    embed = discord.Embed(title=f'Топ-{top_num} {team_name} с выбранными персонажами', description=description, color=discord.Color.random())
    embed.set_author(name=charsIn[0].capitalize(), icon_url=f'https://db.gcsim.app/api/assets/avatar/{charsIn[0]}.png', url=f'https://db.gcsim.app/db/{charsIn[0]}')
    embed.set_thumbnail(url=f'https://db.gcsim.app/api/assets/avatar/{charsIn[0]}.png')
    embed.set_image(url='attachment://image.png')
    embed.set_footer(text=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    return file, embed


async def getTopImage(keys_array: list, dps_array: list, top_num: int):
    bg = Image.open('cmds/images/top.png')
    rect_width = 700
    rect_height = 195
    margin_out = 50
    margin_in = 10
    bg = bg.crop((0, 0, bg.width, (rect_height + margin_out) * top_num + margin_out))

    draw = ImageDraw.Draw(bg)
    futures = await getImagesData(keys_array)
    for i in range(top_num):
        res = next((x.result() for x in futures if x.key == keys_array[i]), None)
        img = Image.open(res.raw)
        img = img.crop((0, 0, img.width, 175)).convert('RGBA')
        img_pos = (margin_out + margin_in, (img.height + margin_in) * i + (margin_out + margin_in) * (i + 1))
        bg.paste(img, img_pos, img)

        txt_len = len(str(round(dps_array[i])))
        if txt_len < 5:
            font_size = 48
        elif txt_len < 6:
            font_size = 40
        else:
            font_size = 32

        font = ImageFont.truetype('cmds/fonts/hyv.ttf', font_size)
        txt = str(f'DPS\n{round(dps_array[i])}')
        txt_pos = ((bg.width - margin_out - margin_in) - (rect_width - img.width - margin_in * 2) / 2, img_pos[1] + img.height / 2)
        draw.text(xy=txt_pos, text=txt, fill=(255, 255, 255), font=font, anchor='mm', align='center')
    return bg


async def getImagesData(keys_array: list):
    api_preview_url = 'https://gcsim.app/api/preview/'
    with FuturesSession(max_workers=len(keys_array)) as session:
        futures = []
        for key in keys_array:
            future = session.get(f'{api_preview_url}{key}', stream=True)
            future.key = key
            futures.append(future)
        return [future for future in as_completed(futures)]


# return two lists, first is top simulations keys and second is top simulations dps
async def getSimulations(charsIn: list, charsOut: list, top_num: int):
    api_char_url = 'https://db.gcsim.app/api/db/'
    response = requests.get(url=api_char_url + charsIn[0]).json()
    simulations = dict()  # sim_key:mean_dps
    for sim in response:
        metadata = json.loads(sim['metadata'])

        if not all(item in metadata['char_names'] for item in charsIn):
            continue
        if any(item in metadata['char_names'] for item in charsOut):
            continue

        mean_dps = 0
        for target_key in metadata['dps_by_target']:
            mean_dps += metadata['dps_by_target'][target_key]['mean']
        mean_dps /= len(metadata['dps_by_target'])
        simulations[sim['simulation_key']] = mean_dps

    simulations = dict(
        sorted(simulations.items(), key=lambda item: item[1], reverse=True))
    return list(itertools.islice(simulations.keys(), top_num)), list(itertools.islice(simulations.values(), top_num))


def replaceChars(charsList: list):
    for i in range(len(charsList)):
        for char in ginames.items():
            if charsList[i].lower() in [x.lower() for x in char[1]]:
                charsList[i] = char[0]
                break
    return charsList


def is_integer(n: any):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()
