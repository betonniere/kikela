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

export default
{
  init(ws, data)
  {
    let socket = ws;
    const result = document.getElementById('result');

    document.getElementById('form').addEventListener('submit', (event) => {
      event.preventDefault();
      socket.send(JSON.stringify({ credentials: {'user': document.getElementById('user').value.trim(), 'password': document.getElementById('password').value.trim()}}));
    });

    if (data)
    {
      result.style.color = data.status == 'OK' ? 'var(--text-color)' : 'red';
      result.textContent = data.info;
    }
  }
}
