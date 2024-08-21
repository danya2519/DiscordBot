import discord
from discord.ext import commands
from discord.utils import get
from datetime import datetime
import os
import aiofiles
from openai import OpenAI
import asyncio


TOKEN = ''
#TOKEN = ''
GUILD_ID = 1214331896025055232
CHANNEL_ID = 1222935955208671323
ALLOWED_ROLES_REPORT = [1222664800648040449, 1224088403470061618, 1222940972976050267,1222679827778240653, 1223033731304919201, 1223033938352541766, 1223034233480675388, 1223034443347001465]
ALLOWED_ROLES_ADMIN_REPORT = [1222664800648040449, 1224088403470061618, 1222940972976050267,1222679827778240653, 1223033731304919201]
FOR_PROMT = "попробуй отыграть такую роль: ты являешься ботом на одном дискорд сервере по игре 'scp sl',"
RULES_OF_SERVER = "вот тебе список правил дискорд сервера: ОБРАШАЙСЯ К НИМ КОГДА ПОЛЬЗОВАТЕЛЬ ХОЧЕТ УЗНАТЬ О ПРАВИЛАХ 'Правила Discord сервера Заходя на сервер, Вы автоматически соглашаетесь с правилами ниже: [1] Неподобающее поведение. Запрещено оскорблять пользователей или проект.Запрещено разжигание межнациональной розни.Запрещены оскорбления или провокации в сторону других существующих проектов или серверов.Оскорбление определяется по лексическому значению. [2] Спам, NSFW контент.Запрещён спам и NSFW контент в любых текстовых каналах.Распространяется на все текстовые и голосовые каналы,Распространяется на аватарки, ники, описание профиля, статусы, баннеры. [3] Раздражительные звуки в голосовых каналах.Запрещено перезаходить намерено в голосовые каналы.Спам через: Soundpad, Soundboard или подобные программы.Запрещены громкие и раздражительные звуки. [4] Реклама.Запрещено рекламировать существующие проекты, за исключением: Балдёжников, SCP:SL и сайт Фонда SCP. [5] Киберпреступления.Запрещено распространять ссылки с целью фишинга.Запрещено использование вредоносное ПО.Запрещено распространение вредоносного ПО, читов. [6] Обход наказаний. Запрещено любыми способами обходить наказания. Любые альтернативные аккаунты будут заблокированы вместе с основным.[7] Упоминание должностных ролей. Запрещается упоминать должностные роли без веской причины. Разрешаться упоминать роль в тикетах жалоб 'ссылка на один из каналов', придерживаясь инструкций."

role_bot = "assistant"

intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.presences = True
intents.guilds = True
intents.messages = True
intents.bans = True

client = OpenAI(
    api_key = ""
)

OpenAI.api_key = ""

bot = commands.Bot(command_prefix='!', intents=intents)

ticket_limits = {}
EMOJI_TO_TICKET_TYPE = {
    '1224027672921772134': 'player_report',
    '1224023170776825928': 'tech_support',
    '1224022638544945224': 'ban_appeal',
    '1224081932296650852': 'admin_report'
}


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    #await status()
    #user = await bot.fetch_user(776754698883170304)
    #await ctx.guild.unban(user)
    

async def create_ticket_channel(guild, ticket_type, member):
    category_names = {
        'player_report': 'Жалобы_на_игроков',
        'tech_support': 'Техподдержка',
        'ban_appeal': 'Бан_апилы',
        'admin_report': 'Жалобы_на_администрацию'
    }

    category_name = category_names.get(ticket_type)
    if not category_name:
        print("Invalid ticket type.")
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    if category_name == "Жалобы_на_игроков" or category_name == "Бан_апилы":
        for role_id in ALLOWED_ROLES_REPORT:
            role = guild.get_role(role_id)
            overwrites[role] = discord.PermissionOverwrite(read_messages=True)
    else:
        for role_id in ALLOWED_ROLES_ADMIN_REPORT:
            role = guild.get_role(role_id)
            overwrites[role] = discord.PermissionOverwrite(read_messages=True)
    
    overwrites[member] = discord.PermissionOverwrite(read_messages=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_channel_name = f'{ticket_type}-{timestamp}'

    try:
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name)
        new_channel = await category.create_text_channel(name=new_channel_name, overwrites=overwrites)
    except discord.HTTPException as e:
        print(f"Failed to create channel: {e}")
        return None

    return new_channel

@bot.event
async def on_raw_reaction_add(payload):
    if payload.guild_id == GUILD_ID and payload.channel_id == CHANNEL_ID:
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            print("Guild not found.")
            return

        channel = bot.get_channel(payload.channel_id)
        if not channel:
            print("Channel not found.")
            return

        message = await channel.fetch_message(payload.message_id)
        if not message:
            print("Message not found.")
            return

        emoji_id = str(payload.emoji.id)
        ticket_type = EMOJI_TO_TICKET_TYPE.get(emoji_id)
        if not ticket_type:
            print("Ticket type not found.")
            return

        member = guild.get_member(payload.user_id)
        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.HTTPException as e:
                print(f"Failed to fetch member: {e}")
                return

        if member.id not in ticket_limits:
            ticket_limits[member.id] = {}
        if ticket_type not in ticket_limits[member.id]:
            ticket_limits[member.id][ticket_type] = 0

        if ticket_limits[member.id][ticket_type] >= 3:
            print("Ticket limit reached.")
            return

        new_category = await create_ticket_channel(guild, ticket_type, member)
        if not new_category:
            print("Failed to create ticket category.")
            return

        welcome_messages = {
            'player_report': (
                f'{member.mention}\nЗдравствуйте, пожалуйста, опишите вашу проблему.\n```ini\n'
                f'При подаче жалобы на игрока, обязательно указывайте [ник пострадавшего], если он отличается от ника в Discord,\n'
                f'[Steam профиль нарушителя], [номер сервера] и распишите [причину жалобы], по возможности прикрепите видеодоказательства, чтобы администраторы могли оперативнее отреагировать на неё.\n```'
            ),
            'tech_support': (
                f'{member.mention}\nЗдравствуйте, пожалуйста, опишите вашу проблему.\n'
            ),
            'ban_appeal': (
                f'{member.mention}\nЗдравствуйте, предоставьте ссылку на ваш Steam профиль и ожидайте ответа.\n'
            ),
            'admin_report': (
                f'{member.mention}\nЗдравствуйте, пожалуйста, опишите вашу жалобу.\n```ini\n'
                f'Для подачи репорта на администрацию предоставьте видео и ник/стим профиль игрока\n'
                f'Если же видео док-ва у вас отсутствует опишите вашу жалобу как можно подробнее\n```'
            )
        }
        welcome_message = welcome_messages.get(ticket_type)

        await new_category.send(welcome_message)

        try:
            await message.remove_reaction(payload.emoji, member)
        except discord.HTTPException as e:
            print(f"Failed to remove reaction: {e}")

        ticket_limits[member.id][ticket_type] += 1

#@bot.event
#async def on_member_join(ctx, member):
#    channel_for_message = bot.get_channel(1226623644197720124)
#    await channel_for_message.send("Добро пожаловать, <@" + str(member.id) + >)

@bot.event
async def on_message(message):
    # отчёт о бане
    if message.channel.id == 1225479292356399114:
        async for last_message in message.channel.history(limit=1):
            print(last_message)
    # возврат.
    if message.author.id == 776754698883170304 and message.mentions and message.mentions[0].id == 1224032173246644284 and message.channel.id == 1227656528392093798:
        role = discord.utils.get(message.guild.roles, id=1222679827778240653)
        await message.author.add_roles(role)
        await message.add_reaction(":Complete:1226852120670507040")
        await message.delete()
    # bot_O5 + ст. ад.
    if message.channel.id == 1225874165538619402 or message.channel.id == 1225425252591603752:
        mentioned_roles = message.role_mentions
        if mentioned_roles:
            mentioned_users = message.mentions
            for user in mentioned_users:
                for role in mentioned_roles:
                    if message.author.id == 776754698883170304 or message.author.top_role > role:
                        if role in user.roles:
                            if user.id == 776754698883170304 and role == user.top_role and message.author.id != 776754698883170304:
                                await message.channel.send(message.author.mention + " даже не пытайся")
                                await message.add_reaction(":Pepe_Clown:1225539333654843564")
                            else:
                                await user.remove_roles(role)
                                await message.add_reaction(":Rejection:1226853031577124875")
                        else:
                            await user.add_roles(role)
                            await message.add_reaction(":Complete:1226852120670507040")
                    else:
                        id_to_ping = str(message.author.id)
                        await message.channel.send("<@" + id_to_ping + "> у вас недостаточно прав, анлак")

    # бот отдела безопасности
    if message.channel.id == 1227293918761058424:
        if message.mentions:
            async for last_message in message.channel.history(limit=1):
                await message.mentions[0].send("Здравствуйте, Вам был выдан варн по пункту " + str(last_message.content).replace("<@" + str(last_message.mentions[0].id) + ">", "").replace(" ", "") + " нашего дискорд сервера, не нарушайте")
                await message.add_reaction(":Complete:1226852120670507040")

    # 079
    if message.channel.id == 1227350330447233116 or message.channel.id == 1227341954841313280:
        if message.mentions and message.mentions[0].id == 1224032173246644284 and message.author.id != 1224032173246644284:
            try:
                async for last_message in message.channel.history(limit=1):
                    await message.add_reaction("a:XVo6:1228003166759555205")
                    if "!картинка" in last_message.content:
                        prompt = str(last_message.content).replace("<@1224032173246644284> !картинка", "")
                        response = client.images.generate(prompt=prompt, model="dall-e-3")
                        image_url = response.data[0].url
                        await message.channel.send("<@" + str(message.author.id) + "> " + str(image_url))
                
                    else:
                        async for last_message in message.channel.history(limit=1):
                            prompt = FOR_PROMT + ", СТАРАЙСЯ ШУТИТЬ ПОЧТИ В КАЖДОМ СООБЩЕНИЕ, вот тебе правила дискорд сервера - " + RULES_OF_SERVER + ". тебя упоминает другой пользователь, ОТВЕТЬ НА ЕГО СООБЩЕНИЕ - " + str(last_message.content).replace("<@" + str(last_message.mentions[0].id) + ">", "")
                        chat_completion = client.chat.completions.create(
                            messages=[
                                {
                                    "role":role_bot,
                                    "content":prompt
                                }
                            ],
                            model = "gpt-3.5-turbo"
                        )
                        answer = chat_completion.choices[0].message.content
                        await message.channel.send("<@" + str(message.author.id) + "> " + answer)
                await message.clear_reactions()
            except:
                await message.clear_reactions()
                await message.add_reaction(":Rejection:1226853031577124875")

    # команда delete
    if message.author.id == 718540160840761414 or message.author.id == 776754698883170304:
        async for last_message in message.channel.history(limit=1):
            if "#delete" in last_message.content:
                massage_comand_number = str(last_message.content).replace("#delete ", "")
                async for last_message in message.channel.history(limit=int(massage_comand_number)):
                    await last_message.delete()

    # remote_bot_control
    if message.channel.id == 1225415507319062569:
        if message.mentions:
            member = message.mentions[0]
            if member.id == 776754698883170304:
                if message.author.id != 1224032173246644284:
                    await message.channel.send(message.author.mention + " даже не пытайся")
                    await message.add_reaction(":Rejection:1226853031577124875")
            else:
                if member and message.author.id != 1224032173246644284:
                    if message.author.id == 776754698883170304 or member.top_role < message.author.top_role:
                        print(f'Участник {member.mention} был забанен')
                        try:
                            await message.guild.ban(member, reason='По требованию администратора')
                            async for last_message in message.channel.history(limit=1):
                                RULE_NUMBER = str(last_message.content).replace("<@" + str(last_message.mentions[0].id) + ">", "")
                                await message.mentions[0].send("Здравствуйте, Вы были забанены из-за нарушения пункта " + RULE_NUMBER + " нашего дискорд сервера, разбан можете купить у <@718540160840761414>")
                            await message.add_reaction(":Complete:1226852120670507040")
                            channel_for_ban = bot.get_channel(1224010064923463843)
                            await channel_for_ban.send("\n[1] <@" + str(member.id) + "> " + str(member.id) + "\n[2] пункт " + RULE_NUMBER + "\n[3] бан\n[4] #запрос_блокировки")

                        except discord.Forbidden:
                            await message.channel.send('У меня нет прав на бан пользователей.')

                    else:
                        id_to_ping = str(message.author.id)
                        await message.add_reaction(":Rejection:1226853031577124875")
        return
    # закрытие тикетов
    if len(message.mentions) > 0 and message.mentions[0].id == 1224032173246644284:
        if isinstance(message.channel, discord.TextChannel):
            ticket_type = message.channel.name.split('-', 1)[0]
            if ticket_type in EMOJI_TO_TICKET_TYPE.values() and any(role.id in ALLOWED_ROLES_REPORT for role in message.author.roles):
                #Create_Txt_Document(message.channel.history(limit=200), message.channel.name)
                #fileName = "C:\\Users\\user\\Downloads\\" + message.channel.name + ".txt"
                fileName = message.channel.name + ".txt"
                lines_list = []
                async with aiofiles.open(fileName, 'w') as f:
                    users_in_ticket = []
                    users_in_ticket.append("<@" + str(message.author.id) + "> ")
                    async for message in message.channel.history(limit=200):
                        await f.write("[" + str(message.created_at) + "]" + " (" + message.author.name + "):" + message.content + "\n")
                        if not "<@" + str(message.author.id) + "> " in users_in_ticket:
                            users_in_ticket.append("<@" + str(message.author.id) + "> ")
                async with aiofiles.open(fileName, 'r') as f:
                    lines = await f.read()
                    lines_list = str(lines).split("\n") 
                    
                os.remove(fileName)
                async with aiofiles.open(fileName, 'w') as f:
                    lines_list = lines_list[::-1]
                    for line in range(len(lines_list)):
                        await f.write(str(lines_list[line]) + "\n")

                channel = bot.get_channel(1226606076078854316)
                await channel.send(str(users_in_ticket),file=discord.File(fileName))
                await message.channel.delete()
                #os.remove(fileName)
                return
        else:
            await message.channel.send("Эта команда должна быть отправлена в текстовом канале тикета.")
            return

    await bot.process_commands(message)

@bot.command()
async def unban(ctx, member: discord.Member):
    if ctx.channel.id == 1225415507319062569:
        if ctx.author.guild_permissions.ban_members:
            banned_users = await ctx.guild.bans()
            for entry in banned_users:
                if entry.user == member:
                    try:
                        await ctx.guild.unban(entry.user)
                        await ctx.send(f'{member.mention} был успешно разбанен.')
                        return
                    except discord.Forbidden:
                        await ctx.send(f'У бота недостаточно прав для разбана пользователя {member.mention}.')
            await ctx.send("Пользователь не найден в списке забаненных.")
        else:
            await ctx.send("У вас недостаточно прав для выполнения этой команды.")
    else:
        await ctx.send("Эта команда должна быть вызвана только из определенного канала.")

async def Create_Txt_Document(massages , channel_Name):
    fileName = channel_Name + ".txt"
    with open(fileName, 'w') as f:
        for i in range(len(massages)):
            f.write(str(massages[i]) + "/n")
            channel = bot.channels.get("id", 1226606076078854316)
            await message.channel.send(open(fileName, 'a'))
            os.remove(fileName)

async def status():
    while True:
        guild = bot.get_guild(1214331896025055232)
        member = guild.get_member(1222933494385082468)
        rawStatus = member.activity
        if(rawStatus != None):
            status = str(rawStatus).replace("online", "игроков")
            #activity = discord.Activity(type=discord.ActivityType.custom, name="мой создатель пидорасs")
            await bot.change_presence(activity=discord.Game(name="слежка за порядком на сервере: " + status))
        else:
            await bot.change_presence(activity=discord.Game(name="ч̶̴и̶҉н҉҉и҉т̶ с̶̶е̶̵р҈в̶҉е̴̷р̷а҉҉"))
        await asyncio.sleep(2)


bot.run(TOKEN)
