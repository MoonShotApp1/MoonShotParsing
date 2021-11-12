#!usr/bin/env python
# -*- coding: utf-8 -*-
# Create Time: 11/09 2021
# Author: Yunquan (Clooney) Gu
import asyncio
from datetime import datetime

from loguru import logger

from app.Twitter_v2 import Twitter
from app.config import init_logging
from app.database import FireBase
from app.schedule import Schedule


@logger.catch
async def startup():
    init_logging()
    fb = FireBase()
    tw = Twitter(start_time=datetime.now(), db=fb)

    # The parsing job run every 10 min.
    Schedule.add_job(func=tw.acquire_hot_coins_list,
                     trigger="interval",
                     seconds=60 * 10,
                     next_run_time=datetime.now())

    Schedule.add_job(func=tw.update_all_coins_detail,
                     trigger="interval",
                     seconds=1,
                     next_run_time=datetime.now())


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(startup())
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
