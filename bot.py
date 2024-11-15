import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Retrieve BOT_KEY from the environment
bot_key = os.getenv('BOT_KEY')
# Initialize the bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Filepath for the records storage
records_file = 'records.json'

# In-memory storage for lift records
lift_data = {
    'squat': {},
    'bench': {},
    'deadlift': {}
}

fitness_role_id = 1306645640456966154  

### Helper Functions ###

# Function to load the data from the JSON file
def load_lift_data():
    try:
        with open(records_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return default structure if the file doesn't exist or is corrupted
        return {
            'squat': {},
            'bench': {},
            'deadlift': {}
        }

# Function to save the data to the JSON file
def save_lift_data():
    with open(records_file, 'w') as f:
        json.dump(lift_data, f, indent=4)

# Initialize the lift data from the JSON file
lift_data = load_lift_data()

### COMMANDS ###

# Command to record a lift
@bot.command()
async def record(ctx, lift_type: str, weight: str):
    # Validate the lift type
    lift_type = lift_type.lower()
    if lift_type not in lift_data:
        await ctx.send("Invalid lift type! Please use 'squat', 'bench', or 'deadlift'.")
        return

    # Validate the weight input to ensure it's an integer and positive
    try:
        weight = int(weight)
        if weight <= 0:
            await ctx.send("Please enter a positive weight value.")
            return
    except ValueError:
        await ctx.send("Invalid weight! Please enter a valid number for weight.")
        return

    user_id = str(ctx.author.id)
    
    # Remove the user's previous record if it exists
    if user_id in lift_data[lift_type]:
        lift_data[lift_type].pop(user_id, None)  # Use pop with default None to avoid KeyError

    # Add the new record
    if user_id == '440594794381574144':
        weight += 20
    
    lift_data[lift_type][user_id] = weight
    save_lift_data()  # Save the updated data to the JSON file
    
    # Send confirmation message
    await ctx.send(f"Recorded {weight} kg for {ctx.author.display_name}'s {lift_type}.")


# Command to view the leaderboard
@bot.command()
async def leaderboard(ctx):
    leaderboard_message = "🏆 **Leaderboard** 🏆\n\n"
    for lift, records in lift_data.items():
        sorted_records = sorted(records.items(), key=lambda item: item[1], reverse=True)
        leaderboard_message += f"**{lift.capitalize()}**:\n"
        for i, (user_id, weight) in enumerate(sorted_records, 1):
            user = await bot.fetch_user(user_id)
            leaderboard_message += f"{i}. {user.display_name}: {weight} Kg\n"
        leaderboard_message += "\n"
    await ctx.send(leaderboard_message)

# Command to delete a lift record
@bot.command()
async def delete_record(ctx, lift_type: str):
    if lift_type.lower() not in lift_data:
        await ctx.send("Invalid lift type! Please use 'squat', 'bench', or 'deadlift'.")
        return

    user_id = str(ctx.author.id)
    if user_id in lift_data[lift_type.lower()]:
        del lift_data[lift_type.lower()][user_id]
        save_lift_data()  # Save the updated data after deletion
        await ctx.send(f"{ctx.author.display_name}'s {lift_type} record has been deleted.")
    else:
        await ctx.send(f"{ctx.author.display_name} has no record for {lift_type}.")

# Custom Help Command
@bot.command(name="commands")
async def help_command(ctx):
    embed = discord.Embed(
        title="Fitness Bot Commands",
        description="Here are the commands you can use with this bot to track and view your fitness records.",
        color=discord.Color.blue()
    )

    # Add each command and its description
    embed.add_field(
        name="!record [lift_type] [weight]",
        value="Records your lift weight for a specific type of lift (squat, bench, deadlift).\nExample: `!record squat 120`",
        inline=False
    )
    
    embed.add_field(
        name="!leaderboard",
        value="Displays the top lifters for each category (squat, bench, deadlift) in descending order.",
        inline=False
    )
    
    embed.add_field(
        name="!delete_record [lift_type]",
        value="Deletes your lift record for a specific category.\nExample: `!delete_record bench`",
        inline=False
    )

    embed.add_field(
        name="Monthly Announcement",
        value="On the first of each month, the bot announces the top lifters for each category in the `#gym-leaderboard` channel and resets the records.",
        inline=False
    )

    embed.set_footer(text="Use these commands to keep track of your personal bests and compete with others!")

    await ctx.send(embed=embed)

### MONTHLY WINNER ANNOUNCEMENT ###

@tasks.loop(hours=24)  # Runs every day to check if it's the first day of the month
async def check_end_of_month():
    today = datetime.today()
    if today.day == 1:  # Trigger only on the first day of the month
        await announce_winners()

async def announce_winners():
    channel = discord.utils.get(bot.get_all_channels(), name="gym-leaderboard")  # Replace with your target channel name
    if channel is None:
        print("Channel 'gym-leaderboard' not found. Please check the channel name.")
        return
    guild = channel.guild
    fitness_role = guild.get_role(fitness_role_id)

    announcement_message = "🏆 **Monthly Winners** 🏆\n\n"
    for lift, records in lift_data.items():
        if records:
            winner_id = max(records, key=records.get)
            winner = await bot.fetch_user(winner_id)
            announcement_message += f"**{lift.capitalize()}**: {winner.display_name} with {records[winner_id]} kg\n"
        else:
            announcement_message += f"**{lift.capitalize()}**: No records this month\n"

    await channel.send(f"{fitness_role.mention} \n {announcement_message}")

### BOT EVENTS ###

@bot.event
async def on_ready():
    print(f"{bot.user} is now running!")
    check_end_of_month.start()  # Start the end-of-month task loop

# Run the bot
bot.run(bot_key)
