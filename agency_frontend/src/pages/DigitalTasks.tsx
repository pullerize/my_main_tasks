import { useEffect, useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { API_URL } from '../api';
import DigitalProject from './DigitalProject';
import { formatDateTimeUTC5 } from '../utils/dateUtils';
import { usePersistedState } from '../utils/filterStorage';

interface ProjectOption { id: number; name: string }
interface Service { id: number; name: string }
interface User { id: number; name: string; role: string }

interface DigitalItem {
  id: number;
  project_id: number;
  project: string;
  service_id: number;
  service: string;
  executor_id: number;
  executor: string;
  created_at: string;
  deadline?: string;
  monthly: boolean;
  logo?: string | null;
  high_priority?: boolean;
  status: string;
}

function timeLeft(dateStr: string) {
  const diff = new Date(dateStr).getTime() - Date.now();
  if (diff <= 0) return 'Просрочено';
  const days = Math.floor(diff / 86400000);
  const hours = Math.floor((diff % 86400000) / 3600000);
  const minutes = Math.floor((diff % 3600000) / 60000);
  if (days > 0) {
    return `${days}д ${hours}ч ${minutes}м`;
  }
  const seconds = Math.floor((diff % 60000) / 1000);
  return `${hours}ч ${minutes}м ${seconds}с`;
}

function getTaskStatus(item: DigitalItem) {
  if (item.status === 'completed') return 'Завершено';
  if (item.monthly) return 'В работе';
  if (!item.deadline) return 'В работе';
  const diff = new Date(item.deadline).getTime() - Date.now();
  if (diff <= 0) return 'Просрочено';
  return 'В работе';
}

function DigitalList() {
  const token = localStorage.getItem('token');
  const [items, setItems] = useState<DigitalItem[]>([]);
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [show, setShow] = useState(false);
  const [proj, setProj] = useState('');
  const [service, setService] = useState('');
  const [executor, setExecutor] = useState('');
  const [deadlineDate, setDeadlineDate] = useState('');
  const [deadlineTime, setDeadlineTime] = useState('');
  const [monthly, setMonthly] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [filterProj, setFilterProj] = usePersistedState('filter_digital_project', '');
  const [filterService, setFilterService] = usePersistedState('filter_digital_service', '');
  const [filterExec, setFilterExec] = usePersistedState('filter_digital_executor', '');
  const [filterDate, setFilterDate] = usePersistedState('filter_digital_date', 'all');
  const [customDate, setCustomDate] = usePersistedState('filter_digital_custom_date', '');
  const [filterStatus, setFilterStatus] = usePersistedState('filter_digital_status', '');
  const [timezone, setTimezone] = useState('Asia/Tashkent');
  const navigate = useNavigate();

  const load = async () => {
    if (!token) {
      setProjects([])
      setServices([])
      setUsers([])
      setItems([])
      return
    }

    try {
      const [resP, resS, resU, resD, resT] = await Promise.all([
        fetch(`${API_URL}/projects/`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/digital/services`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/users/`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/digital/projects`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/settings/timezone`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      
      if (resP.ok) {
        const data = await resP.json()
        setProjects(Array.isArray(data) ? data : [])
      } else {
        setProjects([])
      }
      
      if (resS.ok) {
        const data = await resS.json()
        setServices(Array.isArray(data) ? data : [])
      } else {
        setServices([])
      }
      
      if (resU.ok) {
        const data = await resU.json()
        setUsers(Array.isArray(data) ? data : [])
      } else {
        setUsers([])
      }
      
      if (resD.ok) {
        const data = await resD.json()
        const items: DigitalItem[] = Array.isArray(data) ? data : []
        items.sort((a,b)=> (b.high_priority?1:0)-(a.high_priority?1:0) || ((a.deadline?new Date(a.deadline).getTime():Infinity)-(b.deadline?new Date(b.deadline).getTime():Infinity)));
        setItems(items);
      } else {
        setItems([])
      }
      
      if (resT.ok) { 
        const data = await resT.json()
        if (data && data.timezone) setTimezone(data.timezone)
      }
    } catch (error) {
      setProjects([])
      setServices([])
      setUsers([])
      setItems([])
    }
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const id = setInterval(() => setItems(it => [...it]), 1000);
    return () => clearInterval(id);
  }, []);

  const save = async () => {
    if (!proj || !service || !executor) return;
    const deadline = monthly || !deadlineDate || !deadlineTime ? null : `${deadlineDate}T${deadlineTime}`;
    const payload = {
      project_id: Number(proj),
      service_id: Number(service),
      executor_id: Number(executor),
      deadline,
      monthly,
      status: 'in_progress'
    };
    const url = editId ? `${API_URL}/digital/projects/${editId}` : `${API_URL}/digital/projects`;
    const method = editId ? 'PUT' : 'POST';
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const item = await res.json();
      if (editId) {
        setItems(Array.isArray(items) ? items.map(i => (i.id === editId ? item : i)) : []);
      } else {
        setItems(Array.isArray(items) ? [...items, item] : [item]);
      }
      setShow(false);
      setProj('');
      setService('');
      setExecutor('');
      setDeadlineDate('');
      setDeadlineTime('');
      setMonthly(false);
      setEditId(null);
    }
  };

  const completeTask = async (id: number) => {
    const res = await fetch(`${API_URL}/digital/projects/${id}/status?status=completed`, {
      method: 'PUT',
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.ok) {
      const updatedItem = await res.json();
      setItems(Array.isArray(items) ? items.map(i => i.id === id ? updatedItem : i) : []);
    }
  };

  const reactivateTask = async (id: number) => {
    const res = await fetch(`${API_URL}/digital/projects/${id}/status?status=in_progress`, {
      method: 'PUT',
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.ok) {
      const updatedItem = await res.json();
      setItems(Array.isArray(items) ? items.map(i => i.id === id ? updatedItem : i) : []);
    }
  };

  const remove = async (id: number) => {
    await fetch(`${API_URL}/digital/projects/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    });
    setItems(Array.isArray(items) ? items.filter(i => i.id !== id) : []);
    if (editId === id) setShow(false);
  };

  const handleTimeChange = (val: string) => {
    let v = val.replace(/\D/g, '').slice(0, 4);
    if (v.length >= 3) v = v.slice(0, 2) + ':' + v.slice(2);
    setDeadlineTime(v);
  };

  const openAdd = () => {
    setEditId(null);
    setProj('');
    setService('');
    setExecutor('');
    setDeadlineDate('');
    setDeadlineTime('');
    setMonthly(false);
    setShow(true);
  };

  const openEdit = (it: DigitalItem) => {
    setEditId(it.id);
    setProj(String(it.project_id));
    setService(String(it.service_id));
    setExecutor(String(it.executor_id));
    if (it.deadline) {
      const d = new Date(it.deadline);
      setDeadlineDate(d.toISOString().slice(0, 10));
      setDeadlineTime(d.toISOString().slice(11, 16));
    } else {
      setDeadlineDate('');
      setDeadlineTime('');
    }
    setMonthly(it.monthly);
    setShow(true);
  };

  const togglePriority = async (it: DigitalItem) => {
    await fetch(`${API_URL}/projects/${it.project_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: it.project, high_priority: !it.high_priority })
    });
    const updatedItems = Array.isArray(items) ? items.map(p => p.id === it.id ? { ...p, high_priority: !p.high_priority } : p) : []
    updatedItems.sort((a,b)=> (b.high_priority?1:0)-(a.high_priority?1:0) || ((a.deadline?new Date(a.deadline).getTime():Infinity)-(b.deadline?new Date(b.deadline).getTime():Infinity)))
    setItems(updatedItems);
  };

  return (
    <div className="w-full overflow-hidden bg-gray-50 min-h-screen">
      <div className="bg-white shadow-sm border-b p-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Digital Задачи</h1>
            <p className="text-gray-600 mt-1">Управляйте digital проектами и отслеживайте прогресс</p>
          </div>
        </div>
      </div>
      
      <div className="bg-white p-6 shadow-sm border-b">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex flex-wrap gap-3">
            <select className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" value={filterProj} onChange={e => setFilterProj(e.target.value)}>
              <option value="">Все проекты</option>
              {Array.isArray(projects) && projects.map(p => <option key={p.id} value={p.name}>{p.name}</option>)}
            </select>
            <select className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" value={filterService} onChange={e => setFilterService(e.target.value)}>
              <option value="">Все услуги</option>
              {Array.isArray(services) && services.map(s => <option key={s.id} value={s.name}>{s.name}</option>)}
            </select>
            <select className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" value={filterExec} onChange={e => setFilterExec(e.target.value)}>
              <option value="">Все исполнители</option>
              {Array.isArray(users) && users.filter(u => u.role === 'digital').map(u => <option key={u.id} value={u.name}>{u.name}</option>)}
            </select>
            <select className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
              <option value="">Все статусы</option>
              <option value="В работе">В работе</option>
              <option value="Завершено">Завершено</option>
              <option value="Просрочено">Просрочено</option>
            </select>
            <select className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" value={filterDate} onChange={e => setFilterDate(e.target.value)}>
              <option value="all">За все время</option>
              <option value="today">За сегодня</option>
              <option value="week">За неделю</option>
              <option value="month">За месяц</option>
              <option value="custom">Выбрать дату</option>
            </select>
            {filterDate === 'custom' && (
              <input type="date" className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" value={customDate} onChange={e => setCustomDate(e.target.value)} />
            )}
          </div>
          <button
            className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white px-6 py-3 rounded-lg font-medium shadow-lg transform hover:scale-105 transition-all duration-200 flex items-center space-x-2"
            onClick={openAdd}
          >
            <span>+</span>
            <span>Добавить проект</span>
          </button>
        </div>
      </div>

      <div className="p-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[50px]">
                    Статус
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[200px]">
                    Проект
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[150px]">
                    Вид услуги
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[120px]">
                    Исполнитель
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[140px]">
                    Время создания
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[120px]">
                    Дедлайн
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[160px]">
                    Действия
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {Array.isArray(items) && items.filter(it => {
                  if (filterProj && it.project !== filterProj) return false;
                  if (filterService && it.service !== filterService) return false;
                  if (filterExec && it.executor !== filterExec) return false;
                  if (filterStatus && getTaskStatus(it) !== filterStatus) return false;
                  const created = new Date(it.created_at.endsWith('Z') ? it.created_at : it.created_at + 'Z');
                  if (filterDate === 'today') {
                    const now = new Date();
                    if (created.toDateString() !== now.toDateString()) return false;
                  } else if (filterDate === 'week') {
                    if (Date.now() - created.getTime() > 7 * 86400000) return false;
                  } else if (filterDate === 'month') {
                    if (Date.now() - created.getTime() > 30 * 86400000) return false;
                  } else if (filterDate === 'custom' && customDate) {
                    const sel = new Date(customDate);
                    if (created.toDateString() !== sel.toDateString()) return false;
                  }
                  return true;
                }).map(it => (
                  <tr key={it.id} className="hover:bg-gray-50 transition-colors duration-150 cursor-pointer" onClick={() => navigate(String(it.id), { state: it })}>
                    <td className="px-6 py-4" onClick={e => {e.stopPropagation(); togglePriority(it);}}>
                      <span className={`text-2xl cursor-pointer ${it.high_priority ? 'text-yellow-500' : 'text-gray-300'}`}>
                        {it.high_priority ? '★' : '☆'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        {it.logo ? (
                          <img src={`${API_URL}/${it.logo}`} alt={it.project} className="w-8 h-8 rounded-full" />
                        ) : (
                          <div className="text-sm font-medium text-gray-900 truncate max-w-[180px]">
                            {it.project}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 truncate max-w-[130px]">{it.service}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 truncate max-w-[100px]">{it.executor}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">
                        {formatDateTimeUTC5(it.created_at)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {it.monthly ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          🔄 Ежемесячно
                        </span>
                      ) : it.deadline ? (
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          timeLeft(it.deadline) === 'Просрочено' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                        }`}>
                          {timeLeft(it.deadline) === 'Просрочено' ? '🚫 Просрочено' : `⏰ ${timeLeft(it.deadline)}`}
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          ⏰ Не установлен
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4" onClick={e => e.stopPropagation()}>
                      <div className="flex gap-2 justify-start flex-wrap">
                        {getTaskStatus(it) !== 'Завершено' && (
                          <button 
                            className="inline-flex items-center px-3 py-1.5 border border-blue-300 text-xs font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors" 
                            onClick={() => openEdit(it)}
                          >
                            Редактировать
                          </button>
                        )}
                        {getTaskStatus(it) !== 'Завершено' ? (
                          <button 
                            className="inline-flex items-center px-3 py-1.5 border border-green-300 text-xs font-medium rounded-md text-green-700 bg-green-50 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors" 
                            onClick={() => completeTask(it.id)}
                          >
                            Завершить
                          </button>
                        ) : (
                          <button
                            className="inline-flex items-center px-3 py-1.5 border border-green-300 text-xs font-medium rounded-md text-green-700 bg-green-50 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors cursor-pointer"
                            onClick={() => reactivateTask(it.id)}
                          >
                            ✅ Завершено
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {Array.isArray(items) && items.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">💻</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Нет digital проектов</h3>
              <p className="text-gray-500">Создайте первый digital проект!</p>
            </div>
          )}
        </div>
      </div>

      {show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-4 rounded w-[32rem] space-y-2">
            <h3 className="text-lg mb-2">{editId ? 'Редактировать проект' : 'Новый проект'}</h3>
            <select className="border p-2 w-full" value={proj} onChange={e => setProj(e.target.value)}>
              <option value="">Выберите проект</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <select className="border p-2 w-full" value={service} onChange={e => setService(e.target.value)}>
              <option value="">Выберите услугу</option>
              {services.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select className="border p-2 w-full" value={executor} onChange={e => setExecutor(e.target.value)}>
              <option value="">Выберите исполнителя</option>
              {users.filter(u => u.role === 'digital').map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
            {!monthly && (
              <div className="flex gap-2">
                <input type="date" className="border p-2 flex-1" value={deadlineDate} onChange={e => setDeadlineDate(e.target.value)} />
                <input className="border p-2 w-24" placeholder="00:00" value={deadlineTime} onChange={e => handleTimeChange(e.target.value)} />
              </div>
            )}
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={monthly} onChange={e => setMonthly(e.target.checked)} />
              Ежемесячно
            </label>
            <div className="text-right space-x-2">
              <button className="px-3 py-1 border rounded" onClick={() => { setShow(false); setEditId(null); }}>Отмена</button>
              {editId && <button className="px-3 py-1 bg-red-500 text-white rounded" onClick={() => remove(editId)}>Удалить</button>}
              <button className="px-3 py-1 bg-green-500 text-white rounded" onClick={save}>Сохранить</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DigitalTasks() {
  return (
    <Routes>
      <Route index element={<DigitalList />} />
      <Route path=":id" element={<DigitalProject />} />
    </Routes>
  );
}
