from PIL import Image, ImageColor, ImageDraw

# Creates a clashing "progress bar" which displays the total bets on each side fighting for space.
def create_progress_bar(amount_one, amount_two):
  WIDTH = 1000
  HEIGHT = 200
  percentage_one = amount_one / (amount_one + amount_two) #amount of the bar option one takes up
  percentage_two = amount_two / (amount_one + amount_two) #amount of the bar option two takes up

  meter_one = Image.new("RGBA", (WIDTH,HEIGHT), color=None)
  ImageDraw.Draw(meter_one).rectangle([10, 10, WIDTH * percentage_one, HEIGHT - 10], fill=ImageColor.getrgb("#5865F2"))

  meter_two = Image.new("RGBA", (WIDTH,HEIGHT), color=None)
  ImageDraw.Draw(meter_two).rectangle([WIDTH - (WIDTH * percentage_two), 10, WIDTH, HEIGHT - 10], fill=ImageColor.getrgb("#ED4245"))

  meters_together = Image.new("RGBA", (WIDTH,HEIGHT), color=None)
  meters_together.alpha_composite(meter_one)
  meters_together.alpha_composite(meter_two)

  meter_border = Image.open("./mask.png")
  border_base = Image.new("RGBA", (WIDTH, HEIGHT), color=None)
  border_base.paste(meter_border)
  meters_together.alpha_composite(border_base)
  
  return meters_together