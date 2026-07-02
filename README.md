# Kikela

Kikela est un service Python (Raspberry Pi) qui arme et désarme automatiquement des
caméras [Blink](https://blinkforhome.com/) en fonction de la présence de smartphones
sur le réseau local. Quand aucun smartphone connu n'est détecté, les sync modules Blink sont armés,
dès qu'un smartphone revient sur le réseau, ils sont désarmés.

Le service embarque également une interface web de configuration gérant les paramètres suivants :

- Wi-Fi
- comptes Blink
- code d'authentification Blink
- liste des smartphones à détecter
- etc...

## Licence

Ce projet est distribué sous licence GNU General Public License v3 (ou ultérieure). Voir
les en-têtes de fichiers pour le détail.
