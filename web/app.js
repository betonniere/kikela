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

const root = document.getElementById('app');
const ws = new WebSocket(`ws://${location.host}/ws`);

let currentPage = null;

async function loadPage(name, data)
{
  const response = await fetch(`/static/pages/${name}/page.html`);
  const html = await response.text();
  root.innerHTML = html;

  const mod = await import(`/static/pages/${name}/page.js`);
  currentPage = mod.default || null;
  if (currentPage && currentPage.init)
    currentPage.init(ws, data);
}

ws.onmessage = (e) =>
{
  const msg = JSON.parse(e.data);
  if (msg.type === 'display_page')
    loadPage(msg.name, msg.data);
  else if (currentPage && currentPage.onMessage)
    currentPage.onMessage(msg);
};
