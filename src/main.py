import asyncio

from website.www_jpq_me.spider import Parser

parser = Parser()

asyncio.run(parser.start_parse())
