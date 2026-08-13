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

const REFRESH_INTERVAL_SECONDS = 5;
const SWITCHING_TIMEOUT_SECONDS = 20;

export default
{
  init(ws, data)
  {
    let socket = ws;
    const form = document.getElementById('form');
    const result = document.getElementById('result');
    const switching = document.getElementById('switching');
    const timeout = document.getElementById('timeout');
    const passwordInput = document.getElementById('password');
    const togglePassword = document.getElementById('toggle-password');

    togglePassword.addEventListener('click', () => {
      const isHidden = passwordInput.type === 'password';
      passwordInput.type = isHidden ? 'text' : 'password';
      togglePassword.textContent = isHidden ? '🙈' : '👁';
      togglePassword.setAttribute('aria-label', isHidden ? 'Masquer le mot de passe' : 'Afficher le mot de passe');
    });

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      socket.send(JSON.stringify({ wifi: {'ssid': document.getElementById('ssid').value.trim(), 'password': document.getElementById('password').value.trim()}}));
    });

    if (data && data.status === 'SWITCHING')
    {
      startSwitchingScreen(form, result, switching, timeout);
      return;
    }

    form.style.display = '';
    result.style.display = '';
    switching.style.display = 'none';
    timeout.style.display = 'none';

    if (data)
    {
      result.style.color = data.status == 'OK' ? 'var(--text-color)' : 'red';
      result.textContent = data.info;
    }
  }
}

function startSwitchingScreen(form, result, switching, timeout)
{
  form.style.display = 'none';
  result.style.display = 'none';
  switching.style.display = 'flex';
  timeout.style.display = 'none';

  let remaining = REFRESH_INTERVAL_SECONDS;
  let elapsed = 0;
  let timedOut = false;

  setInterval(() => {
    elapsed += 1;

    if (!timedOut && elapsed >= SWITCHING_TIMEOUT_SECONDS)
    {
      timedOut = true;
      switching.style.display = 'none';
      timeout.style.display = 'flex';
    }

    remaining -= 1;
    if (remaining <= 0)
    {
      remaining = REFRESH_INTERVAL_SECONDS;
      tryReload();
    }
  }, 1000);
}

function tryReload()
{
  fetch(location.href, { cache: 'no-store', signal: AbortSignal.timeout(3000) })
    .then(() => location.reload())
    .catch(() => {});
}
