import os
import discord
import asyncio
import uuid
import sqlite3
from dotenv import load_dotenv
from discord.ext import tasks, commands

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = commands.Bot(command_prefix="!", help_command=None)

@bot.event
async def on_ready():
  print(f'Logged in as {bot.user.name}, id:{bot.user.id}')
  await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"people win bets!"))

class Prediction():
  def __init__(self, bet_text, option_one, option_two, owner, id):
    self.bet_text = bet_text
    self.option_one = option_one
    self.option_two = option_two
    self.owner = owner
    self.id = id
    self.option_one_bettors = []
    self.option_two_bettors = []
  
  def get_current_options(self):
    return self.option_one.lower(), self.option_two.lower()

class PredictionsBot(commands.Cog):
  def __init__(self):
    self.bot = bot
    self.current_prediction = None
    self.color = 0xBB36C9
  
  @commands.command(command="help")
  async def help(self, ctx):
    embed = discord.Embed(title="Welcome to Predictions Bot!", description="""
    Make a prediction by using the following command:\n
    !makeprediction <\'prompt to bet on\'> <\'option one\'> <\'option two\'>\n
    Like this: !makeprediction \'I will win the next game\' \'True\' \'False\'\n
    Make sure to use quotes around each sentence!\n
    People can bet by typing using !bet <option> <amount>\n
    Use this: !bet \'True\' 100 to bet 100 points on True winning!\n
    The person who made the prediction can end the prediciton by using !endprediction <\'option that won\'>\n
    Like this: !endprediction \'True\'\n
    Check how many points you have with !balance. Have fun!
    """, color=self.color)
    await ctx.send(embed=embed)

  @commands.has_permissions(manage_messages=True)
  @commands.command(command="makeprediction", aliases=["startprediction"])
  async def makeprediction(self, ctx, bet_text, option_one, option_two):
    if self.current_prediction is not None:
      await ctx.message.add_reaction("❌")
      await ctx.author.send(f"There's already a prediction going! Ask {self.current_prediction.owner} to end it with !endprediction <option>")
      return
    if option_one.lower() == option_two.lower():
      await ctx.message.add_reaction("❌")
      await ctx.author.send("Can't start a bet with the same two options!")
      return
    embed = discord.Embed(title="A new prediction!", color=self.color)
    embed.add_field(name=bet_text, value=f"**__{option_one}__** *or* **__{option_two}__**\nPlace your bets with !bet <option> <amount>")
    await ctx.send(embed=embed)
    prediction_owner = ctx.author
    prediction_id = uuid.uuid4()
    self.current_prediction = Prediction(bet_text, option_one, option_two, prediction_owner, prediction_id)
  
  @commands.command(command="bet", aliases=["predict"])
  async def bet(self, ctx, option, amount_bet):
    if self.current_prediction is not None:
      db = sqlite3.connect("main.sqlite")
      cursor = db.cursor()
      cursor.execute(f"SELECT * FROM main WHERE user_id = {ctx.author.id}")
      result = cursor.fetchone()
      if result is None: #if user doesn't exist, get them started and keep going
        await self.start(ctx)
        cursor.execute(f"SELECT * FROM main WHERE user_id = {ctx.author.id}")
        result = cursor.fetchone()

      user_id, points = result

      try:
        amount_bet = int(amount_bet)
      except ValueError:
        await ctx.message.add_reaction("❌")
        await ctx.author.send("You can't bet something that's not a number, sorry.")
        return
      if points < amount_bet:
        await ctx.message.add_reaction("❌")
        await ctx.author.send(f"You can't afford that! You have {points} points and tried to bet {amount_bet}.")
        return
      
      current_op_one, current_op_two = self.current_prediction.get_current_options()
      option = option.lower()

      if option not in [current_op_one, current_op_two]: #if the option is invalid
        await ctx.message.add_reaction("❌")
        await ctx.author.send(f"{option} is not one of the options to bet on.")
        return
      cursor.execute(f"UPDATE main SET points = {points - amount_bet} WHERE user_id = {user_id}")
      if option == current_op_one:
        self.current_prediction.option_one_bettors.append((ctx.author, amount_bet))
      elif option == current_op_two:
        self.current_prediction.option_two_bettors.append((ctx.author, amount_bet))
      db.commit()
      db.close()
      await ctx.message.add_reaction("✅")

  @commands.command(command="debug")
  async def debug(self, ctx):
    if ctx.author.id == 164822993489362953: #this is my id, only I can use the debug function
      await self.makeprediction(ctx, "max will lose this level", "yes", "no")

  @commands.command(command="endprediction")
  async def endprediction(self, ctx, winning_op):
    if self.current_prediction != None and ctx.author == self.current_prediction.owner:
      current_op_one, current_op_two = self.current_prediction.get_current_options()
      winning_op = winning_op.lower()
      if winning_op not in [current_op_one, current_op_two]:
        await ctx.message.add_reaction("❌")
        await ctx.author.send(f"{winning_op} is not one of the options.")
        return
      embed = discord.Embed(title="The Prediction is Over!", description=f"Everyone who bet for {winning_op} wins!", color=self.color)
      await ctx.send(embed=embed)
      db = sqlite3.connect("main.sqlite")
      cursor = db.cursor()
      option_one_sum = sum([i[1] for i in self.current_prediction.option_one_bettors])
      option_two_sum = sum([i[1] for i in self.current_prediction.option_two_bettors])
      if winning_op == current_op_one:
        for user, amount in self.current_prediction.option_one_bettors:
          cursor.execute(f"SELECT points FROM main WHERE user_id = {user.id}")
          current_points = cursor.fetchone()[0]
          ratio = option_two_sum / option_one_sum # if $100 is on one and $200 is on two, then if one wins you get two dollars for every $1 you bet. 200/100 = 2, amount*ratio = amount won
          cursor.execute(f"UPDATE main SET points = {current_points + amount + (round(amount * ratio, 2))} WHERE user_id = {user.id}")
      elif winning_op == current_op_two:
        for user, amount in self.current_prediction.option_two_bettors:
          cursor.execute(f"SELECT points FROM main WHERE user_id = {user.id}")
          current_points = cursor.fetchone()[0]
          ratio = option_one_sum / option_two_sum # if $100 is on one and $200 is on two, then if two wins you get 0.5 dollars for every $1 you bet. 100/200 = 0.5, amount*ratio = amount won
          cursor.execute(f"UPDATE main SET points = {current_points + amount + (round(amount * ratio, 2))} WHERE user_id = {user.id}")
      db.commit()
      db.close()
      self.current_prediction = None

  @commands.command(command="balance", aliases=["bal", "money", "amount"])
  async def balance(self, ctx):
    db = sqlite3.connect("main.sqlite")
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM main WHERE user_id = {ctx.author.id}")
    result = cursor.fetchone()
    user_id, points = result
    if result is None:
      await self.start(ctx)
      return
    embed = discord.Embed(title=f"{ctx.author} has {points} points!", color=self.color)
    await ctx.send(embed=embed)
    db.close()

  @commands.command(command="start")
  async def start(self, ctx):
    db = sqlite3.connect("main.sqlite")
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM main WHERE user_id = {ctx.author.id}")
    result = cursor.fetchone()
    if result is None:
      cursor.execute(f"INSERT INTO main (user_id, points) VALUES ({ctx.author.id}, 100)")
      db.commit()
      db.close()
      embed = discord.Embed(title=f"{ctx.author} just started betting! Have 100 points.", color=self.color)
      await ctx.send(embed=embed)
    elif result is not None:
      await ctx.message.add_reaction("❌")
      await ctx.author.send(f"You can't start twice!")
    
  @commands.command(command="broke")
  async def broke(self, ctx):
    db = sqlite3.connect("main.sqlite")
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM main WHERE user_id = {ctx.author.id}")
    result = cursor.fetchone()
    if result is None:
      await self.start(ctx)
      return
    user_id, points = result
    if points == 0:
      cursor.execute(f"UPDATE main SET points = 25 WHERE user_id = {user_id}")
      embed = discord.Embed(title=f"Aww, {ctx.author} ran out of money! Have some pocket change.", color=self.color)
      await ctx.message.add_reaction("🪙") #coin emoji
      await ctx.send(embed=embed)
    else:
      embed = discord.Embed(title=f"You aren't broke! You've still got {points} points! Come back when you're REAL poor.", color=self.color)
      await ctx.send(embed=embed)
    db.commit()
    db.close()

bot.add_cog(PredictionsBot())
bot.run(BOT_TOKEN)