# README

## 1. arping

sudo setcap cap_net_raw+ep /usr/sbin/arping

## 2. Dépendances

sudo apt install arping
sudo apt install python3-aiofiles
sudo apt install python3-aiohttp
sudo apt install python3-dateutil
sudo apt install python3-rich
sudo apt install python3-slugify
sudo apt install python3-sortedcontainers

## 3. Création des profils réseaux

### Hotspot

sudo nmcli con add type wifi ifname wlan0 mode ap con-name Hotspot ssid "Kikela"

sudo nmcli con modify Hotspot 802-11-wireless.band bg
sudo nmcli con modify Hotspot 802-11-wireless-security.key-mgmt wpa-psk
sudo nmcli con modify Hotspot 802-11-wireless-security.proto rsn
sudo nmcli con modify Hotspot 802-11-wireless-security.psk "changeme"
sudo nmcli con modify Hotspot connection.autoconnect no
sudo nmcli con modify Hotspot ipv4.method shared
sudo nmcli con modify Hotspot ipv4.addresses 10.3.141.1/24
sudo nmcli con modify Hotspot ipv6.method disabled

### WifiClient

sudo nmcli con add type wifi ifname wlan0 con-name WifiClient ssid "GaletteSaucisse"

sudo nmcli con modify WifiClient 802-11-wireless-security.key-mgmt wpa-psk
sudo nmcli con modify WifiClient 802-11-wireless-security.psk "changeme"
sudo nmcli con modify WifiClient connection.autoconnect yes
sudo nmcli con modify WifiClient connection.auth-retries 1
sudo nmcli con modify WifiClient connection.autoconnect-retries 1
sudo nmcli con modify WifiClient ipv4.dhcp-timeout 5

### Suppression du profil préconfiguré

sudo nmcli con delete preconfigured
