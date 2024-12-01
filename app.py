import discord
from discord.ext import commands
from discord import app_commands
from tinydb import TinyDB, Query, JSONStorage
from tinydb.storages import MemoryStorage
import random
import string
from dotenv import load_dotenv
import os

# Load the .env file
load_dotenv()

# Get the bot token from the environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Function to load the database safely
def load_database(file_path):
    if os.path.exists(file_path):
        try:
            return TinyDB(file_path, storage=JSONStorage)
        except Exception as e:
            print(f"Error loading database: {e}. Resetting database.")
            with open(file_path, 'w') as f:
                f.write("{}")  # Reset file content
            return TinyDB(file_path, storage=JSONStorage)
    else:
        return TinyDB(file_path, storage=JSONStorage)

# Initialize TinyDB database
db = load_database('mail_system.json')
profiles_table = db.table('profiles')
mails_table = db.table('mails')

# Function to get a user's profile
def get_profile(user_id):
    Profile = Query()
    profile = profiles_table.search(Profile.user_id == str(user_id))
    return profile[0] if profile else None

# Function to save a user's profile
def save_profile(user_id, username, profile_code):
    Profile = Query()
    profiles_table.upsert(
        {'user_id': str(user_id), 'username': username, 'profile_code': profile_code},
        Profile.user_id == str(user_id)
    )

# Function to save a mail
def save_mail(user_id, sender_name, message):
    mails_table.insert({'user_id': str(user_id), 'sender_name': sender_name, 'message': message})

# Function to get all mails for a user
def get_mail(user_id):
    Mail = Query()
    mails = mails_table.search(Mail.user_id == str(user_id))
    return mails

# Discord bot setup
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Command to generate or view profile
@bot.tree.command(name="profile")
async def profile(interaction: discord.Interaction):
    """Display the user's profile code and store it in the database with fancy UI"""
    # Generate a 4-digit profile code
    profile_code = ''.join(random.choices(string.digits, k=4))

    # Save the profile code in the database
    save_profile(interaction.user.id, interaction.user.name, profile_code)

    # Create an embed with the user's profile information
    embed = discord.Embed(
        title=f"{interaction.user.name}'s Profile",
        description=f"Here is your profile code:\n**{profile_code}**",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else "")
    embed.set_footer(text="Profile Code is visible to others")
    await interaction.response.send_message(embed=embed, ephemeral=False)

# Command to send mail
@bot.tree.command(name="send")
async def send_mail(interaction: discord.Interaction, profile_code: str, message: str):
    """Send mail to another user using their profile code with fancy UI"""
    # Acknowledge the interaction first
    await interaction.response.defer(ephemeral=True)

    # Find the user by profile code
    Profile = Query()
    target_user = profiles_table.search(Profile.profile_code == profile_code)

    if target_user:
        target_user_id = target_user[0]['user_id']
        # Send a direct message to the target user
        try:
            target_user_obj = await bot.fetch_user(int(target_user_id))
            await target_user_obj.send(f"You have received a new mail from {interaction.user.name}:\n\n{message}")
            save_mail(target_user_id, interaction.user.name, message)

            # Success message
            embed = discord.Embed(
                title="Mail Sent!",
                description=f"Your message was successfully sent to {target_user_obj.name}.",
                color=discord.Color.green()
            )
            embed.set_footer(text="Thank you for using the mail system!")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send("User not found or could not be messaged.", ephemeral=True)
    else:
        await interaction.followup.send("Profile code not found.", ephemeral=True)

# Command to view received mail
@bot.tree.command(name="mail")
async def view_mail(interaction: discord.Interaction):
    """View any mail the user has received with fancy UI"""
    user_id = str(interaction.user.id)
    mails_list = get_mail(user_id)

    if mails_list:
        embed = discord.Embed(
            title="Your Mails",
            description="Here are your recent mails:",
            color=discord.Color.green()
        )
        for i, mail in enumerate(mails_list, 1):
            embed.add_field(name=f"Mail {i} from {mail['sender_name']}", value=mail['message'], inline=False)

        embed.set_footer(text="This is your private mailbox.")
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else "")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("You have no new mail.", ephemeral=True)

# Command to explore all authorized users
@bot.tree.command(name="explore")
async def explore(interaction: discord.Interaction):
    """Display all authorized users and their profile codes with fancy UI"""
    users = profiles_table.all()

    if not users:
        await interaction.response.send_message("No authorized users found.", ephemeral=True)
        return

    user_list = "\n".join([f"User: **{user['username']}** - Profile Code: **{user['profile_code']}**" for user in users])

    embed = discord.Embed(
        title="Authorized Users",
        description=user_list,
        color=discord.Color.purple()
    )
    embed.set_footer(text="These are the authorized users with their profile codes.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Run the bot
bot.run(DISCORD_TOKEN)
