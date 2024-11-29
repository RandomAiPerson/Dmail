import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import string
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Setting up SQLite Database
def setup_db():
    conn = sqlite3.connect('mail_system.db')
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        profile_code TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS mails (
        mail_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        sender_name TEXT,
        message TEXT,
        FOREIGN KEY (user_id) REFERENCES profiles(user_id)
    )''')
    
    conn.commit()
    conn.close()

# Simulate profile and mail storage functions
def get_profile(user_id):
    conn = sqlite3.connect('mail_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM profiles WHERE user_id = ?', (user_id,))
    profile = cursor.fetchone()
    conn.close()
    return profile

def save_profile(user_id, username, profile_code):
    conn = sqlite3.connect('mail_system.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO profiles (user_id, username, profile_code) VALUES (?, ?, ?)',
                   (user_id, username, profile_code))
    conn.commit()
    conn.close()

def save_mail(user_id, sender_name, message):
    conn = sqlite3.connect('mail_system.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO mails (user_id, sender_name, message) VALUES (?, ?, ?)',
                   (user_id, sender_name, message))
    conn.commit()
    conn.close()

def get_mail(user_id):
    conn = sqlite3.connect('mail_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT sender_name, message FROM mails WHERE user_id = ?', (user_id,))
    mails = cursor.fetchall()
    conn.close()
    return mails

# Initialize the database
setup_db()

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
    conn = sqlite3.connect('mail_system.db')
    cursor = conn.cursor()
    cursor.execute('REPLACE INTO profiles (user_id, profile_code) VALUES (?, ?)', 
                   (interaction.user.id, profile_code))
    conn.commit()
    conn.close()

    # Respond with the user's profile code
    await interaction.response.send_message(f"Your profile code is: {profile_code}", ephemeral=True)

# Command to send mail
@bot.tree.command(name="send")
async def send_mail(interaction: discord.Interaction, profile_code: str, message: str):
    """Send mail to another user using their profile code"""
    # Acknowledge the interaction first to avoid the "Unknown interaction" error
    await interaction.response.defer(ephemeral=True)
    
    # Find the user by profile code
    conn = sqlite3.connect('mail_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM profiles WHERE profile_code = ?', (profile_code,))
    target_user = cursor.fetchone()
    conn.close()

    if target_user:
        target_user_id = target_user[0]
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
        for i, (sender, message) in enumerate(mails_list, 1):
            embed.add_field(name=f"Mail {i} from {sender}", value=message, inline=False)

        embed.set_footer(text="This is your private mailbox.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("You have no new mail.", ephemeral=True)

# Command to explore all authorized users
@bot.tree.command(name="explore")
async def explore(interaction: discord.Interaction):
    """Display all authorized users and their profile codes"""
    # Fetch all authorized users and their profile codes from the database
    conn = sqlite3.connect('mail_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, profile_code FROM profiles')
    users = cursor.fetchall()
    conn.close()

    # If there are no users, inform the caller
    if not users:
        await interaction.response.send_message("No authorized users found.", ephemeral=True)
        return

    # Create a message listing all users and their profile codes
    user_list = "\n".join([f"User ID: {user[0]} - Profile Code: {user[1]}" for user in users])

    # Send the list as a message
    await interaction.response.send_message(f"Authorized Users:\n{user_list}", ephemeral=True)

bot.run(os.getenv('BOT_TOKEN'))  # Use the bot token from the .env file
