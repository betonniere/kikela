// Copyright (C) Yannick Le Roux.
// This file is part of Kikela.
//
//   Kikela is free software: you can redistribute it and/or modify
//   it under the terms of the GNU General Public License as published by
//   the Free Software Foundation, either version 3 of the License, or
//   (at your option) any later version.
//
//   Kikela is distributed in the hope that it will be useful,
//   but WITHOUT ANY WARRANTY; without even the implied warranty of
//   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//   GNU General Public License for more details.
//
//   You should have received a copy of the GNU General Public License
//   along with Kikela.  If not, see <http://www.gnu.org/licenses/>.

let lastStatus = { smartphones: {}, hubs: {} };

function renderBadge(el, isOn, onLabel, offLabel)
{
  if (isOn === null || isOn === undefined)
  {
    el.className = 'status-badge';
    el.textContent = '⏳ Inconnu';
    return;
  }

  el.className = 'status-badge ' + (isOn ? 'status-on' : 'status-off');
  el.textContent = isOn ? `🟢 ${onLabel}` : `⚫ ${offLabel}`;
}

function applyStatus()
{
  document.querySelectorAll('[data-smartphone-status]').forEach(el =>
  {
    const name = el.dataset.smartphoneStatus;
    renderBadge(el, lastStatus.smartphones[name], 'Présent', 'Absent');
  });

  document.querySelectorAll('[data-hub-status]').forEach(el =>
  {
    const name = el.dataset.hubStatus;
    renderBadge(el, lastStatus.hubs[name], 'Caméra ON', 'Caméra OFF');
  });
}

export default
{
  onMessage(msg)
  {
    if (msg.type !== 'status')
      return;

    lastStatus = msg.status;
    applyStatus();
  },

  init(ws, data)
  {
    let socket = ws;
    let config = data.config;

    const hubsContainer = document.getElementById('hubs-container');
    const smartphonesContainer = document.getElementById('smartphones-container');
    const addHubBtn = document.getElementById('add-hub-btn');
    const addSmartphoneBtn = document.getElementById('add-smartphone-btn');

    // --- Rendu ---

    function createHubDOM(val, index)
    {
      const div = document.createElement('div');
      div.className = 'dynamic-item';
      div.innerHTML = `
        <input type="text" value="${val}" style="flex-grow: 1;" data-role="hub-value" data-index="${index}" placeholder="Nom du Hub">
        <span class="status-badge" data-hub-status="${val}">⚪ ...</span>
        <button class="btn btn-danger" data-action="remove-hub" data-index="${index}">✕</button>
      `;
      return div;
    }

    function createSmartphoneDOM(name, data)
    {
      const div = document.createElement('div');
      div.className = 'smartphone-card';
      div.dataset.originalName = name;
      div.innerHTML = `
        <div class="card-header">
          <input type="text" class="phone-name" value="${name}" placeholder="Nom (ex: yannick)" style="font-weight: bold; background: transparent; border: none; border-bottom: 1px solid var(--border-color); color: var(--info); outline: none; padding: 2px;">
          <span class="status-badge" data-smartphone-status="${name}">⚪ ...</span>
          <button class="btn btn-danger" style="padding: 4px 8px; font-size: 0.75rem;" data-action="remove-smartphone">Supprimer</button>
        </div>
        <div class="grid-3">
          <div class="form-group" style="margin-bottom: 0;">
            <input type="text" class="phone-ip" value="${data.ip}" placeholder="192.168.1.X">
          </div>
        </div>
      `;
      return div;
    }

    function initUI()
    {
      hubsContainer.innerHTML = '';
      config.hubs.forEach((hub, index) =>
      {
        hubsContainer.appendChild(createHubDOM(hub, index));
      });

      smartphonesContainer.innerHTML = '';
      Object.keys(config.smartphones).forEach(name =>
      {
        smartphonesContainer.appendChild(createSmartphoneDOM(name, config.smartphones[name]));
      });

      applyStatus();
    }

    function refreshUI()
    {
      initUI();
      socket.send ('{"configuration": ' + JSON.stringify(config) + '}');
    }

    // --- Logique métier ---

    function addHub()
    {
      config.hubs.push("");
      refreshUI();
    }

    function removeHub(index)
    {
      config.hubs.splice(index, 1);
      refreshUI();
    }

    function addSmartphone()
    {
      const uniqueId = "nouveau_" + Date.now().toString().slice(-4);
      config.smartphones[uniqueId] = { ip: "192.168.1.100", arping_attemps: 3, arping_delay: 1 };
      refreshUI();
    }

    function removeSmartphone(name)
    {
      delete config.smartphones[name];
      refreshUI();
    }

    function updateSmartphoneData(cardEl)
    {
      const oldName = cardEl.dataset.originalName;
      const newName = cardEl.querySelector('.phone-name').value.trim() || oldName;
      const ip = cardEl.querySelector('.phone-ip').value;
      const attempts = config.smartphones[oldName]['arping_attemps'] || 3;
      const delay = config.smartphones[oldName]['arping_delay'] || 1;

      if (oldName !== newName)
      {
        delete config.smartphones[oldName];
        cardEl.dataset.originalName = newName;
        const badge = cardEl.querySelector('[data-smartphone-status]');
        if (badge)
          badge.dataset.smartphoneStatus = newName;
      }

      config.smartphones[newName] = { ip, arping_attemps: attempts, arping_delay: delay };
      socket.send ('{"configuration": ' + JSON.stringify(config) + '}');
    }

    // --- Écouteurs globaux (statiques, posés une seule fois) ---

    addHubBtn.addEventListener('click', addHub);
    addSmartphoneBtn.addEventListener('click', addSmartphone);

    // --- Délégation d'événements (pour les éléments générés dynamiquement) ---

    hubsContainer.addEventListener('click', (e) =>
    {
      const btn = e.target.closest('[data-action="remove-hub"]');
      if (btn)
        removeHub(Number(btn.dataset.index));
    });

    hubsContainer.addEventListener('input', (e) =>
    {
      if (e.target.dataset.role === 'hub-value')
      {
        config.hubs[Number(e.target.dataset.index)] = e.target.value;
        const badge = e.target.closest('.dynamic-item').querySelector('[data-hub-status]');
        if (badge)
          badge.dataset.hubStatus = e.target.value;
        socket.send ('{"configuration": ' + JSON.stringify(config) + '}');
      }
    });

    smartphonesContainer.addEventListener('click', (e) =>
    {
      const btn = e.target.closest('[data-action="remove-smartphone"]');
      if (btn)
        removeSmartphone(btn.closest('.smartphone-card').dataset.originalName);
    });

    smartphonesContainer.addEventListener('input', (e) =>
    {
      const card = e.target.closest('.smartphone-card');
      if (card)
        updateSmartphoneData(card);
    });

    initUI();

    lastStatus = data.status;
    applyStatus();
  }
}