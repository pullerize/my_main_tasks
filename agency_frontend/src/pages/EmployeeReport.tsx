import { useEffect, useState } from 'react'
import { API_URL } from '../api'
import { formatDateTimeUTC5, formatDeadlineUTC5 } from '../utils/dateUtils'

interface User {
  id: number
  name: string
  role: string
  birth_date?: string | null
  contract_path?: string | null
}

interface Project { id: number; name: string }
interface Task {
  id: number
  title: string
  description?: string
  project?: string
  status: string
  created_at: string
  deadline?: string | null
  executor_id?: number
  author_id?: number
  task_type?: string
  task_format?: string
  finished_at?: string | null
  high_priority?: boolean
  source?: 'tasks' | 'digital' // Для различения источника задачи
}

interface DigitalTask {
  id: number
  project_id: number
  project: string
  service_id: number
  service: string
  executor_id: number
  executor: string
  created_at: string
  deadline?: string
  monthly: boolean
  status: string
  high_priority?: boolean
}

const ROLE_NAMES: Record<string, string> = {
  designer: 'Дизайнер',
  smm_manager: 'СММ-менеджер',
  admin: 'Администратор',
}

function firstDay(dt: Date) {
  return new Date(dt.getFullYear(), dt.getMonth(), 1)
}

function lastDay(dt: Date) {
  return new Date(dt.getFullYear(), dt.getMonth() + 1, 0)
}

function formatDateTime(d?: string | null) {
  if (!d) return ''
  return formatDateTimeUTC5(d)
}

function timeLeft(d: string) {
  const target = new Date(d).getTime()
  const now = Date.now()
  const diff = target - now
  if (diff <= 0) return 'Просрочено'
  const hours = Math.floor(diff / 3600000)
  const minutes = Math.floor((diff % 3600000) / 60000)
  const seconds = Math.floor((diff % 60000) / 1000)
  const parts: string[] = []
  if (hours) parts.push(`${hours}ч`)
  if (minutes || hours) parts.push(`${minutes}м`)
  parts.push(`${seconds}с`)
  return parts.join(' ')
}

function renderDeadline(t: Task) {
  if (!t.deadline) return ''
  const formatted = formatDeadlineUTC5(t.deadline) // Используем formatDeadlineUTC5 для дедлайнов
  if (t.status !== 'done') {
    return `${formatted} (${timeLeft(t.deadline)})`
  }
  return formatted
}

function EmployeeReport() {
  const token = localStorage.getItem('token')
  const [users, setUsers] = useState<User[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [modalTask, setModalTask] = useState<Task | null>(null)

  const [userId, setUserId] = useState('')
  const [project, setProject] = useState('')

  const now = new Date()
  const [period, setPeriod] = useState<'day' | 'week' | 'month' | 'custom'>('custom')
  // Set default date range to include all tasks (2024-2025)
  const [startDate, setStartDate] = useState('2024-01-01')
  const [endDate, setEndDate] = useState('2025-12-31')
  const [status, setStatus] = useState<'all' | 'in_progress' | 'done'>('all')
  const [taskSource, setTaskSource] = useState<'all' | 'tasks' | 'digital' | 'smm'>('all')

  const loadData = async () => {
    const headers = { Authorization: `Bearer ${token}` }
    
    try {
      // Загружаем пользователей и проекты
      const [u, p] = await Promise.all([
        fetch(`${API_URL}/users/`, { headers }).then(r => r.json()),
        fetch(`${API_URL}/projects/`, { headers }).then(r => r.json()),
      ])
      setUsers(u)
      setProjects(p)
      
      // Загружаем ВСЕ задачи для отчета (включая задачи без исполнителя)
      const tasksRes = await fetch(`${API_URL}/tasks/all`, { headers })
      const regularTasks = tasksRes.ok ? await tasksRes.json() : []
      
      // Загружаем Digital проекты
      const digitalProjectsRes = await fetch(`${API_URL}/digital/projects`, { headers })
      const digitalProjects = digitalProjectsRes.ok ? await digitalProjectsRes.json() : []
      
      // Загружаем задачи из каждого Digital проекта
      const digitalTasksPromises = digitalProjects.map(async (project: any) => {
        try {
          const tasksRes = await fetch(`${API_URL}/digital/projects/${project.id}/tasks`, { headers })
          if (tasksRes.ok) {
            const projectTasks = await tasksRes.json()
            return projectTasks.map((task: any) => ({
              id: task.id + 2000000, // Добавляем большое число чтобы избежать конфликта ID
              title: task.title || `${project.project_name} - ${task.task_name || 'Задача'}`,
              description: task.description,
              project: project.project_name,
              status: task.status === 'completed' ? 'done' : 'in_progress',
              created_at: task.created_at || project.created_at,
              deadline: task.deadline,
              executor_id: project.executor_id, // Используем executor_id из проекта
              author_id: task.author_id,
              task_type: 'Digital',
              task_format: project.service_name,
              finished_at: task.finished_at,
              high_priority: task.high_priority || project.high_priority,
              source: 'digital' as const
            }))
          }
          return []
        } catch (error) {
          console.error(`Failed to load tasks for digital project ${project.id}:`, error)
          return []
        }
      })
      
      const digitalTasksArrays = await Promise.all(digitalTasksPromises)
      const digitalTasks: Task[] = digitalTasksArrays.flat()
      
      // Помечаем обычные задачи
      const markedRegularTasks = regularTasks.map((t: any) => ({
        ...t,
        source: 'tasks' as const
      }))
      
      // Объединяем все задачи
      setTasks([...markedRegularTasks, ...digitalTasks])
    } catch (error) {
      console.error('Failed to load data:', error)
      setUsers([])
      setProjects([])
      setTasks([])
    }
  }

  useEffect(() => { loadData() }, [])
  useEffect(() => {
    const id = setInterval(() => setTasks(ts => [...ts]), 1000)
    return () => clearInterval(id)
  }, [])

  const selectedUser = users.find(u => String(u.id) === userId)

  const handlePeriodChange = (p: 'day'|'week'|'month'|'custom') => {
    setPeriod(p)
    const base = new Date()
    if (p === 'day') {
      const iso = base.toISOString().slice(0,10)
      setStartDate(iso)
      setEndDate(iso)
    } else if (p === 'week') {
      const day = base.getDay()
      const diff = base.getDate() - (day === 0 ? 6 : day - 1)
      const monday = new Date(base.setDate(diff))
      const sunday = new Date(monday)
      sunday.setDate(monday.getDate() + 6)
      setStartDate(monday.toISOString().slice(0,10))
      setEndDate(sunday.toISOString().slice(0,10))
    } else if (p === 'month') {
      setStartDate(firstDay(base).toISOString().slice(0,10))
      setEndDate(lastDay(base).toISOString().slice(0,10))
    }
  }

  // Pre-filter tasks WITHOUT status filter to get correct counts
  const baseFilteredTasks = tasks.filter(t => {
    // Фильтр по пользователю: если выбран конкретный пользователь, показываем только его задачи
    if (userId && String(t.executor_id || '') !== userId) return false
    if (project && t.project !== project) return false
    const created = new Date(t.created_at).getTime()
    const start = new Date(startDate).getTime()
    const end = new Date(endDate).getTime() + 86400000 - 1
    if (created < start || created > end) return false
    
    // Фильтр по источнику задач
    if (taskSource === 'digital' && t.source !== 'digital') return false
    if (taskSource === 'smm' && !(t.source === 'tasks' && t.task_type?.toLowerCase().includes('smm'))) return false
    if (taskSource === 'tasks' && (t.source === 'digital' || t.task_type?.toLowerCase().includes('smm'))) return false
    
    return true
  })

  // Apply status filter for display
  const filteredTasks = baseFilteredTasks.filter(t => {
    if (status === 'in_progress' && (t.status === 'done' || t.status === 'cancelled')) return false
    if (status === 'done' && t.status !== 'done') return false
    return true
  }).sort((a,b)=>{
    const sa = a.status === 'done' ? 1 : 0
    const sb = b.status === 'done' ? 1 : 0
    if (sa !== sb) return sa - sb
    const da = new Date(a.deadline || a.created_at).getTime()
    const db = new Date(b.deadline || b.created_at).getTime()
    return da - db
  })

  // Calculate counts from base filtered tasks
  const allTasksCount = baseFilteredTasks.length
  const doneTasksCount = baseFilteredTasks.filter(t => t.status === 'done').length
  const inProgressTasksCount = baseFilteredTasks.filter(t => t.status !== 'done').length

  const getUserName = (id?: number) => {
    const u = users.find(x => x.id === id)
    return u ? u.name : ''
  }

  const uploadContract = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!userId || !e.target.files?.length) return
    const file = e.target.files[0]
    const fd = new FormData()
    fd.append('file', file)
    await fetch(`${API_URL}/users/${userId}/contract`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    })
    loadData()
  }

  const downloadContract = async () => {
    if (!selectedUser) return
    const res = await fetch(`${API_URL}/users/${selectedUser.id}/contract`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const name = selectedUser.contract_path?.split('/').pop() || 'contract'
      a.download = name
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  const deleteContract = async () => {
    if (!userId) return
    await fetch(`${API_URL}/users/${userId}/contract`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    loadData()
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="px-6 py-4">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <span className="text-3xl">👥</span>
            Отчет по сотрудникам
          </h1>
          <p className="text-gray-600 mt-1">Анализ выполненных задач и продуктивности</p>
        </div>
      </div>

      {/* Filters */}
      <div className="px-6 py-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <span>🔍</span>
            Фильтры
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                📅 Период
              </label>
              <select 
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                value={period} 
                onChange={e=>handlePeriodChange(e.target.value as any)}
              >
                <option value="day">За день</option>
                <option value="week">За неделю</option>
                <option value="month">За месяц</option>
                <option value="custom">Кастомный период</option>
              </select>
            </div>
            
            {period === 'custom' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    📆 Начало периода
                  </label>
                  <input 
                    type="date" 
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    value={startDate} 
                    onChange={e=>setStartDate(e.target.value)} 
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    📆 Конец периода
                  </label>
                  <input 
                    type="date" 
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                    value={endDate} 
                    onChange={e=>setEndDate(e.target.value)} 
                  />
                </div>
              </>
            )}
            
            <div className={period !== 'custom' ? 'lg:col-span-2' : ''}>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                👤 Сотрудник
              </label>
              <select 
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                value={userId} 
                onChange={e=>setUserId(e.target.value)}
              >
                <option value="">Все сотрудники</option>
                {users.map(u => (
                  <option key={u.id} value={u.id}>
                    {u.name} ({ROLE_NAMES[u.role] || u.role})
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                📁 Проект
              </label>
              <select 
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                value={project} 
                onChange={e=>setProject(e.target.value)}
              >
                <option value="">Все проекты</option>
                {projects.map(p => (
                  <option key={p.id} value={p.name}>{p.name}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                📋 Тип задач
              </label>
              <select 
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                value={taskSource} 
                onChange={e=>setTaskSource(e.target.value as any)}
              >
                <option value="all">Все типы</option>
                <option value="tasks">📋 Общие задачи</option>
                <option value="smm">📱 SMM задачи</option>
                <option value="digital">💻 Digital задачи</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <div className="px-6 pb-6">
          {/* Employee Info Cards */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <span>📊</span>
              {selectedUser ? 'Информация о сотруднике' : 'Общая информация'}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-blue-600">{selectedUser ? 'Имя сотрудника' : 'Отчет'}</div>
                    <div className="text-xl font-bold text-gray-900 mt-1">{selectedUser ? selectedUser.name : 'Все сотрудники'}</div>
                  </div>
                  <span className="text-3xl">👤</span>
                </div>
              </div>
              
              <div className="bg-gradient-to-r from-purple-50 to-purple-100 rounded-lg p-4 border border-purple-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-purple-600">Должность</div>
                    <div className="text-xl font-bold text-gray-900 mt-1">{selectedUser ? (ROLE_NAMES[selectedUser.role] || selectedUser.role) : 'Все роли'}</div>
                  </div>
                  <span className="text-3xl">💼</span>
                </div>
              </div>
              
              {selectedUser && (
                <div className="bg-gradient-to-r from-green-50 to-green-100 rounded-lg p-4 border border-green-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-green-600">Договор</div>
                      <div className="mt-1">
                        {selectedUser.contract_path ? (
                        <div className="flex items-center gap-2">
                          <button 
                            onClick={downloadContract} 
                            className="text-green-700 hover:text-green-900 font-medium transition-colors"
                          >
                            📥 Скачать
                          </button>
                          <button 
                            onClick={deleteContract} 
                            className="text-red-600 hover:text-red-800 font-medium transition-colors"
                          >
                            🗑️
                          </button>
                        </div>
                      ) : (
                        <label className="inline-flex items-center gap-1 px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded-lg cursor-pointer transition-colors">
                          📤 Загрузить
                          <input type="file" className="hidden" onChange={uploadContract} />
                        </label>
                      )}
                    </div>
                  </div>
                    <span className="text-3xl">📄</span>
                  </div>
                </div>
              )}
              
              <div className="bg-gradient-to-r from-orange-50 to-orange-100 rounded-lg p-4 border border-orange-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-orange-600">Количество задач</div>
                    <div className="text-3xl font-bold text-gray-900 mt-1">{allTasksCount}</div>
                  </div>
                  <span className="text-3xl">📋</span>
                </div>
              </div>
            </div>
            
            {/* Additional Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-gray-600">Выполнено задач</div>
                    <div className="text-2xl font-bold text-green-600 mt-1">
                      {doneTasksCount}
                    </div>
                  </div>
                  <span className="text-2xl">✅</span>
                </div>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-gray-600">В работе</div>
                    <div className="text-2xl font-bold text-blue-600 mt-1">
                      {inProgressTasksCount}
                    </div>
                  </div>
                  <span className="text-2xl">⏳</span>
                </div>
              </div>
            </div>
          </div>

          {/* Tasks Table */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <span>📝</span>
                  Список задач
                </h2>
                <div className="flex gap-2">
                  <button
                    className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                      status === 'all' 
                        ? 'bg-blue-600 text-white shadow-lg transform scale-105' 
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    onClick={() => setStatus('all')}
                  >
                    📊 Все задачи ({allTasksCount})
                  </button>
                  <button
                    className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                      status === 'in_progress' 
                        ? 'bg-blue-600 text-white shadow-lg transform scale-105' 
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    onClick={() => setStatus('in_progress')}
                  >
                    ⏳ В работе ({inProgressTasksCount})
                  </button>
                  <button
                    className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                      status === 'done' 
                        ? 'bg-green-600 text-white shadow-lg transform scale-105' 
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    onClick={() => setStatus('done')}
                  >
                    ✅ Завершенные ({doneTasksCount})
                  </button>
                </div>
              </div>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Название задачи
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Проект
                    </th>
                    <th className="px-6 py-4 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Статус
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Дата создания
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                      Дедлайн
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredTasks.length > 0 ? (
                    filteredTasks.map(t => (
                      <tr 
                        key={t.id} 
                        className="hover:bg-gray-50 transition-colors duration-150 cursor-pointer"
                        onClick={() => setModalTask(t)}
                      >
                        <td className="px-6 py-4 whitespace-normal">
                          <div className="flex items-center">
                            {t.high_priority && <span className="mr-2 text-red-500">🔴</span>}
                            <div>
                              <div className="text-sm font-medium text-gray-900">{t.title}</div>
                              <div className="flex items-center gap-2 mt-1">
                                {t.task_type && (
                                  <span className="text-xs text-gray-500">Тип: {t.task_type}</span>
                                )}
                                {t.source === 'digital' && (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                    💻 Digital
                                  </span>
                                )}
                                {t.source === 'tasks' && t.task_type?.toLowerCase().includes('smm') && (
                                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-pink-100 text-pink-800">
                                    📱 SMM
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {t.project || 'Без проекта'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          {t.status === 'done' ? (
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              ✅ Завершено
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                              ⏳ В работе
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900">
                          {formatDateTime(t.created_at)}
                        </td>
                        <td className="px-6 py-4">
                          {t.deadline ? (
                            <div className={`text-sm ${
                              t.status !== 'done' && new Date(t.deadline) < new Date() 
                                ? 'text-red-600 font-medium' 
                                : 'text-gray-900'
                            }`}>
                              {renderDeadline(t)}
                            </div>
                          ) : (
                            <span className="text-gray-400 text-sm">Не установлен</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="px-6 py-12 text-center">
                        <div className="text-gray-400">
                          <span className="text-5xl">📭</span>
                          <p className="mt-2 text-lg">Нет задач для отображения</p>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      {modalTask && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl w-[40rem] max-h-[90vh] overflow-hidden">
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 relative">
              <button 
                className="absolute right-4 top-4 text-white hover:text-gray-200 transition-colors"
                onClick={() => setModalTask(null)}
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <span>📋</span>
                Информация о задаче
              </h2>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
              <div className="space-y-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                    <span>📝</span>
                    Основная информация
                  </h3>
                  <div className="space-y-2">
                    <div className="flex items-start">
                      <span className="text-gray-600 font-medium min-w-[120px]">Название:</span>
                      <span className="text-gray-900 font-semibold">{modalTask.title}</span>
                    </div>
                    {modalTask.description && (
                      <div className="flex items-start">
                        <span className="text-gray-600 font-medium min-w-[120px]">Описание:</span>
                        <span className="text-gray-900">{modalTask.description}</span>
                      </div>
                    )}
                    {modalTask.project && (
                      <div className="flex items-start">
                        <span className="text-gray-600 font-medium min-w-[120px]">Проект:</span>
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {modalTask.project}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                    <span>📊</span>
                    Статус и временные рамки
                  </h3>
                  <div className="space-y-2">
                    <div className="flex items-start">
                      <span className="text-gray-600 font-medium min-w-[120px]">Статус:</span>
                      {modalTask.status === 'done' ? (
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          ✅ Завершено
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                          ⏳ В работе
                        </span>
                      )}
                    </div>
                    <div className="flex items-start">
                      <span className="text-gray-600 font-medium min-w-[120px]">Создано:</span>
                      <span className="text-gray-900">{formatDateTime(modalTask.created_at)}</span>
                    </div>
                    {modalTask.deadline && (
                      <div className="flex items-start">
                        <span className="text-gray-600 font-medium min-w-[120px]">Дедлайн:</span>
                        <span className="text-gray-900">{renderDeadline(modalTask)}</span>
                      </div>
                    )}
                    {modalTask.finished_at && (
                      <div className="flex items-start">
                        <span className="text-gray-600 font-medium min-w-[120px]">Завершено:</span>
                        <span className="text-gray-900">{formatDateTime(modalTask.finished_at)}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                    <span>👥</span>
                    Участники
                  </h3>
                  <div className="space-y-2">
                    <div className="flex items-start">
                      <span className="text-gray-600 font-medium min-w-[120px]">Исполнитель:</span>
                      <span className="text-gray-900">{getUserName(modalTask.executor_id) || 'Не назначен'}</span>
                    </div>
                    <div className="flex items-start">
                      <span className="text-gray-600 font-medium min-w-[120px]">Автор:</span>
                      <span className="text-gray-900">{getUserName(modalTask.author_id) || 'Неизвестно'}</span>
                    </div>
                  </div>
                </div>

                {(modalTask.task_type || modalTask.task_format || modalTask.high_priority) && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                      <span>🏷️</span>
                      Дополнительная информация
                    </h3>
                    <div className="space-y-2">
                      {modalTask.task_type && (
                        <div className="flex items-start">
                          <span className="text-gray-600 font-medium min-w-[120px]">Тип задачи:</span>
                          <span className="text-gray-900">{modalTask.task_type}</span>
                        </div>
                      )}
                      {modalTask.task_format && (
                        <div className="flex items-start">
                          <span className="text-gray-600 font-medium min-w-[120px]">Формат:</span>
                          <span className="text-gray-900">{modalTask.task_format}</span>
                        </div>
                      )}
                      {modalTask.high_priority && (
                        <div className="flex items-start">
                          <span className="text-gray-600 font-medium min-w-[120px]">Приоритет:</span>
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            🔴 Высокий
                          </span>
                        </div>
                      )}
                      {modalTask.source && (
                        <div className="flex items-start">
                          <span className="text-gray-600 font-medium min-w-[120px]">Источник:</span>
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            {modalTask.source === 'digital' ? '💻 Digital' : '📋 Общие задачи'}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default EmployeeReport