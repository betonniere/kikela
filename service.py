#!/usr/bin/env python3

# Copyright (C) Yannick Le Roux.
# This file is part of Kikela.
#
#   Kikela is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   Kikela is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Kikela.  If not, see <http://www.gnu.org/licenses/>.

import aiohttp
import aiohttp.web
import asyncio
import datetime
import json
import logging
import os
import pathlib
import re
import rich.traceback
import signal
import sys

from config import Config
from firmware import Firmware

rich.traceback.install(show_locals=True)

root = os.path.realpath(__file__)
root = os.path.dirname(root)
sys.path.append(root + '/blinkpy')

import blinkpy.auth
import blinkpy.blinkpy

logging.basicConfig(level=logging.WARNING)


# -----------------------------------------------
async def execute(cmd):
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        stdout, _ = await process.communicate()
        return stdout, process.returncode
    except asyncio.CancelledError:
        process.kill()
        await process.wait()
        raise


# -----------------------------------------------
class Page:
    # ----
    def __init__(self, name):
        self.name = name
        self.data = None

    # ----
    def set_frontend(self, frontend):
        self.frontend = frontend

    # ----
    def set_data(self, data):
        self.data = data

    # ----
    async def display(self, client=None):
        await self.frontend.display_page(self, client)

    # ----
    async def hide(self):
        await self.frontend.hide_page(self)


# -----------------------------------------------
class WifiPage(Page):
    # ----
    def __init__(self, name):
        super().__init__(name)


# -----------------------------------------------
class CredentialsPage(Page):
    # ----
    def __init__(self, name):
        super().__init__(name)


# -----------------------------------------------
class AuthenticationPage(Page):
    # ----
    def __init__(self, name):
        super().__init__(name)


# -----------------------------------------------
class ConfigurationPage(Page):
    # ----
    def __init__(self, name):
        super().__init__(name)
        self.status = {'hubs': {}, 'smartphones': {}}

    # ----
    async def display(self, client=None):
        with Config() as config:
            self.data = {'config': config.settings, 'status': self.status}

        await super().display(client)

    # ----
    async def report_status(self, status):
        self.status = status
        await self.frontend.report_status(status)


# -----------------------------------------------
class Frontend:
    # ----
    def __init__(self, host='0.0.0.0', port=8099):
        self.runner = None

        self.host = host
        self.port = port

        self.pages = {}
        self.stack = []

        self.clients = []
        self.waiters = []

        self.web_application = aiohttp.web.Application()
        self.web_application.router.add_get('/', self.index)
        self.web_application.router.add_get('/ws', self.handle_ws)
        self.web_application.router.add_static('/static/', path='web')

    # ----
    def add_page(self, page):
        page.set_frontend(self)
        self.pages[page.name] = page

    # ----
    def get_page(self, name):
        return self.pages.get(name, None)

    # ----
    async def start(self):
        self.runner = aiohttp.web.AppRunner(self.web_application)
        await self.runner.setup()

        site = aiohttp.web.TCPSite(self.runner, self.host, self.port)
        try:
            await site.start()
        except OSError as e:
            print(f'🔴 Démarrage du serveur web : [red]{e}[/]')
            sys.exit(1)

        print(f'🟢 Webapp en écoute sur http://{self.host}:{self.port}')

    # ----
    async def stop(self):
        for client in self.clients:
            await client.close()

        if self.runner:
            await self.runner.cleanup()

    # ----
    async def broadcast(self, message):
        lost_clients = []

        for client in self.clients:
            try:
                await client.send_json(message)
            except ConnectionResetError:
                lost_clients.append(client)

        for client in lost_clients:
            self.clients.remove(client)

    # ----
    async def display_page(self, page, client):
        for current_page in self.stack:
            if current_page == page:
                self.stack.remove(current_page)
                break

        self.stack.append(page)

        clients = [client] if client is not None else self.clients
        lost_clients = []
        for client in clients:
            try:
                await client.send_json({'type': 'display_page', 'name': page.name, 'data': page.data})
            except ConnectionResetError:
                lost_clients.append(client)

        for client in lost_clients:
            if client in self.clients:
                self.clients.remove(client)

    # ----
    async def hide_page(self, page):
        new_front_page = None
        if self.stack and self.stack[-1] == page:
            new_front_page = self.stack[-2] if len(self.stack) > 1 else None

        for current_page in self.stack:
            if current_page == page:
                self.stack.remove(current_page)
                break

        if new_front_page is not None:
            await new_front_page.display()

    # ----
    async def report_status(self, status):
        await self.broadcast({'type': 'status', 'status': status})

    # ----
    async def wait_for_message(self, key):
        future = asyncio.get_running_loop().create_future()
        self.waiters.append((key, future))
        try:
            return await future
        finally:
            self.waiters = [(k, f) for k, f in self.waiters if f is not future]

    # ----
    async def index(self, request):
        return aiohttp.web.FileResponse('web/index.html')

    # ----
    async def handle_ws(self, request):
        ws = aiohttp.web.WebSocketResponse()
        await ws.prepare(request)

        self.clients.append(ws)

        if self.stack:
            front_page = self.stack[-1]
            await front_page.display(client=ws)

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue

                for key, future in list(self.waiters):
                    if future.done():
                        continue
                    if key in data:
                        future.set_result(data)
                        break

            elif msg.type == aiohttp.WSMsgType.ERROR:
                break

        return ws


# -----------------------------------------------
class Wifi:
    # ----
    def __init__(self, frontend, interface, connections):
        self.frontend = frontend
        self.interface = interface
        self.connections = connections

    # ----
    async def check(self):
        info = None
        try:
            wifi_page = self.frontend.get_page('wifi')

            while True:
                cmd = ['nmcli', '-g', 'NAME', 'connection', 'show', '--active']
                stdout, _ = await execute(cmd)
                active_connections = stdout.decode().strip().splitlines()

                if active_connections:
                    if 'Hotspot' in active_connections:
                        wifi_page.set_data({'info': info, 'status': 'KO'})
                        await wifi_page.display()

                        message = await self.frontend.wait_for_message('wifi')

                        info = 'Bascule en cours, veuillez patienter...'
                        wifi_page.set_data({'info': info, 'status': 'SWITCHING'})
                        await wifi_page.display()

                        ssid = message['wifi']['ssid']
                        password = message['wifi']['password']

                        cmd = ['sudo', 'nmcli', 'con', 'modify', 'WifiClient', '802-11-wireless.ssid', ssid, '802-11-wireless-security.psk', password]
                        await execute(cmd)

                        cmd = ['sudo', 'nmcli', 'con', 'up', 'WifiClient']
                        _, returncode = await execute(cmd)
                        if returncode == 0:
                            print("🟢 Succès : La commande s'est exécutée correctement.")
                            return

                        print('🟠 Échec de connexion à WifiClient, retour au mode hotspot.')
                        info = 'Erreur ! Veuillez vérifier le SSID et le mot de passe.'
                        cmd_hotspot = ['sudo', 'nmcli', 'con', 'up', 'Hotspot']
                        await execute(cmd_hotspot)
                        continue

                    else:
                        for connection in self.connections:
                            if connection in active_connections:
                                return

                await asyncio.sleep(2)
                cmd_reconnect = ['sudo', 'nmcli', 'device', 'connect', 'wlan0']
                await execute(cmd_reconnect)

        finally:
            await wifi_page.hide()


# -----------------------------------------------
class BlinkAccount:
    # ----
    def __init__(self, frontend, auth_file=pathlib.Path('/home/yannick/.ssh/kikela.json')):
        self.blink = None
        self.session = None
        self.frontend = frontend
        self.auth_file = auth_file

        if not self.auth_file.exists():
            self.auth_file.parent.mkdir(parents=True, exist_ok=True)
            self.auth_file.write_text('{"username": "email", "password": "mot de passe"}')

    # ----
    async def open(self):
        if self.blink:
            return

        try:
            authentication_page = self.frontend.get_page('authentication')
            credentials_page = self.frontend.get_page('credentials')

            while True:
                if self.session is None:
                    self.session = aiohttp.ClientSession()

                    self.blink = blinkpy.blinkpy.Blink(session=self.session)
                    self.blink.auth = blinkpy.auth.Auth(await blinkpy.helpers.util.json_load(self.auth_file), session=self.session)
                else:
                    await authentication_page.display()

                    message = await self.frontend.wait_for_message('code')

                    authentication_page.set_data({'message': 'Vérification du code ...', 'status': 'OK'})
                    await authentication_page.display()

                    success = await self.blink.send_2fa_code(message['code'])
                    if success:
                        await self.blink.save(self.auth_file)
                        return

                    authentication_page.set_data({'info': 'Code invalide, merci de réessayer.', 'status': 'KO'})
                    continue

                try:
                    if await self.blink.start():
                        return

                    raise blinkpy.auth.LoginError('Erreur de connexion')

                except (blinkpy.auth.LoginError, blinkpy.auth.TokenRefreshFailed):
                    await self.close()

                    await credentials_page.display()

                    message = await self.frontend.wait_for_message('credentials')

                    credentials_page.set_data({'info': 'Vérification des identifiants.', 'status': 'OK'})
                    await credentials_page.display()

                    credentials = {'username': message['credentials']['user'], 'password': message['credentials']['password']}
                    self.auth_file.write_text(json.dumps(credentials))

                    credentials_page.set_data({'info': 'Erreur de connexion, merci de vérifier vos identifiants.', 'status': 'KO'})
                    continue

                except blinkpy.auth.BlinkTwoFARequiredError:
                    continue

                finally:
                    pass

        except Exception as e:
            print(f'🔴 except Exception générique : {type(e).__name__}: {e}')

        finally:
            await credentials_page.hide()
            await authentication_page.hide()

    # ----
    async def reauth(self):
        await self.close()
        await self.open()

    # ----
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

        self.blink = None
        self.session = None

    # ----
    def active(self):
        return self.blink is not None and self.session is not None and not self.session.closed


# -----------------------------------------------
class Hub:
    # ----
    def __init__(self, name, account):
        self.armed = None
        self.name = name
        self.account = account

        with Config() as config:
            self.debug = config.settings.get('debug', False)

    # ----
    def control_center(self):
        return self.account.blink.sync.get(self.name, None)

    # ----
    async def empty(self):
        control_center = self.control_center()
        if control_center is None:
            return

        if self.armed is None or not self.armed:
            print('📤 ⬜ empty')
            self.armed = True
            if not self.debug:
                await control_center.async_arm(self.armed)

    # ----
    async def occupied(self):
        control_center = self.control_center()
        if control_center is None:
            return

        if self.armed is None or self.armed:
            print('📤 ⬛ occupied')
            self.armed = False
            if not self.debug:
                await control_center.async_arm(self.armed)
            # await self.clean()

    # ----
    async def clean(self):
        await self.control_center().refresh()
        if self.control_center().local_storage and self.control_center().local_storage_manifest_ready:
            manifest = self.control_center()._local_storage['manifest']
            print(manifest)
            for item in reversed(manifest):
                now = datetime.datetime.now(datetime.UTC)
                print(now - item.created_at)
                if now - item.created_at < datetime.timedelta(minutes=1):
                    try:
                        print(item)
                        # await item.delete_video(self.account.blink)
                    except Exception as e:
                        print(e)


# -----------------------------------------------
class Network:
    # ----
    def __init__(self, interface):
        self.pattern = re.compile(r'^.*bytes from (?P<MAC>(.*)) \((?P<IP>(.*))\):.*')
        self.interface = interface
        self.empty = True
        self.presence = {}

    # ----
    async def probe_one(self, ip, arping_attemps, arping_delay, found_event):
        cmd = ['/usr/sbin/arping', '-i', self.interface, '-c', '5', '-C', '1', ip]
        for _ in range(0, arping_attemps):
            if found_event.is_set():
                return False

            stdout, _ = await execute(cmd)

            for line in stdout.decode().splitlines():
                match = self.pattern.match(line)
                if match:
                    found_event.set()
                    return True
            await asyncio.sleep(arping_delay)
        return False

    # ----
    async def probe(self):
        with Config() as config:
            smartphones = config.settings.get('smartphones', {})

        found_event = asyncio.Event()
        names = list(smartphones.keys())
        results = await asyncio.gather(
            *(self.probe_one(smartphone['ip'], smartphone['arping_attemps'], smartphone['arping_delay'], found_event) for smartphone in smartphones.values())
        )
        self.presence = dict(zip(names, results, strict=True))
        self.empty = not any(results)
        return self.empty


# -------------------------------------------------
main_task = None


def signal_handler():
    if main_task is not None:
        main_task.cancel()


# -----------------------------------------------
async def monitoring(firmware, frontend, wifi, network, account):

    probe_period = 5

    configuration_page = frontend.get_page('configuration')
    await configuration_page.display()

    while True:
        try:
            # Vérification / configuration de la connexion Wi-Fi
            await wifi.check()

            firmware.upgrade()

            # Sondage réseau et configuration utilisateur
            probe_task = asyncio.create_task(network.probe())
            config_task = asyncio.create_task(frontend.wait_for_message('configuration'))

            # Attente du probe ou d'une interruption
            done, pending = await asyncio.wait({probe_task, config_task}, return_when=asyncio.FIRST_COMPLETED)

            # Interruption : on interrompt le probe en cours et on relance immédiatement
            if config_task in done:
                probe_task.cancel()
                try:
                    await probe_task
                except asyncio.CancelledError:
                    pass

                settings = config_task.result()['configuration']
                with Config() as config:
                    config.settings = settings
                await configuration_page.display()

                continue

            # Résultat du probe
            if probe_task in done:
                config_task.cancel()
                try:
                    await config_task
                except asyncio.CancelledError:
                    pass

                if not account.active():
                    await account.open()

                with Config() as config:
                    hubs = [Hub(name, account) for name in config.settings.get('hubs', [])]

                try:
                    if network.empty:
                        probe_period = 5
                        for hub in hubs:
                            await hub.empty()
                    else:
                        probe_period = 60
                        for hub in hubs:
                            await hub.occupied()
                except (RuntimeError, AttributeError) as e:
                    print(f"🔴 Erreur {type(e)}: {e}, nouvelle tentative d'authentification Blink...")
                    for hub in hubs:
                        hub.armed = None
                    await account.reauth()

                await configuration_page.report_status({'hubs': {hub.name: hub.armed for hub in hubs}, 'smartphones': network.presence})

                # Période de repos interruptible
                try:
                    sleep_task = asyncio.create_task(asyncio.sleep(probe_period))
                    config_task = asyncio.create_task(frontend.wait_for_message('configuration'))

                    done_wait, pending_wait = await asyncio.wait({sleep_task, config_task}, return_when=asyncio.FIRST_COMPLETED)

                    if config_task in done_wait:
                        settings = config_task.result()['configuration']
                        with Config() as config:
                            config.settings = settings
                        await configuration_page.display()

                    for task in pending_wait:
                        task.cancel()
                    await asyncio.gather(*pending_wait, return_exceptions=True)

                except Exception as e:
                    print(f'🔴 Erreur pendant la période de repos : {e}')

        except asyncio.CancelledError:
            break

        except Exception as e:
            print(f'🔴 Erreur dans la boucle de monitoring: {type(e)}: {e}')
            await asyncio.sleep(5)


# -----------------------------------------------
async def main():
    global main_task
    main_task = asyncio.current_task()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    default_config = {'interface': 'wlan0', 'debug': False, 'connections': ['WifiClient'], 'hubs': [], 'smartphones': {}}
    with Config(default_config) as config:
        settings = config.settings

    firmware = Firmware()

    frontend = Frontend()
    frontend.add_page(WifiPage('wifi'))
    frontend.add_page(CredentialsPage('credentials'))
    frontend.add_page(AuthenticationPage('authentication'))
    frontend.add_page(ConfigurationPage('configuration'))

    await frontend.start()

    account = BlinkAccount(frontend)

    network = Network(settings['interface'])
    wifi = Wifi(frontend, settings['interface'], settings['connections'])

    monitoring_task = asyncio.create_task(monitoring(firmware, frontend, wifi, network, account))

    try:
        await monitoring_task
    finally:
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

        await account.close()
        await frontend.stop()


# -----------------------------------------------
if __name__ == '__main__':
    asyncio.run(main())
