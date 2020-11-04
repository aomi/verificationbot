import json
import os.path as osp
import smtplib
import ssl
from random import randint

import discord
from discord.ext import commands
from discord.ext.commands import errors as cmderr

from util.data.guild_data import GuildData  # for reactors


print("Starting...")


# Initialize the variables to hold config data. DO NOT MODIFY THESE PRESETS! Use the config.json file instead.
# If you don't have a config.json file created yet, don't panic! Run the bot.py file and one will automatically be created.
bot_token = "bot.token" 				# The Discord bot token being used. Do not share this!
bot_key = "$"							# The command prefix used by the bot. Defaults to '$'.
role = "role_name"						# The role given to members who successfully verify.
verify_domain = "email.com"				# The email domain checked against (i.e., for a gmail account would be gmail.com).
email_from = "email@email.com"			# The email account used by the bot to send emails.
email_password = "password"				# The password for the email account. Required to log in.
email_subject = "Verify Email"			# The subject of emails being sent by the bot.
email_server = "smtp.gmail.com"			# The SMTP server emails are sent from. The Gmail one is provided.
email_port = "465"						# The port of the SMTP server above. The Gmail one is provided.
channel_id = 1234567890					# The channel id for the verification channel.
notify_id = 1234567890					# The channel id for a channel for bot alerts (i.e. a mod-only channel)
used_emails = "used_emails.txt"			# The filename for the file that stores previously used emails.
warn_emails = "exchange_emails.txt"		# The filename for a file (not needed) for alerting mods if used.
admin_id = 1234567890					# The user id for a user to ping if an email is already used.
author_name = "Student"					# The name sent addressing the person in the email
moderator_email = "email@email.com"		# The moderator email to contact in the sent email


current_dir = osp.dirname(__file__)  # grab the current system directory on an os-independent level
data_path = "data"  # folder name
config_name = "config.json"  # config file name

# Uncomment the line below (and comment the line below it) if you want to use the data folder to store the config file.
#config_path = osp.join(current_dir, data, config_name)
config_path = config_name


#Create a struct to hold json data and associate with variables.
def_config = {
	"bot_token": bot_token,
	"bot_key": bot_key,
	"role": role,
	"verify_domain": verify_domain,
	"email_from": email_from,
	"email_password": email_password,
	"email_subject": email_subject,
	"email_server": email_server,
	"email_port": email_port,
	"channel_id": channel_id,
	"notify_id": notify_id,
	"used_emails": used_emails,
	"warn_emails": warn_emails,
	"admin_id": admin_id,
	"author_name": author_name,
	"moderator_email": moderator_email
}


#Create empty lists for currently active tokens, emails, and attempt rejection.
token_list = {}
email_list = {}
email_attempts = {}
verify_attempts = {}


#Load new intents system. This is required for the new reactors functionality.
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.reactions = True


#Start the bot functions.
do_run = True


#Start config loading from disk.
print("Loading config...")
if osp.isfile(config_path):
	with open(config_path, 'r') as file:
		data = json.load(file)
		bot_token = data["bot_token"]
		bot_key = data["bot_key"]
		role = data["role"]
		verify_domain = data["verify_domain"]
		email_from = data["email_from"]
		email_password = data["email_password"]
		email_subject = data["email_subject"]
		email_server = data["email_server"]
		email_port = data["email_port"]
		channel_id = data["channel_id"]
		notify_id = data["notify_id"]
		used_emails = data["used_emails"]
		warn_emails = data["warn_emails"]
		admin_id = data["admin_id"]
		author_name = data["author_name"]
		moderator_email = data["moderator_email"]
		print("Config loaded.")
else:
	with open(config_path, 'w') as file:
		print("Config file not found, creating...")
		json.dump(def_config, file, indent=4)  # This creates a blank json file for storing the config.
		print("Config file created.")
		do_run = False  # Bot shuts down to allow the config to be written.


# From the used_emails filename, load the data from the data folder. This can be commented out if not using a data folder.
used_emails = osp.join(current_dir, data_path, used_emails)


# Set up the bot based on the loaded bot prefix and load the intents system.
bot = commands.Bot(command_prefix=bot_key, intents=intents)


# By default, there's no help command other than vhelp. This is so that it doesn't interfere with other bots using the same prefix.
bot.remove_command('help')


# Update discord presence when everything is successfully loaded.
@bot.event
async def on_ready():
	await bot.change_presence(activity=discord.Activity(name="verifications", type=discord.ActivityType.watching))
	print(f'We have logged in as {bot.user}')


# Set up per-message checks.
@bot.event
async def on_message(message):
	if message.author == bot.user:
		return
	await bot.process_commands(message)


# Exception handling.
@bot.event
async def on_command_error(ctx, exception):
	if isinstance(exception, cmderr.PrivateMessageOnly):
		await ctx.send("Please DM the bot to use this command!")
	elif isinstance(exception, cmderr.NoPrivateMessage):
		await ctx.channel.send("This command must be used in a Discord server!")
	elif isinstance(exception, cmderr.MissingRole):
		await ctx.channel.send("Missing required role to use this command!")
	elif isinstance(exception, cmderr.MissingRequiredArgument):
		await ctx.channel.send("Missing required arguments!")
	else:
		print(exception)


# Instructions on how to verify.
@bot.command(name="vhelp", aliases=["helpme", "help_me", "verify_help", "Vhelp", "Helpme", "Help_me", "Verify_help"])
async def verify_help(ctx):
	"""
	Help on how to verify.
	"""
	verify_email = ctx.guild.get_channel(channel_id)
	# The line below contains the verify_help command text output.
	await ctx.send(f"To use this bot, please use `{bot_key}email netlinkid@{verify_domain}` in {verify_email.mention} to receive an email with a **4 digit verification token.** Replace `netlinkedid@{verify_domain}` with your own email, keeping in mind that the bot only accepts email addresses with `@{verify_domain}` at the end. **Wait for an email to be received** - you can check your UVic Webmail at https://uvic.ca/webmail/. If you don't receive an email after 5 minutes, try using the email command again. **Send the command provided in the email** as a message in the {verify_email.mention} channel to gain access to the rest of the server.\n\n**Send messages in the {verify_email.mention} channel to use this bot's commands, not in a DM.**")


# The email command handles all the checks done before an email is sent out alongside the actual email sending.
# It's very complicated.
@bot.command(name="email", aliases=["mail", "send", "Email", "Mail", "Send"])
async def _email(ctx, arg):
	if ctx.channel.id == channel_id:
		"""
		Sends an email containing a token to verify the user
		Parameters
		------------
		email: str [Required]
			The email that the token will be send to.
		"""
		print(f'Emailing user {ctx.author.name}, email {arg}')  # This gets sent to the console only.
		await ctx.message.delete()  # delete their email from the channel, to prevent it leaking.

		dm = "teststring"  # just in case, though this should never actually get used.

		try:
			dm = arg.split('@')[1]  # split the string based on the @ symbol
		except:
			await ctx.send("Error! That is not a valid email!")  # no @ symbol = no email

		if set('+').intersection(arg):  # to prevent people from making extra email addresses
			dm = "nou"
			await ctx.send("Error! Please do not use the + character in your email address!")

		blacklist_names = ["netlinkid", "v00"]  # If any email begins with one of these, it's invalid

		if any(arg.lower().startswith(name.lower()) for name in blacklist_names):
			await ctx.send(
				f"{ctx.author.mention} Use your own NetLinkID (your username in Brightspace), not the default one. Please try again with your own email.")
			return

		try:
			with open(used_emails, 'r') as file:  # Checks the used emails file to see if the email has been used.
				if any(str(arg.lower()) == str(line).strip('\n').lower() for line in file):
					admin = await bot.fetch_user(admin_id)
					await ctx.send(
						f"Error! That email has already been used! If you believe this is an error or are trying to re-verify, please contact {admin.mention} in this channel or through direct message. Thanks!")
					return
		except FileNotFoundError:
			print("Used emails file hasn't been created yet, continuing...")

		try:
			with open(warn_emails, 'r') as file:  # Checks the warning email file to notify moderators if an email on the list is used. For example, a list of professor emails could be loaded.
				if any(str(arg.lower()) == str(line).strip('\n').lower() for line in file):
					sendIn = ctx.guild.get_channel(notify_id)
					await sendIn.send(f"Alert! Email on warning list used. Discord ID: {ctx.author.mention}, email `{arg}`. Please use https://www.uvic.ca/search/people/index.php to check status.")
		except FileNotFoundError:
			print("Warning list file not found, ignoring rest.")

		#This is a bit of a hacky way to do an email attempt checking system. If someone tries to repeatedly use the email command, they will be blacklisted from further attempts.
		try:
			if email_attempts[ctx.author.id] >= 5:
				await ctx.send(f"{ctx.author.mention}, you have exceeded the maximum number of command uses. Please contact a moderator for assistance with verifying if this is in error. Thanks!")
				sendIn = ctx.guild.get_channel(notify_id)
				await sendIn.send(f"Alert! User {ctx.author.mention} has exceeded the amount of `!email` command uses.")
				return
		except:
			print("")

		if dm == verify_domain:  # Send the actual email.
			await ctx.send("Sending verification email...")
			with smtplib.SMTP_SSL(email_server, email_port, context=ssl.create_default_context()) as server:
				server.login(email_from, email_password)
				token = randint(1000, 9999)
				token_list[ctx.author.id] = str(token)
				email_list[ctx.author.id] = arg
				verify_email = ctx.guild.get_channel(channel_id)
				message_text = f"Hello {author_name},\n\nThe command to use in {verify_email.mention} is: \n\n{bot_key}verify {token}\n\nMake sure you paste that entire line into the chat, and press enter to send the message. \n\nThank you for joining our Discord server! \n\nThis message was sent automatically by a bot. If you did not request this message, please contact {moderator_email} to report this incident."
				message = f"Subject: {email_subject}\n\n{message_text}"
				server.sendmail(email_from, arg, message)
				server.quit()
			await ctx.send(f"Verification email sent, do `{bot_key}verify ####`, where `####` is the token, to verify.")

			if email_attempts:
				if ctx.author.id in email_attempts:
					email_attempts[ctx.author.id] += 1
				else:
					email_attempts[ctx.author.id] = 1
			else:
				email_attempts[ctx.author.id] = 1

		else:
			await ctx.send(f"Invalid email {ctx.author.mention}!")


@bot.command(name="verify", aliases=["token", "Verify", "Token"])
@commands.guild_only()
async def _verify(ctx, arg):
	"""
	Verifies a user with a token that was previously email.
	For use after the 'email' command.
	Parameters
	------------
	token: int [Required]
		The token that was sent to the user via email.
	"""
	if ctx.channel.id == channel_id:
		print(f'Verifying user {ctx.author.name}, token {arg}')
		await ctx.message.delete()

		# this is copied from above to avoid an issue where two people could use the same email before it was verified.
		try:
			with open(used_emails, 'r') as file:  # Checks the used emails file to see if the email has been used.
				if any(str(arg.lower()) == str(line).strip('\n').lower() for line in file):
					await ctx.send(
						f"Error! That email has already been used! If you believe this is an error or are trying to re-verify, please contact a moderator in this channel or through direct message. Thanks!")
					return
		except FileNotFoundError:
			print("Used emails file hasn't been created yet, continuing...")

		try:
			if verify_attempts[ctx.author.id] >= 5:
				await ctx.send(
					f"{ctx.author.mention}, you have exceeded the maximum number of command uses. Please contact a moderator for assistance with verifying if this is in error. Thanks!")
				sendIn = ctx.guild.get_channel(notify_id)
				await sendIn.send(f"Alert! User {ctx.author.mention} has exceeded the amount of `!verify` command uses.")
				return
		except:
			print("")

		if token_list:
			if token_list[ctx.author.id] == arg:
				await ctx.send(f"{ctx.author.mention}, you've been verified!")
				await ctx.author.add_roles(discord.utils.get(ctx.message.author.guild.roles, name=role))
				with open(used_emails, 'a') as file:  # Writes used emails to file for verification
					file.write(f"{email_list[ctx.author.id]}\n")
				if verify_attempts:
					if ctx.author.id in verify_attempts:
						verify_attempts[ctx.author.id] += 1
					else:
						verify_attempts[ctx.author.id] = 1
				else:
					verify_attempts[ctx.author.id] = 1
			else:
				await ctx.send(f"Invalid token {ctx.author.mention}!")
		else:
			print("Array does not exist yet! Verify will return nothing!")


@bot.command(name="prune", aliases=["purge", "nuke", "Prune", "Purge", "Nuke"])
@commands.has_permissions(manage_messages=True)
@commands.guild_only()
async def prune(ctx, amt: int):
	"""Bulk delete messages (up to 100)"""
	if not amt > 0 and amt <= 100:
		await ctx.send(f'Amount must be between **0** and **100**, you entered `{amt}`')
		return
	await ctx.message.delete()
	await ctx.channel.purge(limit=amt)
	msg = await ctx.send(f'Pruned `{amt}` messages.')
	await msg.delete(delay=3)


@bot.command(name="reactoradd", aliases=["Reactoradd"])
@commands.has_permissions(manage_guild=True)
@commands.cooldown(1, 2, commands.BucketType.user)
@commands.guild_only()
async def reactor_add(ctx, message_id: int, role_id: int, emoji: str):
	"""Add a reactor message."""
	await ctx.message.delete()

	if not ctx.guild.get_role(role_id):
		await ctx.send("Role not found!", delete_after=10)
		return

	GuildData(str(ctx.guild.id)).reactors.insert(message_id, role_id, emoji)

	await ctx.send(f'Reactor has been set.', delete_after=10)

	msg = await ctx.fetch_message(message_id)
	await msg.add_reaction(emoji)


@bot.command(name="reactorget", aliases=["reactorlist", "Reactorget", "Reactorlist"])
@commands.has_permissions(manage_guild=True)
@commands.cooldown(1, 2, commands.BucketType.user)
@commands.guild_only()
async def reactor_get(ctx):
	"""Get the available reactors."""
	await ctx.message.delete()

	reactors = GuildData(str(ctx.guild.id)).reactors.fetch_all()

	if reactors:
		message = "\nReactors\n------------\nMessage ID - Role ID - Emoji\n\n"

		for r in reactors:
			message += f"{r[1]} - {r[2]} - {r[3]}\n"
		message += f"\nTotal Amount: {len(reactors)}\n"

		msg_parts = [(message[i:i + 1500]) for i in range(0, len(message), 1500)]

		for part in msg_parts:
			await ctx.send(f"```{part}```")
	else:
		await ctx.send(f'No reactors currently set!', delete_after=10)


@bot.command(name="reactordelete", aliases=["reactorclear", "Reactordelete", "Reactorclear"])
@commands.has_permissions(manage_guild=True)
@commands.cooldown(1, 2, commands.BucketType.user)
@commands.guild_only()
async def reactor_delete(ctx, message_id: int):
	"""Delete all reactors on a specific message."""
	await ctx.message.delete()

	data_reactors = GuildData(str(ctx.guild.id)).reactors
	reactors = data_reactors.fetch_all()

	if reactors is None or len(reactors) == 0:
		await ctx.send("No reactors currently set!", delete_after=10)
		return

	result = data_reactors.delete(message_id)
	if result:
		await ctx.send("Reactors removed from message.", delete_after=10)
	else:
		await ctx.send("Reactor not found.", delete_after=10)


@bot.command(name="reactorclearall", aliases=["reactordeleteall", "Reactorclearall", "Reactordeleteall"])
@commands.has_permissions(manage_guild=True)
@commands.cooldown(1, 2, commands.BucketType.user)
@commands.guild_only()
async def reactor_clear_all(ctx):
	"""Clear all reactors."""
	await ctx.message.delete()

	GuildData(str(ctx.guild.id)).reactors.delete_all()

	await ctx.send("All reactors deleted.")


@bot.event
async def on_raw_reaction_add(payload):
	await reaction_handle(payload, add_mode=True)


@bot.event
async def on_raw_reaction_remove(payload):
	await reaction_handle(payload, add_mode=False)


async def reaction_handle(payload, add_mode: bool):
	guild = bot.get_guild(payload.guild_id)
	user = payload.member if payload.member else await guild.fetch_member(payload.user_id)

	if user == bot.user:
		return

	reactors = GuildData(str(guild.id)).reactors.fetch_all()
	reactors_filtered = filter(lambda r: payload.message_id == r[1], reactors)
	list_reactors = list(reactors_filtered)

	if len(list_reactors) > 0:
		for reac in list_reactors:
			re_msg_id = reac[1]
			re_role_id = reac[2]
			re_emoji = reac[3]

			reaction_emoji = str(payload.emoji)
			if reaction_emoji == re_emoji:
				role = guild.get_role(re_role_id)
				if add_mode:
					await user.add_roles(role, reason=f"Reacted: {re_msg_id}")
					await user.send(f"**Role Added**\nYou have joined the *{role.name}* Team.")
				else:
					await user.remove_roles(role, reason=f"Un-Reacted: {re_msg_id}")
					await user.send(f"**Role Removed**\nYou have left the *{role.name}* Team.")


@bot.event
async def on_raw_message_delete(payload):
	guild = bot.get_guild(payload.guild_id)

	reactors = GuildData(str(guild.id)).reactors
	if len(reactors.fetch_all()) <= 0:
		return

	reactors.delete(payload.message_id)


if do_run:
	bot.run(bot_token)
else:
	print("Startup aborted.")