import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from flask import Flask
from threading import Thread

# ---------------- CONFIG ----------------
BOTS_CONFIG = [
    {"name": "dinosaurs", "token_env": "DISCORD_TOKEN_DINOSAURS", "scoreboard_file": "dinosaurs_scoreboard.json", "channel_id": 1440123400524791921},
    {"name": "apocalypse", "token_env": "DISCORD_TOKEN_APOCALYPSE", "scoreboard_file": "apocalypse_scoreboard.json", "channel_id": 1405580337605644338},
    {"name": "aces", "token_env": "DISCORD_TOKEN_ACES", "scoreboard_file": "aces_scoreboard.json", "channel_id": 1441380119045210255},
    {"name": "reapers", "token_env": "DISCORD_TOKEN_REAPERS", "scoreboard_file": "reapers_scoreboard.json", "channel_id": 1405579980007669871},
    {"name": "scavengers", "token_env": "DISCORD_TOKEN_SCAVENGERS", "scoreboard_file": "scavengers_scoreboard.json", "channel_id": 1454386696526364774},
    {"name": "vikings", "token_env": "DISCORD_TOKEN_VIKINGS", "scoreboard_file": "vikings_scoreboard.json", "channel_id": 1441197273299161360},
]

ALLOWED_ROLES = ["admin", "captains"]
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------- FLASK KEEP-ALIVE ----------------
app = Flask("")

@app.route("/")
def home():
    return "Bot(s) are running!"

def run_flask():
    app.run(host="0.0.0.0", port=8000)

Thread(target=run_flask).start()

# ---------------- BOT FACTORY ----------------
def create_bot(config):
    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True
    intents.message_content = True

    bot = commands.Bot(command_prefix=None, intents=intents)
    tree = bot.tree

    scoreboard_path = os.path.join(DATA_DIR, config["scoreboard_file"])
    channel_id = config["channel_id"]
    bot_name = config["name"]

    if not os.path.exists(scoreboard_path):
        with open(scoreboard_path, "w") as f:
            json.dump({"wins":0,"losses":0,"map_wins":0,"map_losses":0}, f)

    def load_scoreboard():
        with open(scoreboard_path, "r") as f:
            return json.load(f)

    def save_scoreboard():
        with open(scoreboard_path, "w") as f:
            json.dump(scoreboard_data, f)

    scoreboard_data = load_scoreboard()
    scoreboard_message_id = None

    def has_role(member):
        return any(role.name.lower() in ALLOWED_ROLES for role in member.roles)

    def is_admin(member):
        return any(role.name.lower() == "admin" for role in member.roles)

    def get_ratio(w,l):
        if l==0: return f"{w:.2f}" if w>0 else "0"
        return f"{w/l:.2f}"

    def get_map_win_percent(mw,ml):
        t = mw+ml
        return "0%" if t==0 else f"{(mw/t)*100:.1f}%"

    def generate_scoreboard():
        return (
            f"**🏆 UGT {bot_name.capitalize()}'s Scoreboard**\n"
            f"Wins: {scoreboard_data['wins']}\n"
            f"Losses: {scoreboard_data['losses']}\n"
            f"W/L Ratio: {get_ratio(scoreboard_data['wins'],scoreboard_data['losses'])}\n"
            f"Map Wins: {scoreboard_data['map_wins']}\n"
            f"Map Losses: {scoreboard_data['map_losses']}\n"
            f"Map Win%: {get_map_win_percent(scoreboard_data['map_wins'],scoreboard_data['map_losses'])}\n"
            f"@everyone"
        )

    async def update_scoreboard():
        nonlocal scoreboard_message_id
        channel = bot.get_channel(channel_id)
        if channel and scoreboard_message_id:
            try:
                msg = await channel.fetch_message(scoreboard_message_id)
                await msg.edit(content=generate_scoreboard())
            except:
                scoreboard_message_id = None

    @bot.event
    async def on_ready():
        nonlocal scoreboard_message_id
        print(f"✅ {bot.user} is online!")

        channel = bot.get_channel(channel_id)
        async for msg in channel.history(limit=10):
            if msg.author == bot.user and f"**🏆 UGT {bot_name.capitalize()}'s Scoreboard**" in msg.content:
                scoreboard_message_id = msg.id
                break
        if scoreboard_message_id is None:
            msg = await channel.send(generate_scoreboard())
            scoreboard_message_id = msg.id

        await tree.sync()
        print(f"✅ {bot_name.capitalize()} slash commands synced")

    group = app_commands.Group(name=bot_name, description=f"{bot_name.capitalize()} scoreboard commands")
    tree.add_command(group)

    @group.command(name="add_maps")
    async def add_maps(interaction: discord.Interaction, map_wins: int, map_losses: int):
        if not has_role(interaction.user):
            await interaction.response.send_message("❌ No permission", ephemeral=True)
            return
        scoreboard_data["map_wins"] += map_wins
        scoreboard_data["map_losses"] += map_losses
        scoreboard_data["wins"] += map_wins>map_losses
        scoreboard_data["losses"] += map_wins<map_losses
        save_scoreboard()
        await update_scoreboard()
        await interaction.response.send_message("✅ Match added", ephemeral=True)

    @group.command(name="reset")
    async def reset_scoreboard(interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("❌ Only admins can reset the scoreboard.", ephemeral=True)
            return
        scoreboard_data.update({"wins":0,"losses":0,"map_wins":0,"map_losses":0})
        save_scoreboard()
        await update_scoreboard()
        await interaction.response.send_message("🧹 Scoreboard reset", ephemeral=True)

    return bot, config["token_env"]

# ---------------- MAIN ----------------
async def main():
    tasks = []
    for cfg in BOTS_CONFIG:
        bot, token_env = create_bot(cfg)
        token = os.getenv(token_env)
        if not token:
            print(f"⚠️ Token for {cfg['name']} not found in environment variables!")
        tasks.append(asyncio.create_task(bot.start(token)))
    await asyncio.gather(*tasks)

asyncio.run(main())