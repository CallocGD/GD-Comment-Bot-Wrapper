# GD Comment Bot Wrapper
My Super Secret Framework for build Geometry dash comment bots with commands inplace.
At this point robtop has pretty much smothered the majority of my free proxies so I'm dumping 
the source code here to anyone who wishes to continue my legacy that I've pretty much left behind.

It includes a very friendly coding atmosphere not seen ever in GD Bot programming ever before

## Some Cleaver Examples include the following
```py
from discord_webhook import AsyncDiscordWebhook
import json, random

from dcbot import DCBot
WEBHOOK_LINK = "<your discord webhook>"

bot = DCBot("/")

@bot.on_comment_banned()
def on_comment_banned(ctx:DCBot, ban:CommentBanned):
    # Uh Oh...
    webhook = AsyncDiscordWebhook(
        url=WEBHOOK_LINK,
        content=f"@everyone The king is dead ;-; : [Banned] : ```json\n{json.loads(ban.__dict__)}```"
    )
    # Send our message back to discord
    await webhook.execute()

# The most basic command in the book....
@bot.command
async def diceroll(ctx:DCBot, comment:LevelComment)
    return await ctx.send(comment, "your rolled a {random.randint(1,6)}")
```

Even when the bot becomes commentbanned it has a smart backup-system inplace that will immediately send a 
dm to the user instead so that the bot remains alive for as long as possible without failure. Special event callbacks like in discordpy as demonstrated above are also inplace to help with this.