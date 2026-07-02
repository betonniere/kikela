#!/bin/bash

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

set -euo pipefail

readonly INTERFACE="wlan0"
readonly HOTSPOT_NAME="Hotspot"
readonly CLIENT_NAME="WifiClient"
readonly GPIO_PIN=21

# 1. Attente de la présence de l'interface Wi-Fi
while [[ ! -d "/sys/class/net/${INTERFACE}" ]]; do
    sleep 0.5
done

# 2. Activation du Wi-Fi et prise en charge par NetworkManager
nmcli radio wifi on
nmcli device set "${INTERFACE}" managed yes

# 3. Attente du statut "managed"
WAIT=0
while [[ ${WAIT} -lt 10 ]]; do
    STATE=$(nmcli -t -f DEVICE,STATE device | grep "^${INTERFACE}:" | cut -d: -f2 || true)
    if [[ -n "${STATE}" && "${STATE}" != "unmanaged" ]]; then
        break
    fi
    sleep 0.5
    WAIT=$((WAIT + 1))
done

# 4. Détection du mode forcé par GPIO
pinctrl set "${GPIO_PIN}" ip pu
GPIO_LEVEL=$(pinctrl lev "${GPIO_PIN}" 2>/dev/null || echo "1")

if [[ "${GPIO_LEVEL}" == "0" ]]; then
    echo "GPIO ${GPIO_PIN} détecté à l'état BAS. Mode Hotspot FORCÉ."
    nmcli connection up id "${HOTSPOT_NAME}"
    exit 0
fi

# 5. Tentative de connexion au client Wi-Fi
echo "Tentative de connexion à ${CLIENT_NAME}..."

if nmcli connection up id "${CLIENT_NAME}"; then
    echo "Connexion ${CLIENT_NAME} établie avec succès."
    exit 0
else
    echo "Échec de connexion à ${CLIENT_NAME} (Mot de passe invalide ou AP absent)."

    nmcli device disconnect "${INTERFACE}" || true
    sleep 1

    nmcli connection up id "${HOTSPOT_NAME}"
    exit 0
fi
