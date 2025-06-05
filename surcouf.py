#!/usr/bin/env python3

import aiohttp
import asyncio
import datetime
import json
import os
import pathlib
import re
import rich
import rich.traceback
import signal
import subprocess
import sys
import time

rich.traceback.install(show_locals=True)

root = os.path.realpath(__file__)
root = os.path.dirname(root)
sys.path.append(root + '/blinkpy')

from blinkpy.blinkpy import Blink
from blinkpy.auth import Auth as BlinkAuth
import blinkpy.helpers.util as BlinkUtil


# -----------------------------------------------
class House:
    # ----
    def __init__(self, name):
        self.armed = None
        self.blink = None
        self.session = None
        self.name = name

    # ----
    def control_center(self):
        return self.blink.sync[self.name]

    # ----
    async def open(self):
        if not self.blink:
            self.session = aiohttp.ClientSession()
            self.blink = Blink(session=self.session)

            auth = BlinkAuth(await BlinkUtil.json_load('/home/yannick/.ssh/blink.json'), session=self.session)
            self.blink.auth = auth

            await self.blink.start()
            await self.blink.save('/home/yannick/.ssh/blink.json')

    # ----
    async def close(self):
        await self.session.close()

    # ----
    async def empty(self):
        if self.armed is None or not self.armed:
            rich.print('[red]empty[/]')
            self.armed = True
            await self.control_center().async_arm(self.armed)

    # ----
    async def occupied(self):
        if self.armed is None or self.armed:
            rich.print('[green]occupied[/]')
            self.armed = False
            await self.control_center().async_arm(self.armed)
            # await self.clean()

    # ----
    async def clean(self):
        await self.control_center().refresh()
        if self.control_center().local_storage and self.control_center().local_storage_manifest_ready:
            manifest = self.control_center()._local_storage['manifest']
            rich.print(manifest)
            for item in reversed(manifest):
                now = datetime.datetime.now(datetime.timezone.utc)
                rich.print(now - item.created_at)
                if now - item.created_at < datetime.timedelta(minures=1):
                    try:
                        rich.print(item)
                        # await item.delete_video(self.blink)
                    except Exception as e:
                        rich.print(e)

    # ----
    async def status(self):
        await self.control_center().refresh()
        print(f'{self.control_center().name} status: {self.control_center().arm}')
        print()


# -----------------------------------------------
class Network:
    # ----
    def __init__(self, smartphones):
        self.pattern = re.compile(r'^.*bytes from (?P<MAC>(.*)) \((?P<IP>(.*))\):.*')
        self.smartphones = smartphones

    # ----
    def probe(self):
        self.empty = True
        for member, smartphone in self.smartphones.items():
            cmd = ['/usr/sbin/arping', '-v', '-c', '1', smartphone['ip']]
            for _ in range(0, smartphone['arping_attemps']):
                result = subprocess.run(cmd, capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    match = self.pattern.match(line)
                    if match:
                        self.empty = False
                        return
                time.sleep(smartphone['arping_delay'])


# -------------------------------------------------
def signal_handler(sig, frame):
    exit()


# -----------------------------------------------
async def main():
    config_file = pathlib.Path(__file__).parent / 'config.json'
    with config_file.open(encoding='utf-8') as f:
        config = json.load(f)

        house = House(config['hub'])
        network = Network(config['smartphones'])

        await house.open()
        try:
            while True:
                network.probe()

                if network.empty:
                    await house.empty()
                    time.sleep(5)
                else:
                    await house.occupied()
                    time.sleep(60)
        finally:
            await house.close()


signal.signal(signal.SIGINT, signal_handler)
asyncio.run(main())
