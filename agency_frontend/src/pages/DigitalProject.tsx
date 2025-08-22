import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { API_URL } from '../api';

interface LinkItem { id: number; name: string; url: string }
interface TaskItem {
  id: number;
  title: string;
  description: string;
  links: LinkItem[];
  created_at: string;
  deadline?: string;
  high_priority?: boolean;
  status?: 'completed' | 'in_progress';
}

interface ProjectInfo {
  id: number;
  project_id: number;
  project: string;
  service_id: number;
  executor_id: number;
  deadline?: string;
  monthly: boolean;
  logo?: string | null;
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

function getTaskStatus(task: TaskItem): string {
  if (task.status === 'completed') return 'Завершено';
  if (!task.deadline) return 'В работе';
  const diff = new Date(task.deadline).getTime() - Date.now();
  if (diff <= 0) return 'Просрочено';
  return 'В работе';
}

const sortTasks = (tasks: TaskItem[]): TaskItem[] => {
  return tasks.sort((a, b) => {
    // 1. Приоритет: высокий приоритет всегда наверху
    if (a.high_priority !== b.high_priority) {
      return b.high_priority ? 1 : -1;
    }
    
    // 2. Статус: в работе наверху, завершенные внизу
    const statusA = getTaskStatus(a);
    const statusB = getTaskStatus(b);
    if (statusA !== statusB) {
      if (statusA === 'В работе' && statusB !== 'В работе') return -1;
      if (statusA !== 'В работе' && statusB === 'В работе') return 1;
      if (statusA === 'Просрочено' && statusB === 'Завершено') return -1;
      if (statusA === 'Завершено' && statusB === 'Просрочено') return 1;
    }
    
    // 3. Дедлайн: ближайший дедлайн наверху
    const deadlineA = a.deadline ? new Date(a.deadline).getTime() : Infinity;
    const deadlineB = b.deadline ? new Date(b.deadline).getTime() : Infinity;
    return deadlineA - deadlineB;
  });
};

export default function DigitalProject() {
  const { state } = useLocation();
  const [project, setProject] = useState<ProjectInfo | undefined>(state as ProjectInfo | undefined);
  const token = localStorage.getItem('token');
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [filterDate, setFilterDate] = useState('all');
  const [customDate, setCustomDate] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [show, setShow] = useState(false);
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [links, setLinks] = useState<LinkItem[]>([]);
  const [linksModal, setLinksModal] = useState<LinkItem[] | null>(null);
  const [deadlineDate, setDeadlineDate] = useState('');
  const [deadlineTime, setDeadlineTime] = useState('');
  const [editId, setEditId] = useState<number | null>(null);
  const [timezone, setTimezone] = useState('Asia/Tashkent');
  const [confirm, setConfirm] = useState(false);
  const [pendingPayload, setPendingPayload] = useState<any | null>(null);
  const [pendingDeadline, setPendingDeadline] = useState<string | null>(null);

  const load = async () => {
    if (!project) return;
    const [res, tz] = await Promise.all([
      fetch(`${API_URL}/digital/projects/${project.id}/tasks`, {
        headers: { Authorization: `Bearer ${token}` }
      }),
      fetch(`${API_URL}/settings/timezone`, { headers: { Authorization: `Bearer ${token}` } })
    ]);
    if (res.ok) {
      const data: TaskItem[] = await res.json();
      const sortedData = sortTasks(data);
      setTasks(sortedData.map(t => ({ ...t, links: t.links.map((l, i) => ({ ...l, id: i })) })));
    }
    if (tz.ok) { const d = await tz.json(); setTimezone(d.timezone); }
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    const id = setInterval(() => setTasks(ts => [...ts]), 1000);
    return () => clearInterval(id);
  }, []);

  const submitTask = async (payload: any) => {
    if (!project) return;
    const url = editId ? `${API_URL}/digital/projects/${project.id}/tasks/${editId}` : `${API_URL}/digital/projects/${project.id}/tasks`;
    const method = editId ? 'PUT' : 'POST';
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const item: TaskItem = await res.json();
      item.links = item.links.map((l, i) => ({ ...l, id: i }));
      if (editId) {
        setTasks(sortTasks(tasks.map(t => (t.id === editId ? item : t))));
      } else {
        setTasks(sortTasks([...tasks, item]));
      }
      setShow(false);
      setTitle('');
      setDesc('');
      setLinks([]);
      setDeadlineDate('');
      setDeadlineTime('');
      setEditId(null);
    }
  };

  const saveTask = async () => {
    if (!project || !title) return;
    const deadline = !deadlineDate || !deadlineTime ? null : `${deadlineDate}T${deadlineTime}`;
    const payload = {
      title,
      description: desc,
      deadline,
      links: links.map(({ name, url }) => ({ name, url })),
      high_priority: editId ? tasks.find(t => t.id === editId)?.high_priority ?? false : false
    };
    if (deadline && project.deadline && new Date(deadline) > new Date(project.deadline)) {
      setPendingPayload(payload);
      setPendingDeadline(deadline);
      setConfirm(true);
      return;
    }
    await submitTask(payload);
  };

  const continueWithDeadline = async () => {
    if (!project || !pendingPayload || !pendingDeadline) return;
    await fetch(`${API_URL}/digital/projects/${project.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        project_id: project.project_id,
        service_id: project.service_id,
        executor_id: project.executor_id,
        deadline: pendingDeadline,
        monthly: project.monthly
      })
    });
    setProject({ ...project, deadline: pendingDeadline });
    await submitTask(pendingPayload);
    setConfirm(false);
    setPendingPayload(null);
    setPendingDeadline(null);
  };

  const addLink = () => setLinks([...links, { id: Date.now(), name: '', url: '' }]);

  const updateLink = (id: number, field: 'name' | 'url', value: string) => {
    setLinks(links.map(l => (l.id === id ? { ...l, [field]: value } : l)));
  };

  const handleTimeChange = (val: string) => {
    let v = val.replace(/\D/g, '').slice(0, 4);
    if (v.length >= 3) v = v.slice(0, 2) + ':' + v.slice(2);
    setDeadlineTime(v);
  };

  const openAdd = () => {
    setEditId(null);
    setTitle('');
    setDesc('');
    setLinks([]);
    setDeadlineDate('');
    setDeadlineTime('');
    setShow(true);
  };

  const openEdit = (t: TaskItem) => {
    setEditId(t.id);
    setTitle(t.title);
    setDesc(t.description);
    setLinks(t.links.map((l, i) => ({ ...l, id: i }))); // ensure ids
    if (t.deadline) {
      const d = new Date(t.deadline);
      setDeadlineDate(d.toISOString().slice(0, 10));
      setDeadlineTime(d.toISOString().slice(11, 16));
    } else {
      setDeadlineDate('');
      setDeadlineTime('');
    }
    setShow(true);
  };

  const toggleTaskPriority = async (t: TaskItem) => {
    if (!project) return;
    await fetch(`${API_URL}/digital/projects/${project.id}/tasks/${t.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        title: t.title,
        description: t.description,
        deadline: t.deadline,
        links: t.links.map(({name,url})=>({name,url})),
        high_priority: !t.high_priority
      })
    });
    setTasks(sortTasks(tasks.map(it => it.id === t.id ? { ...it, high_priority: !it.high_priority } : it)));
  };

  const completeTask = async (id: number) => {
    if (!project) return;
    const task = tasks.find(t => t.id === id);
    if (!task) return;
    
    const newStatus = task.status === 'completed' ? 'in_progress' : 'completed';
    
    const res = await fetch(`${API_URL}/digital/projects/${project.id}/tasks/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        title: task.title,
        description: task.description,
        deadline: task.deadline,
        links: task.links.map(({name,url})=>({name,url})),
        high_priority: task.high_priority,
        status: newStatus
      })
    });
    
    if (res.ok) {
      const updatedTask = await res.json();
      updatedTask.links = updatedTask.links.map((l: any, i: number) => ({ ...l, id: i }));
      setTasks(sortTasks(tasks.map(t => t.id === id ? updatedTask : t)));
    }
  };

  const remove = async (id: number) => {
    await fetch(`${API_URL}/digital/projects/${project?.id}/tasks/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    });
    setTasks(tasks.filter(t => t.id !== id));
    if (editId === id) setShow(false);
  };

  const filtered = tasks.filter(t => {
    // Фильтр по статусу
    if (filterStatus !== 'all') {
      const taskStatus = getTaskStatus(t);
      if (filterStatus !== taskStatus) return false;
    }
    
    // Фильтр по дате
    if (filterDate === 'today') {
      const d = new Date(t.created_at.endsWith('Z') ? t.created_at : t.created_at + 'Z');
      const now = new Date();
      return d.toDateString() === now.toDateString();
    }
    if (filterDate === 'week') {
      const d = new Date(t.created_at.endsWith('Z') ? t.created_at : t.created_at + 'Z').getTime();
      return Date.now() - d <= 7 * 86400000;
    }
    if (filterDate === 'month') {
      const d = new Date(t.created_at.endsWith('Z') ? t.created_at : t.created_at + 'Z').getTime();
      return Date.now() - d <= 30 * 86400000;
    }
    if (filterDate === 'custom' && customDate) {
      const d = new Date(t.created_at.endsWith('Z') ? t.created_at : t.created_at + 'Z');
      const sel = new Date(customDate);
      return d.toDateString() === sel.toDateString();
    }
    return true;
  });

  return (
    <div className="w-full overflow-hidden bg-gray-50 min-h-screen">
      {/* Header with project info */}
      <div className="bg-white shadow-sm border-b p-6">
        <div className="flex items-center space-x-4">
          {project?.logo ? (
            <img src={`${API_URL}/${project.logo}`} className="w-16 h-16 rounded-lg object-cover" alt={project.project} />
          ) : (
            <div className="w-16 h-16 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <span className="text-white text-2xl font-bold">{project?.project?.charAt(0) || 'D'}</span>
            </div>
          )}
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {project?.logo ? 'Задачи проекта' : project?.project}
            </h1>
            <p className="text-gray-600 mt-1">Управление задачами проекта</p>
          </div>
        </div>
      </div>

      {/* Filters and actions */}
      <div className="bg-white p-6 shadow-sm border-b">
        <div className="flex flex-wrap gap-4 items-center justify-between">
          <div className="flex flex-wrap gap-3">
            <select className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
              <option value="all">Все задачи</option>
              <option value="Просрочено">Просрочено</option>
              <option value="В работе">В работе</option>
              <option value="Завершено">Завершено</option>
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
            <span>Добавить задачу</span>
          </button>
        </div>
      </div>
      {/* Tasks table */}
      <div className="p-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          {filtered.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[50px]">
                      Приоритет
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[200px]">
                      Название задачи
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[250px]">
                      Описание
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[120px]">
                      Ссылки
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[140px]">
                      Создано
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
                  {filtered.map(t => (
                    <tr key={t.id} className="hover:bg-gray-50 transition-colors duration-150">
                      <td className="px-6 py-4" onClick={() => toggleTaskPriority(t)}>
                        <span className={`text-2xl cursor-pointer ${t.high_priority ? 'text-yellow-500' : 'text-gray-300'}`}>
                          {t.high_priority ? '★' : '☆'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900 truncate max-w-[180px]">
                          {t.title}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-700 max-w-[230px] truncate" title={t.description}>
                          {t.description || <span className="text-gray-400 italic">Нет описания</span>}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {t.links.length > 0 ? (
                          <button 
                            className="inline-flex items-center px-3 py-1.5 border border-blue-300 text-xs font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                            onClick={() => setLinksModal(t.links)}
                          >
                            🔗 {t.links.length} ссылок
                          </button>
                        ) : (
                          <span className="text-gray-400 text-sm">Нет ссылок</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900">
                          {new Date(t.created_at.endsWith('Z') ? t.created_at : t.created_at + 'Z').toLocaleString('ru-RU', { 
                            timeZone: timezone,
                            day: '2-digit',
                            month: '2-digit',
                            year: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {t.deadline ? (
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            timeLeft(t.deadline) === 'Просрочено' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                          }`}>
                            {timeLeft(t.deadline) === 'Просрочено' ? '🚫 Просрочено' : `⏰ ${timeLeft(t.deadline)}`}
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            ⏰ Не установлен
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex gap-2 justify-start flex-wrap">
                          {getTaskStatus(t) !== 'Завершено' && (
                            <button 
                              className="inline-flex items-center px-3 py-1.5 border border-blue-300 text-xs font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors" 
                              onClick={() => openEdit(t)}
                            >
                              Редактировать
                            </button>
                          )}
                          <button 
                            className="inline-flex items-center px-3 py-1.5 border border-green-300 text-xs font-medium rounded-md text-green-700 bg-green-50 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors" 
                            onClick={() => completeTask(t.id)}
                          >
                            {getTaskStatus(t) === 'Завершено' ? '✅ Завершено' : 'Завершить'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">📋</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Нет задач</h3>
              <p className="text-gray-500 mb-6">Создайте первую задачу для этого проекта!</p>
              <button
                className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white px-6 py-3 rounded-lg font-medium shadow-lg transform hover:scale-105 transition-all duration-200"
                onClick={openAdd}
              >
                Добавить задачу
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Task creation/edit modal */}
      {show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-[40rem] max-w-[90vw] max-h-[90vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-xl font-semibold text-gray-900">{editId ? 'Редактировать задачу' : 'Новая задача'}</h3>
            </div>
            <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Название задачи *
                </label>
                <input 
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" 
                  placeholder="Введите название задачи" 
                  value={title} 
                  onChange={e => setTitle(e.target.value)} 
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Описание
                </label>
                <textarea 
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors resize-none" 
                  placeholder="Опишите задачу подробнее..." 
                  rows={4}
                  value={desc} 
                  onChange={e => setDesc(e.target.value)} 
                />
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="block text-sm font-medium text-gray-700">
                    Полезные ссылки
                  </label>
                  <button 
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                    onClick={addLink}
                  >
                    + Добавить ссылку
                  </button>
                </div>
                <div className="space-y-3">
                  {links.map(l => (
                    <div key={l.id} className="grid grid-cols-2 gap-3">
                      <input 
                        className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" 
                        placeholder="Название ссылки" 
                        value={l.name} 
                        onChange={e => updateLink(l.id, 'name', e.target.value)} 
                      />
                      <input 
                        className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" 
                        placeholder="https://example.com" 
                        value={l.url} 
                        onChange={e => updateLink(l.id, 'url', e.target.value)} 
                      />
                    </div>
                  ))}
                  {links.length === 0 && (
                    <p className="text-gray-500 text-sm italic">Нет ссылок</p>
                  )}
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Дедлайн
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <input 
                    type="date" 
                    className="border border-gray-300 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" 
                    value={deadlineDate} 
                    onChange={e => setDeadlineDate(e.target.value)} 
                  />
                  <input 
                    className="border border-gray-300 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" 
                    placeholder="00:00" 
                    value={deadlineTime} 
                    onChange={e => handleTimeChange(e.target.value)} 
                  />
                </div>
              </div>
            </div>
            <div className="p-6 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
              <button 
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors font-medium"
                onClick={() => { setShow(false); setEditId(null); }}
              >
                Отмена
              </button>
              {editId && (
                <button 
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
                  onClick={() => remove(editId)}
                >
                  Удалить
                </button>
              )}
              <button 
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={saveTask}
                disabled={!title.trim()}
              >
                {editId ? 'Сохранить изменения' : 'Создать задачу'}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Confirm deadline modal */}
      {confirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-96 overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Предупреждение о дедлайне</h3>
            </div>
            <div className="p-6">
              <div className="flex items-start space-x-3">
                <div className="text-yellow-500 text-2xl">⚠️</div>
                <div>
                  <p className="text-gray-900 font-medium">Дедлайн задачи позже дедлайна проекта</p>
                  <p className="text-gray-600 text-sm mt-1">Это может повлиять на планирование проекта. Хотите продолжить?</p>
                </div>
              </div>
            </div>
            <div className="p-6 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
              <button 
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors font-medium"
                onClick={() => setConfirm(false)}
              >
                Изменить дедлайн
              </button>
              <button 
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                onClick={continueWithDeadline}
              >
                Продолжить
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Links modal */}
      {linksModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-96 max-w-[90vw] overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Полезные ссылки</h3>
            </div>
            <div className="p-6 max-h-[60vh] overflow-y-auto">
              <div className="space-y-3">
                {linksModal.map(l => (
                  <div key={l.id} className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                    <div className="text-blue-500 text-lg">🔗</div>
                    <div className="flex-1 min-w-0">
                      {l.name && (
                        <div className="font-medium text-gray-900 truncate">{l.name}</div>
                      )}
                      <a 
                        className="text-blue-600 hover:text-blue-800 text-sm underline block truncate" 
                        href={l.url} 
                        target="_blank" 
                        rel="noreferrer"
                        title={l.url}
                      >
                        {l.url}
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="p-6 bg-gray-50 border-t border-gray-200 flex justify-end">
              <button 
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors font-medium"
                onClick={() => setLinksModal(null)}
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

