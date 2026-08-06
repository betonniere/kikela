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

import datetime
import subprocess


# -------------------------------------------------
class Firmware:
    # -----------
    def __init__(self):
        self._url = None
        self._last_date_check = None
        self._check_period = datetime.timedelta(hours=24)

        stdout = self._run_command(['git', 'remote', 'get-url', 'upgrade'])

        if stdout is None:
            return

        if not stdout.startswith('https://'):
            return

        self._url = stdout.strip()

    # -----------
    def _run_command(self, command):
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"🔴 Erreur lors de l'exécution de la commande '{' '.join(command)}")
            return None

        return result.stdout.strip()

    # -----------
    def _get_latest_remote_tag(self):
        stdout = self._run_command(['git', 'ls-remote', '--tags', '--refs', self._url])
        if stdout is None:
            return None

        lines = stdout.split('\n')
        if not lines or lines == ['']:
            return None

        tags = [line.split('\t')[1].replace('refs/tags/', '') for line in lines]
        return tags[-1] if tags else None

    # -----------
    def _get_current_local_tag(self):
        stdout = self._run_command(['git', 'describe', '--tags', '--abbrev=0'])
        if stdout is None:
            return None

        return stdout.strip()

    # -----------
    def _checkout_tag(self, tag):
        if self._run_command(['git', 'fetch', '--force', '--tags', 'upgrade']) is None:
            return False

        if self._run_command(['git', 'checkout', f'tags/{tag}']) is None:
            return False

        return self._run_command(['git', 'submodule', 'update']) is not None

    # -----------
    def upgrade(self):
        if self._url is None:
            return

        current_time = datetime.datetime.now(datetime.UTC)
        if self._last_date_check is not None and (current_time - self._last_date_check) < self._check_period:
            return

        self._last_date_check = current_time

        remote_tag = self._get_latest_remote_tag()
        if remote_tag is None:
            print('🔴 Impossible de récupérer le dernier tag distant.')
            return

        local_tag = self._get_current_local_tag()

        if local_tag == remote_tag:
            print('ℹ️  Pas de mise à jour nécessaire du firmware.')
            return

        if not self._checkout_tag(remote_tag):
            print('🔴 Échec du checkout du tag.')
            return

        if self._run_command(['sudo', 'systemctl', 'restart', '--no-block', 'kikela.service']) is None:
            print('🔴 Échec du redémarrage du service.')
            return

        print(f'🟢 Mise à jour du firmware {remote_tag} réussie.')
