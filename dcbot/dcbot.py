from typing import Awaitable, Callable, Union, Optional
from .gdpy_extensions import ProxyClient, COMMON_PROXY_ERRORS
from gd import (
    Client,
    LevelComment,
    User,
    CommentBanned,
    Level,
    Role,
    MissingAccess,
    IconType,
)
from string import ascii_letters, digits
import random
from getpass import getpass

# -- Our Module --
from .callbacks import Bot, Context
import asyncio

GDEvent = Callable[[Bot], Awaitable[None]]


def obfuscate_text(text: str, left: int = 0, right=4):
    obfuscate = lambda size: "".join(random.choices(ascii_letters + digits, k=size))
    out = text
    if right:
        out = text + " " + obfuscate(right)
    if left:
        out = obfuscate(left) + " " + out
    return out


class UnsafeAbort(Exception):
    """Thrown to abort the program in an unsafe-manner hence the name"""


class DCBot(Bot[User]):
    """Dailychat Bot Class Object, Used to write Dailychat bots with minimal effor"""

    not_it = ["ctx", "comment"]

    def __init__(
        self, prefixes: Union[list[str], str] = "/", vpn: bool = False
    ) -> None:
        super().__init__(prefixes)
        self.vpn = vpn
        self.banned = False
        # should not be used unless the bot is already running...
        # self.client = Client()
        self._username = ""
        self._password = ""
        self.no_abort = True
        """Do not abort the from the main loop"""
        self.banned_users: set[int] = set()
        """banned users cannot execute commands..."""

    def prepare_to_abort(self):
        """aborts the bot gracefully after reading the comment's pages
        This should only be used as a last resort measure to save the
        program..."""
        self.no_abort = True

    async def abort(self):
        """Forces the program to shut-down"""
        raise UnsafeAbort("Daily Chat Bot was forced to shutdown")

    @property
    def name(self):
        """Bot's username"""
        return self._username

    def ban_user(self, user: Union[LevelComment, User, int]):
        """Bans a user from using the bot this should be done by the account_id attribute"""
        if isinstance(user, int):
            self.banned_users.add(user)
        elif isinstance(user, User):
            self.banned_users.add(user.account_id)
        else:
            self.banned_users.add(user.author.account_id)

    def unban_user(self, user: Union[LevelComment, User, int]):
        """Unbans a user, the user banned will be allowed to use the bot again"""
        if isinstance(user, int):
            self.banned_users.remove(user)
        elif isinstance(user, User):
            self.banned_users.remove(user.account_id)
        else:
            self.banned_users.remove(user.author.account_id)

    def event(self, func: Callable[[Context], Awaitable[None]], name: str = None):
        return super().event(func, "on_" + name + "_event")

    async def run(self, username: str = "", password: str = "", proxy_url=None):
        """runs the geometry dash bot, prompts user input if nothing is avalible"""
        self._username = username or input("Bot Username: ")
        self._password = password or getpass("Bot Password: ")
        if proxy_url:
            self.client = ProxyClient(proxy_url=proxy_url)
        else:
            self.client = Client()
        if not proxy_url or self.vpn:
            print(
                "[!] WARNING GOING IN WITHOUT A VPN OR A PROXY IS DANGEROUS, BOT AT YOUR OWN RISK"
            )
        await self.main()

    async def send(self, to: LevelComment, text: str):
        # This loop is used whenever proxy failure occurs so we can rotate on the event on_dead_proxy
        # If we fail after 10 times it's best to quit execution of the command then cause the bot to breakdown...
        for _ in range(10):
            if not self.banned:
                try:
                    return await self.client.post_level_comment(
                        to.level, f"@{to.author.name} " + text
                    )
                except CommentBanned as ban:
                    # Set the flag that we are comment banned...
                    self.banned = True
                    # Invoke the one-time only event...
                    await self.on_comment_banned_event(ban)
                except COMMON_PROXY_ERRORS:
                    # Rotate Our Dead proxy and quickly try a new one this will not run
                    # if we are using a vpn instead...
                    await self.on_dead_proxy_event()
                    continue  # Now Try sending another message

            # Backup method if we're banned...
            try:
                return await to.author.send(
                    obfuscate_text("No Reply Response To Command", left=4, right=4),
                    text,
                )
            except COMMON_PROXY_ERRORS:
                await self.on_dead_proxy_event()
                continue
            except MissingAccess:
                # We are likely blocked at this point no use in continueing
                break
        # TODO: Raise an error or notice of failure or another event of some sort after the loop fails to send anything to the user...

    def on_abort(self, func: Callable[[Context], Awaitable[None]]):
        """This Even is called when the bot is shutting down this wrapper can be used to assist with the shutdown..."""
        return self.event(func, "abort")

    async def on_abort_event(self):
        pass

    async def on_authority_event(self, comment: LevelComment):
        pass

    def on_authority(self, func: Callable[[Context], Awaitable[None]]):
        """The Event can be ran when a Comment belongs to an eldermod
        ::

            @bot.on_authority
            async def warn_user(ctx:DCBot, authority:LevelComment):
                print("{authority.author.name} is in dailychat")
        """
        return self.event(func, "authority")

    async def on_dead_proxy_event(self):
        pass

    def on_dead_proxy(self, func: GDEvent):
        """if your not using a vpn this function is invoked when the proxy is not working
        ::

            import random

            @bot.on_dead_proxy
            async def rotate_proxy(ctx:DCBot):
                with open("proxies.txt","r") as r:
                    ctx.client.rotate_proxy(random.choice(r.readlines()))
        """
        return self.event(func, "dead_proxy")

    async def on_comment_banned_event(self, ban: CommentBanned):
        """Your bot was banned"""
        pass

    def on_comment_banned(self, func: GDEvent):
        """Invoked when your comment bot has been banned, This program will resort to dms if this occurs
        along with this event...

        ::

            from discord_webhook import AsyncDiscordWebhook
            import json

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
                await webhook.execute()

        """
        return self.event(func, "comment_banned")

    def command(
        self,
        func: Callable[[Context, LevelComment], Awaitable[None]],
        name: Optional[str] = None,
    ):
        """A Command that your bot can run
        ::

            @bot.command("ping")
            async def ping_pong(ctx:DCBot, comment:LevelComment):
                await ctx.send(comment, f"Pong!")

        """
        return super().command(func, name)

    def help_command(self, func):
        return self.command(func, "help")

    async def main(self):
        """Do the main part and setup for chat listening..."""
        await self.client.session.http.ensure_session()
        assert not self.client.session.http._session.closed
        await self.client.try_login(self._username, self._password)
        assert self.client.is_logged_in()
        self.no_abort = True

        async def on_daily_comment(daily: Level, comment: LevelComment):
            # view all comments as a part of debugging...
            print(comment.author.name + ":" + comment.content)
            if comment.author.role == Role.ELDER_MODERATOR:
                # dispatch on the authority event...
                await self.on_authority_event(comment)
            try:
                start, end = comment.content.split(" ", 1)
            except:
                start = comment.content
                end = ""
            cmd = self.commands.get(start)
            # Continue if we have nothing...
            if not cmd:
                return
            # otherwise do this...
            try:
                # print("[+] Command in action! CONGRATS!")
                return await cmd.invoke(comment, end)
            except Exception as e:
                print(e)
    

        daily = await self.client.get_daily()
        # data = await self.client.post_level_comment(
        #     daily, "Hello There Everyone I am :D I am now online"
        # )
        cache: list[int] = []
        while self.no_abort:
            try:
                async for comment in daily.get_comments_on_page():
                    if comment.id not in cache:
                        cache.append(comment.id)
                        await on_daily_comment(daily, comment)

            except UnsafeAbort:
                # force program's exit...
                break
            except COMMON_PROXY_ERRORS:
                await self.on_dead_proxy_event()

            except KeyboardInterrupt:
                # abort because the user asked to exit via keyboard
                print("[+] Program is aborting thanks to keyboard interrupt")
                break
            await asyncio.sleep(10)
            if len(cache) >= 200:
                cache = cache[100:]
        # Run our on_abort event so we can shutdown any loosley running programs ...
        await self.on_abort_event()
        # now we may exit
        return
    


class DCDummy(DCBot):
    """Made to simulate commands before production is ready... This can also debug commands off..."""

    async def send(self, to: str, text: str):
        return print(f"@{to} {text}")

    async def test(self, text: str, comment: str = "author"):
        return await self.read_comment(comment, text)


def bot(prefixes: Union[list[str], str] = "/", vpn: bool = False, dummy: bool = False):
    """
    dummy: `bool` : returns `DummyBot` where the bot is not yet production ready (Only Commands can be rigged together)
    """
    return DCDummy(prefixes=prefixes) if dummy else DCBot(prefixes, vpn=vpn)
