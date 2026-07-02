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

import json
import pathlib


# -------------------------------------------------
class Config:
    # -----------
    def __init__(self, default=None):
        self._default = default
        self._path = pathlib.Path(__file__).parent / 'config.json'

        self.settings = {}

    # -----------
    def __contains__(self, key):
        return key in self.settings

    # -----------
    def __getitem__(self, key):
        return self.settings[key]

    # -----------
    def __setitem__(self, key, value):
        self.settings[key] = value

    # -----------
    def _load(self):
        if self._path.exists():
            with self._path.open(encoding='utf-8') as f:
                self.settings = json.load(f)
        elif self._default is not None:
            self.settings = self._default

    # -----------
    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open('w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)

    # -----------
    def __enter__(self):
        self._load()
        return self

    # -----------
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._save()
