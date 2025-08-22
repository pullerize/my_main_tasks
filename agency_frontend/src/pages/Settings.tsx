import { useEffect, useState } from 'react';
import { API_URL } from '../api';

const zones = ['Asia/Tashkent','UTC','Europe/Moscow','Asia/Almaty','Asia/Bishkek'];

export default function Settings() {
  const token = localStorage.getItem('token');
  const [timezone, setTimezone] = useState('Asia/Tashkent');

  useEffect(() => {
    const load = async () => {
      const res = await fetch(`${API_URL}/settings/timezone`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        setTimezone(data.timezone);
      }
    };
    load();
  }, []);

  const save = async () => {
    await fetch(`${API_URL}/settings/timezone`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ timezone })
    });
  };

  return (
    <div className="p-4 space-y-2">
      <label className="block">Часовой пояс
        <select className="border p-2 ml-2" value={timezone} onChange={e => setTimezone(e.target.value)}>
          {zones.map(z => <option key={z} value={z}>{z}</option>)}
        </select>
      </label>
      <button className="px-3 py-1 bg-blue-500 text-white rounded" onClick={save}>Сохранить</button>
    </div>
  );
}
