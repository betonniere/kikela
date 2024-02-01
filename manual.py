#! /usr/bin/env python3

import asyncio
import os
import rich
from datetime import datetime, timedelta
from blinkpy.helpers.util import json_load
from blinkpy.blinkpy import Blink, BlinkSyncModule
from blinkpy.auth import Auth
from aiohttp import ClientSession


async def start(session: ClientSession):
    blink = Blink(session=session)
    blink.auth = Auth(await json_load(os.getenv('HOME') + '/.ssh/blink.json'), session=session)
    await blink.start()
    return blink


async def main():
    session = ClientSession()
    try:
        blink = await start(session)
        await blink.refresh()
        my_sync: BlinkSyncModule = blink.sync['surcouf']
        await my_sync.refresh()
        if my_sync.local_storage and my_sync.local_storage_manifest_ready:
            manifest = my_sync._local_storage['manifest']
            # print(f'Manifest {manifest}')
            for item in reversed(manifest):
                rich.print(item)
                current_date = datetime.now(item.created_at.tzinfo)
                time_difference = current_date - item.created_at

                if time_difference > timedelta(days=14):
                    try:
                        pass
                        # await item.delete_video(blink)
                        # await asyncio.sleep(2)
                    except Exception as e:
                        print(f'Error deleting video {item.id}: {e}')
        else:
            print('Manifest not ready')
    finally:
        await session.close()

asyncio.run(main())
