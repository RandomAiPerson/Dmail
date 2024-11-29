import discord
from discord.ext import commands
from discord import app_commands
from tinydb import TinyDB, Query
import random
import string
from dotenv import load_dotenv
import os

# Load the .env file
load_dotenv()

# Get the bot token from the environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Initialize TinyDB database
db = TinyDB('mail_system.json')
profiles_table = db.table('profiles')
mails_table = db.table('mails')

# Function to get a user's profile
def get_profile(user_id):
    Profile = Query()
    profile = profiles_table.search(Profile.user_id == user_id)
    return profile[0] if profile else None

# Function to save a user's profile
def save_profile(user_id, username, profile_code):
    Profile = Query()
    profiles_table.upsert({'user_id': user_id, 'username': username, 'profile_code': profile_code}, Profile.user_id == user_id)

# Function to save a mail
def save_mail(user_id, sender_name, message):
    mails_table.insert({'user_id': user_id, 'sender_name': sender_name, 'message': message})

# Function to get all mails for a user
def get_mail(user_id):
    Mail = Query()
    mails = mails_table.search(Mail.user_id == user_id)
    return mails

# Discord bot setup
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Command to generate or view profile
@bot.tree.command(name="profile")
async def profile(interaction: discord.Interaction):
    """Display the user's profile code and store it in the database"""
    # Generate a 4-digit profile code
    profile_code = ''.join(random.choices(string.digits, k=4))

    # Save the profile code in the database
    save_profile(interaction.user.id, interaction.user.name, profile_code)

    # Respond with the user's profile code
    await interaction.response.send_message(f"Your profile code is: {profile_code}", ephemeral=True)

# Command to send mail
@bot.tree.command(name="send")
async def send_mail(interaction: discord.Interaction, profile_code: str, message: str):
    """Send mail to another user using their profile code"""
    # Acknowledge the interaction first to avoid the "Unknown interaction" error
    await interaction.response.defer(ephemeral=True)
    
    # Find the user by profile code
    Profile = Query()
    target_user = profiles_table.search(Profile.profile_code == profile_code)

    if target_user:
        target_user_id = target_user[0]['user_id']
        # Send a direct message to the target user
        try:
            target_user_obj = await bot.fetch_user(target_user_id)
            await target_user_obj.send(f"You have received a new mail from {interaction.user.name}:\n\n{message}")
            save_mail(target_user_id, interaction.user.name, message)
            await interaction.followup.send("Mail sent successfully!", ephemeral=True)
        except discord.NotFound:
            await interaction.followup.send("User not found or could not be messaged.", ephemeral=True)
    else:
        await interaction.followup.send("Profile code not found.", ephemeral=True)

# Command to view received mail (only viewable by the user)
@bot.tree.command(name="mail")
async def view_mail(interaction: discord.Interaction):
    """View any mail the user has received"""
    user_id = interaction.user.id
    mails_list = get_mail(user_id)

    if mails_list:
        embed = discord.Embed(title="Your Mails", description="Here are your recent mails:", color=discord.Color.green())
        for i, (mail) in enumerate(mails_list, 1):
            embed.add_field(name=f"Mail {i} from {mail['sender_name']}", value=mail['message'], inline=False)

        embed.set_footer(text="This is your private mailbox.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("You have no new mail.", ephemeral=True)

# Command to explore all authorized users
@bot.tree.command(name="explore")
async def explore(interaction: discord.Interaction):
    """Display all authorized users and their profile codes"""
    # Fetch all authorized users and their profile codes from the database
    users = profiles_table.all()

    # If there are no users, inform the caller
    if not users:
        await interaction.response.send_message("No authorized users found.", ephemeral=True)
        return

    # Create a message listing all users and their profile codes
    user_list = "\n".join([f"User ID: {user['user_id']} - Profile Code: {user['profile_code']}" for user in users])

    # Send the list as a message
    await interaction.response.send_message(f"Authorized Users:\n{user_list}", ephemeral=True)

bot.run(DISCORD_TOKEN)
