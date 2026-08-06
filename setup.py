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


import os
import pathlib
import shutil
import subprocess


# -----------------------------------------------
if __name__ == '__main__':
    print('Vérification des privilèges root...')
    if os.geteuid() != 0:
        print('Ce script doit être exécuté avec les privilèges root.')
        exit()

    print('Installation des dépendances apt...')
    cmd = ['apt-get', 'update']
    subprocess.run(cmd, check=True)

    cmd = ['apt-get', 'upgrade', '-y']
    subprocess.run(cmd, check=True)

    dependencies = ['arping', 'python3-aiofiles', 'python3-aiohttp', 'python3-dateutil', 'python3-rich', 'python3-slugify', 'python3-sortedcontainers']
    for dependency in dependencies:
        cmd = ['apt', 'install', '-y', dependency]
        subprocess.run(cmd, check=True)

    print('Rendre arping exécutable avec les privilèges root...')
    cmd = ['setcap', 'cap_net_raw+ep', '/usr/sbin/arping']
    subprocess.run(cmd, check=True)

    print('Copie des fichiers system...')
    source = pathlib.Path('root')
    destination = pathlib.Path('/')

    shutil.copytree(source, destination, dirs_exist_ok=True)

    print('Ajustement des permissions des fichiers de configuration...')
    connections = ['Hotspot', 'WifiClient']
    for connection in connections:
        pathlib.Path(f'/etc/NetworkManager/system-connections/{connection}.nmconnection').chmod(0o600)

    print('Configuration du mot de passe du hotspot...')
    hotspot_password = input('Mot de passe du hotspot : ')

    path = pathlib.Path('/etc/NetworkManager/system-connections/Hotspot.nmconnection')
    with path.open(encoding='utf-8') as f:
        settings = f.read()
        settings = settings.replace('psk=changeme', f'psk={hotspot_password}')

    with path.open('w', encoding='utf-8') as f:
        f.write(settings)

    print('Autorise la mise à jour du clone...')
    cmd = ['git', 'remote', 'rename', 'origin', 'upgrade']
    subprocess.run(cmd, check=False)

    cmd = ['git', 'submodule', 'update', '--init', '--recursive']
    subprocess.run(cmd, check=True)
