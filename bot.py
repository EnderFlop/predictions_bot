import os
import discord
import asyncio
import uuid
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
    self.users = {}
  
  @commands.command(command="help")
  async def help(self, ctx):
    await ctx.send("Welcome to Predictions Bot!")
    await ctx.send("Make a prediction by using the following command:")
    await ctx.send("!makeprediction \'prompt to bet on\' \'option one\' \'option two\'")
    await ctx.send("Like this: !makeprediction \'I will win the next game\' \'True\' \'False\'")
    await ctx.send("Make sure to use quotes around each sentence!")
    await ctx.send("People can bet by typing using !bet")
    await ctx.send("Use (!bet \'option one\', 100) to bet 100 points on option one winning!")
    #help on how to end the prediction once it's coded lol

  @commands.command(command="makeprediction", aliases=["startprediction"])
  async def makeprediction(self, ctx, bet_text, option_one, option_two):
    if option_one.lower() == option_two.lower():
      await ctx.send("Can't start bet with the same two options!")
      return
    await ctx.send("A PREDICTION HAS BEEN INVOKED!")
    await ctx.send(f"\"{bet_text}\"")
    await ctx.send(f"{option_one} OR {option_two}")
    await ctx.send(f"TYPE \'!bet (option name) (amount)\' TO BET!")
    prediction_owner = ctx.author
    prediction_id = uuid.uuid4()
    self.current_prediction = Prediction(bet_text, option_one, option_two, prediction_owner, prediction_id)
  
  @commands.command(command="bet", aliases=["predict"])
  async def bet(self, ctx, option, amount):
    if self.current_prediction != None:
      if ctx.author not in self.users: #if user doesn't exist, get them started and keep going
        await self.start(ctx)
      try:
        amount = int(amount)
      except ValueError:
        await ctx.send("You can't bet that! (NaN)")
      if self.users[ctx.author] < amount:
        await ctx.send("you can't afford that!")
        return
      
      current_op_one, current_op_two = self.current_prediction.get_current_options()
      option = option.lower()

      if option not in [current_op_one, current_op_two]: #if the option is invalid
        await ctx.send(f"{option} is not one of the options.")
        return
      self.users[ctx.author] -= amount
      if option == current_op_one:
        self.current_prediction.option_one_bettors.append((ctx.author, amount))
      elif option == current_op_two:
        self.current_prediction.option_two_bettors.append((ctx.author, amount))
      await ctx.send(f"{ctx.author} just bet {amount} on {option}!")

  @commands.command(command="debug")
  async def debug(self, ctx):
    self.current_prediction = Prediction("true or false", "true", "false", ctx.author, uuid.uuid4())

  @commands.command(command="endprediction")
  async def endprediction(self, ctx, winning_op):
    if self.current_prediction != None and ctx.author == self.current_prediction.owner:
      current_op_one, current_op_two = self.current_prediction.get_current_options()
      winning_op = winning_op.lower()
      if winning_op not in [current_op_one, current_op_two]:
        await ctx.send(f"{winning_op} is not one of the options.")
        return
      await ctx.send("THE PREDICTION IS OVER!")
      await ctx.send(f"EVERYONE WHO BET FOR {winning_op} WINS!")
      if winning_op == current_op_one:
        for user, amount in self.current_prediction.option_one_bettors:
          self.users[user] += amount * 2
      elif winning_op == current_op_two:
        for user, amount in self.current_prediction.option_two_bettors:
          self.users[user] += amount * 2
      self.current_prediction = None

  @commands.command(command="balance", aliases=["bal", "money", "amount"])
  async def balance(self, ctx):
    if ctx.author not in self.users: #if user doesn't exist, get them started and keep going
      await self.start(ctx)
      return
    await ctx.send(f"{ctx.author} has {self.users[ctx.author]} points!")

  @commands.command(command="start")
  async def start(self, ctx):
    self.users[ctx.author] = 100
    await ctx.send(f"{ctx.author} just started betting! Have 100 points.")
  

    


bot.add_cog(PredictionsBot())
bot.run(BOT_TOKEN)