#!usr/bin/env python
# -*- coding: utf-8 -*-
# Create Time: 11/09 2021
# Author: Yunquan (Clooney) Gu
import asyncio
from datetime import datetime

from loguru import logger

from app.Twitter import Twitter
from app.database import FireBase
from app.schedule import Schedule
from app.config import CERTIFICATE_FILE, FIREBASE_DATABASE_URL, init_logging


@logger.catch
async def startup():
    init_logging()

    # init the tool we need
    fb = FireBase(certificate_file=CERTIFICATE_FILE,
                  firebase_url=FIREBASE_DATABASE_URL)
    tw = Twitter(db=fb, count=100)

    # Set the coroutines
    # Parsing job runs every 5 min.
    Schedule.add_job(func=tw.acquire_hot_coins_list,
                     trigger="interval",
                     seconds=60 * 5,
                     next_run_time=datetime.now())

    # Price updating job runs every 5 seconds.
    Schedule.add_job(func=tw.update_all_coins_detail,
                     trigger="interval",
                     seconds=5,
                     next_run_time=datetime.now())


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(startup())
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
