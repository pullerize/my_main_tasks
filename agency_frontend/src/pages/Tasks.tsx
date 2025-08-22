import { useEffect, useState } from 'react'
import { API_URL } from '../api'

interface Task {
  id: number
  title: string
  description?: string
  status: string
  deadline?: string
  finished_at?: string
  executor_id?: number
  author_id?: number
  created_at: string
  project?: string
  task_type?: string
  task_format?: string
  high_priority?: boolean
}

interface User {
  id: number
  name: string
  role: string
}

const DESIGNER_TYPES = ['Motion', 'Статика', 'Видео', 'Карусель', 'Другое']
const DESIGNER_FORMATS = ['9:16', '1:1', '4:5', '16:9', 'Другое']
const MANAGER_TYPES = [
  'Публикация',
  'Контент план',
  'Отчет',
  'Съемка',
  'Встреча',
  'Стратегия',
  'Презентация',
  'Админ задачи',
  'Анализ',
  'Брифинг',
  'Сценарий',
  'Другое',
]
const ADMIN_TYPES = [
  'Публикация',
  'Съемки',
  'Стратегия',
  'Отчет',
  'Бухгалтерия',
  'Встреча',
  'Документы',
  'Работа с кадрами',
  'Планерка',
  'Администраторские задачи',
  'Собеседование',
  'Договор',
  'Другое',
]

const ROLE_NAMES: Record<string, string> = {
  designer: 'Дизайнер',
  smm_manager: 'СММ-менеджер',
  head_smm: 'Head of SMM',
  admin: 'Администратор',
  digital: 'Digital',
}

const TYPE_ICONS: Record<string, string> = {
  Motion: '🎞️',
  'Статика': '🖼️',
  'Видео': '🎬',
  'Карусель': '🖼️',
  'Другое': '📌',
  'Публикация': '📝',
  'Контент план': '📅',
  'Отчет': '📊',
  'Съемка': '📹',
  'Встреча': '🤝',
  'Стратегия': '📈',
  'Презентация': '🎤',
  'Админ задачи': '🗂️',
  'Анализ': '🔎',
  'Брифинг': '📋',
  'Сценарий': '📜',
  'Съемки': '🎥',
  'Бухгалтерия': '💰',
  'Документы': '📄',
  'Работа с кадрами': '👥',
  'Планерка': '🗓️',
  'Администраторские задачи': '🛠️',
  'Собеседование': '🧑‍💼',
  'Договор': '✍️',
}

const FORMAT_ICONS: Record<string, string> = {
  '9:16': '📱',
  '1:1': '🔲',
  '4:5': '🖼️',
  '16:9': '🎞️',
  'Другое': '📌',
}

const formatDate = (iso?: string) => {
  if (!iso) return ''
  const normalized = /Z|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z'
  const d = new Date(normalized)
  return d.toLocaleString('ru-RU', {
    timeZone: 'Asia/Tashkent',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const timeLeft = (iso?: string) => {
  if (!iso) return 'Не определено'
  const now = Date.now()
  const target = new Date(iso).getTime()
  const diff = target - now
  if (diff <= 0) return 'Просрочено'
  const hours = Math.floor(diff / 3600000)
  const minutes = Math.floor((diff % 3600000) / 60000)
  const seconds = Math.floor((diff % 60000) / 1000)
  const parts = [] as string[]
  if (hours) parts.push(`${hours}ч`)
  if (minutes || hours) parts.push(`${minutes}м`)
  parts.push(`${seconds}с`)
  return parts.join(' ')
}

const renderDeadline = (t: Task) => {
  if (t.status === 'done') {
    if (t.deadline && t.finished_at && new Date(t.finished_at) > new Date(t.deadline)) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
          🚫 Просрочено
        </span>
      )
    }
    return ''
  }
  
  if (!t.deadline) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
        ⏰ Не установлен
      </span>
    )
  }

  const txt = timeLeft(t.deadline)
  if (txt === 'Просрочено') {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
        🚫 Просрочено
      </span>
    )
  }

  // Определяем цвет на основе оставшегося времени
  const now = Date.now()
  const deadline = new Date(t.deadline).getTime()
  const timeLeftMs = deadline - now
  const hoursLeft = timeLeftMs / 3600000

  if (hoursLeft < 24) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
        ⚡ {txt}
      </span>
    )
  } else if (hoursLeft < 48) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
        ⚠️ {txt}
      </span>
    )
  } else {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
        ✅ {txt}
      </span>
    )
  }
}

function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [showModal, setShowModal] = useState(false)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [executorId, setExecutorId] = useState('')
  const [deadlineDate, setDeadlineDate] = useState('')
  const [deadlineTime, setDeadlineTime] = useState('')
  const [project, setProject] = useState('')
  const [taskType, setTaskType] = useState('')
  const [taskFormat, setTaskFormat] = useState('')
  const [executorRole, setExecutorRole] = useState('')
  const [highPriority, setHighPriority] = useState(false)
  const [users, setUsers] = useState<User[]>([])
  const [projects, setProjects] = useState<{id: number; name: string}[]>([])

  const [filterRole, setFilterRole] = useState('')
  const [filterUser, setFilterUser] = useState('')
  const [filterDate, setFilterDate] = useState('all')
  const [customDate, setCustomDate] = useState('')
  const [filterStatus, setFilterStatus] = useState('active')
  const [filterProject, setFilterProject] = useState('')

  const role = localStorage.getItem('role') || ''
  const userId = Number(localStorage.getItem('userId'))

  useEffect(() => {
    setFilterUser(String(userId))
  }, [userId])

  const allowedUsers = Array.isArray(users) ? users.filter((u) => {
    if (role === 'admin') return true
    if (role === 'designer') return u.role === 'designer'
    if (role === 'smm_manager')
      return u.role === 'designer' || u.role === 'smm_manager'
    if (role === 'head_smm')
      return (
        u.role === 'designer' ||
        u.role === 'smm_manager' ||
        u.role === 'head_smm'
      )
    return false
  }) : []

  const allowedRoles = () => {
    if (role === 'admin') return ['designer', 'smm_manager', 'head_smm', 'admin']
    if (role === 'head_smm') return ['designer', 'smm_manager', 'head_smm']
    if (role === 'smm_manager') return ['designer', 'smm_manager']
    if (role === 'designer') return ['designer']
    return []
  }

  const getExecutorName = (id?: number) => {
    if (!Array.isArray(users) || !id) return ''
    const u = users.find((x) => x.id === id)
    return u ? u.name : ''
  }

  const getUserName = (id?: number) => {
    if (!Array.isArray(users) || !id) return ''
    const u = users.find((x) => x.id === id)
    return u ? u.name : ''
  }
  
  useEffect(() => {
    const token = localStorage.getItem('token')
    
    if (!token) {
      setTasks([])
      setUsers([])
      setProjects([])
      return
    }

    fetch(`${API_URL}/tasks/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (res.ok) return res.json()
        throw new Error('Unauthorized')
      })
      .then((data) => setTasks(Array.isArray(data) ? data : []))
      .catch(() => setTasks([]))
      
    fetch(`${API_URL}/users/`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (res.ok) return res.json()
        throw new Error('Unauthorized')
      })
      .then((data) => setUsers(Array.isArray(data) ? data : []))
      .catch(() => setUsers([]))
      
    fetch(`${API_URL}/projects/`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (res.ok) return res.json()
        throw new Error('Unauthorized')
      })
      .then((data) => setProjects(Array.isArray(data) ? data : []))
      .catch(() => setProjects([]))
  }, [])

  useEffect(() => {
    const id = setInterval(() => {
      setTasks((ts) => [...ts])
    }, 1000)
    return () => clearInterval(id)
  }, [])

  const filteredTasks = Array.isArray(tasks) ? tasks.filter((t) => {
    if (!Array.isArray(users)) return true
    
    const execRole = users.find((u) => u.id === t.executor_id)?.role
    if (role === 'designer' && execRole !== 'designer') return false
    if (
      role === 'smm_manager' &&
      execRole !== 'designer' &&
      execRole !== 'smm_manager'
    )
      return false
    if (
      role === 'head_smm' &&
      execRole !== 'designer' &&
      execRole !== 'smm_manager' &&
      execRole !== 'head_smm'
    )
      return false
    if (filterStatus !== 'all') {
      if (filterStatus === 'active' && t.status === 'done') return false
      if (filterStatus === 'done' && t.status !== 'done') return false
    }
    if (filterRole) {
      const exec = users.find((u) => u.id === t.executor_id)
      if (!exec || exec.role !== filterRole) return false
    }
    if (filterUser && String(t.executor_id) !== filterUser) return false
    if (filterProject && t.project !== filterProject) return false
    if (filterDate !== 'all') {
      const created = new Date(t.created_at)
      const now = new Date()
      const diff = now.getTime() - created.getTime()
      if (filterDate === 'today' && diff > 86400000) return false
      if (filterDate === 'week' && diff > 7 * 86400000) return false
      if (filterDate === 'month' && diff > 30 * 86400000) return false
      if (filterDate === 'custom' && customDate) {
        const sel = new Date(customDate)
        if (
          created.getFullYear() !== sel.getFullYear() ||
          created.getMonth() !== sel.getMonth() ||
          created.getDate() !== sel.getDate()
        )
          return false
      }
    }
    return true
  }) : []

  const sortedTasks = filteredTasks
    .slice()
    .sort((a, b) => {
      const da = a.deadline ? new Date(a.deadline).getTime() - Date.now() : Infinity
      const db = b.deadline ? new Date(b.deadline).getTime() - Date.now() : Infinity
      return da - db
    })

  const validateDeadline = () => {
    const execRole = executorId && Array.isArray(users) ? users.find(u => u.id === Number(executorId))?.role : role
    if (execRole === 'designer') {
      if (!deadlineDate || !deadlineTime) return true
      const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Tashkent' }))
      if (now.getHours() >= 17) {
        const dl = new Date(new Date(`${deadlineDate}T${deadlineTime}`).toLocaleString('en-US', { timeZone: 'Asia/Tashkent' }))
        const next = new Date(now)
        next.setDate(now.getDate() + 1)
        next.setHours(9,0,0,0)
        if (dl < next) return false
      }
    }
    return true
  }

  const createTask = async () => {
    if (!validateDeadline()) {
      alert('Нельзя ставить задачу дизайнеру с таким дедлайном после 17:00')
      return
    }
    let deadlineStr: string | undefined
    if (deadlineDate && deadlineTime.length === 5) {
      deadlineStr = `${deadlineDate}T${deadlineTime}`
    } else if (!deadlineDate && deadlineTime.length === 5) {
      const now = new Date(
        new Date().toLocaleString('en-US', { timeZone: 'Asia/Tashkent' })
      )
      const [hh, mm] = deadlineTime.split(':').map(Number)
      const dl = new Date(now)
      dl.setHours(hh, mm, 0, 0)
      if (dl <= now) dl.setDate(dl.getDate() + 1)
      const y = dl.getFullYear()
      const m = String(dl.getMonth() + 1).padStart(2, '0')
      const d = String(dl.getDate()).padStart(2, '0')
      deadlineStr = `${y}-${m}-${d}T${deadlineTime}`
    }
    const payload = {
      title,
      description,
      project: project || undefined,
      task_type: taskType || undefined,
      task_format: taskFormat || undefined,
      executor_id: executorId ? Number(executorId) : undefined,
      deadline: deadlineStr,
      
    }
    const token = localStorage.getItem('token')
    await fetch(`${API_URL}/tasks/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    })
    setShowModal(false)
    setSelectedTask(null)
    setIsEditing(false)
    setIsEditing(false)
    setTitle('')
    setDescription('')
    setProject('')
    setTaskType('')
    setTaskFormat('')
    setExecutorId('')
    setExecutorRole('')
    setDeadlineDate('')
    setDeadlineTime('')
    setHighPriority(false)
    const res = await fetch(`${API_URL}/tasks/`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
    const data = await res.json()
    setTasks(Array.isArray(data) ? data : [])
  }

  const saveTask = async () => {
    if (!selectedTask) return
    if (!validateDeadline()) {
      alert('Нельзя ставить задачу дизайнеру с таким дедлайном после 17:00')
      return
    }
    let deadlineStr: string | undefined
    if (deadlineDate && deadlineTime.length === 5) {
      deadlineStr = `${deadlineDate}T${deadlineTime}`
    } else if (!deadlineDate && deadlineTime.length === 5) {
      const now = new Date(
        new Date().toLocaleString('en-US', { timeZone: 'Asia/Tashkent' })
      )
      const [hh, mm] = deadlineTime.split(':').map(Number)
      const dl = new Date(now)
      dl.setHours(hh, mm, 0, 0)
      if (dl <= now) dl.setDate(dl.getDate() + 1)
      const y = dl.getFullYear()
      const m = String(dl.getMonth() + 1).padStart(2, '0')
      const d = String(dl.getDate()).padStart(2, '0')
      deadlineStr = `${y}-${m}-${d}T${deadlineTime}`
    }
    const payload = {
      title,
      description,
      project: project || undefined,
      task_type: taskType || undefined,
      task_format: taskFormat || undefined,
      executor_id: executorId ? Number(executorId) : undefined,
      deadline: deadlineStr,
      
    }
    const token = localStorage.getItem('token')
    await fetch(`${API_URL}/tasks/${selectedTask.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    })
    setShowModal(false)
    setSelectedTask(null)
    setTitle('')
    setDescription('')
    setProject('')
    setTaskType('')
    setTaskFormat('')
    setExecutorId('')
    setExecutorRole('')
    setDeadlineDate('')
    setDeadlineTime('')
    setHighPriority(false)
    const res = await fetch(`${API_URL}/tasks/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    const data = await res.json()
    setTasks(Array.isArray(data) ? data : [])
  }

  const deleteTask = async (id: number) => {
    const token = localStorage.getItem('token')
    await fetch(`${API_URL}/tasks/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    setTasks(Array.isArray(tasks) ? tasks.filter((t) => t.id !== id) : [])
  }

  const toggleStatus = async (id: number, status: string) => {
    const token = localStorage.getItem('token')
    const res = await fetch(`${API_URL}/tasks/${id}/status?status=${status}`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      const updated = await res.json()
      setTasks(Array.isArray(tasks) ? tasks.map((t) => (t.id === id ? updated : t)) : [])
    }
  }

  return (
    <div className="w-full overflow-hidden bg-gray-50 min-h-screen">
      <div className="bg-white shadow-sm border-b p-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Управление задачами</h1>
            <p className="text-gray-600 mt-1">Отслеживайте прогресс и управляйте задачами команды</p>
          </div>
          <button
            className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white px-6 py-3 rounded-lg font-medium shadow-lg transform hover:scale-105 transition-all duration-200 flex items-center space-x-2"
            onClick={() => {
              setSelectedTask(null)
              setIsEditing(true)
              setTitle('')
              setDescription('')
              setProject('')
              setTaskType('')
              setTaskFormat('')
              setExecutorId('')
              setExecutorRole('')
              setHighPriority(false)
              setDeadlineDate('')
              setDeadlineTime('')
              setShowModal(true)
            }}
          >
            <span>+</span>
            <span>Создать задачу</span>
          </button>
        </div>
      </div>
      <div className="bg-white p-6 shadow-sm border-b">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex flex-wrap gap-3">
            <select
              className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              value={filterProject}
              onChange={(e) => setFilterProject(e.target.value)}
            >
              <option value="">Все проекты</option>
              {Array.isArray(projects) && projects.map(p => (
                <option key={p.id} value={p.name}>{p.name}</option>
              ))}
            </select>
            {role !== 'designer' && (
              <select
                className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                value={filterRole}
                onChange={(e) => setFilterRole(e.target.value)}
              >
                <option value="">Все роли</option>
                <option value="designer">{ROLE_NAMES.designer}</option>
                <option value="smm_manager">{ROLE_NAMES.smm_manager}</option>
                <option value="head_smm">{ROLE_NAMES.head_smm}</option>
                {role === 'admin' && (
                  <option value="admin">{ROLE_NAMES.admin}</option>
                )}
              </select>
            )}
            <select
              className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              value={filterUser}
              onChange={(e) => setFilterUser(e.target.value)}
            >
              <option value="">Все сотрудники</option>
              {Array.isArray(users) && users
                .filter((u) =>
                  role === 'admin'
                    ? filterRole
                      ? u.role === filterRole
                      : true
                    : u.role !== 'admin' && (filterRole ? u.role === filterRole : true)
                )
                .map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name}
                  </option>
                ))}
            </select>
            <select
              className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              value={filterDate}
              onChange={(e) => setFilterDate(e.target.value)}
            >
              <option value="all">За все время</option>
              <option value="today">За сегодня</option>
              <option value="week">За неделю</option>
              <option value="month">За месяц</option>
              <option value="custom">Выбрать дату</option>
            </select>
            {filterDate === 'custom' && (
              <input
                type="date"
                className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                value={customDate}
                onChange={(e) => setCustomDate(e.target.value)}
              />
            )}
            <select
              className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="active">Активные</option>
              <option value="done">Завершенные</option>
              <option value="all">Все</option>
            </select>
          </div>
          <div className="ml-auto bg-gradient-to-r from-gray-100 to-gray-200 px-4 py-2 rounded-full">
            <span className="text-sm font-medium text-gray-700">Всего: {sortedTasks.length}</span>
          </div>
        </div>
      </div>

      <div className="p-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[200px]">
                    Название задачи
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[120px]">
                    Проект
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[140px]">
                    Тип задачи
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[120px]">
                    Автор
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[120px]">
                    Исполнитель
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[140px]">
                    Создана
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
                {sortedTasks.map((t) => (
                  <tr
                    key={t.id}
                    className="hover:bg-gray-50 transition-colors duration-150"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-3">
                        <div className="flex items-center space-x-2">
                          <div className={`w-3 h-3 rounded-full ${
                            t.status === 'done' ? 'bg-green-500' : 
                            t.high_priority ? 'bg-red-500' : 'bg-yellow-500'
                          }`}></div>
                          {t.high_priority && t.status !== 'done' && (
                            <span className="text-red-600 text-xs font-medium">🔥 Приоритет</span>
                          )}
                        </div>
                        <div
                          className="text-sm font-medium text-gray-900 cursor-pointer hover:text-blue-600 transition-colors"
                          onClick={() => {
                            setSelectedTask(t)
                            setIsEditing(false)
                            setShowModal(true)
                            setTitle(t.title)
                            setDescription(t.description || '')
                            setProject(t.project || '')
                            setTaskType(t.task_type || '')
                            setTaskFormat(t.task_format || '')
                            setExecutorId(t.executor_id ? String(t.executor_id) : '')
                            setExecutorRole(Array.isArray(users) ? (users.find(u => u.id === t.executor_id)?.role || '') : '')
                            if (t.deadline) {
                              const d = new Date(t.deadline)
                              setDeadlineDate(d.toISOString().slice(0,10))
                              setDeadlineTime(d.toISOString().slice(11,16))
                            } else {
                              setDeadlineDate('')
                              setDeadlineTime('')
                            }
                          }}
                        >
                          <div className="truncate max-w-[180px]">{t.title}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">
                        <div className="truncate max-w-[100px]">{t.project || '-'}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg">{TYPE_ICONS[t.task_type || ''] || '📋'}</span>
                        <span className="text-sm text-gray-900 truncate max-w-[100px]">{t.task_type || '-'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">
                        <div className="truncate max-w-[100px]">{getUserName(t.author_id) || '-'}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">
                        <div className="truncate max-w-[100px]">{getExecutorName(t.executor_id) || '-'}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">
                        <div className="truncate max-w-[120px]">{formatDate(t.created_at)}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm">
                        {t.status === 'done' ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            ✓ Завершено
                          </span>
                        ) : (
                          renderDeadline(t)
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2 justify-start flex-wrap">
                        {t.status !== 'done' ? (
                          <>
                            {(t.executor_id === userId || t.author_id === userId) && (
                              <button
                                className="inline-flex items-center px-3 py-1.5 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                                onClick={() => deleteTask(t.id)}
                              >
                                Удалить
                              </button>
                            )}
                            {(t.executor_id === userId || t.author_id === userId) && (
                              <button
                                className="inline-flex items-center px-3 py-1.5 border border-green-300 text-xs font-medium rounded-md text-green-700 bg-green-50 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
                                onClick={() => toggleStatus(t.id, 'done')}
                              >
                                Завершить
                              </button>
                            )}
                          </>
                        ) : (
                          (t.executor_id === userId || t.author_id === userId) && (
                            <button
                              className="inline-flex items-center px-3 py-1.5 border border-yellow-300 text-xs font-medium rounded-md text-yellow-700 bg-yellow-50 hover:bg-yellow-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 transition-colors"
                              onClick={() => toggleStatus(t.id, 'in_progress')}
                            >
                              Возобновить
                            </button>
                          )
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {sortedTasks.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">📋</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Нет задач</h3>
              <p className="text-gray-500">Пока что здесь нет ни одной задачи. Создайте первую задачу!</p>
            </div>
          )}
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-white p-6 rounded-lg w-[40rem] max-h-[90vh] overflow-y-auto shadow-lg space-y-4">
            <h2 className="text-xl mb-2">
              {isEditing ? (selectedTask ? 'Редактировать задачу' : 'Новая задача') : 'Информация о задаче'}
            </h2>
            <input
              className="border p-2 w-full mb-2"
              placeholder="Заголовок"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={!isEditing}
            />
            <textarea
              className="border p-2 w-full mb-2"
              placeholder="Описание"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={!isEditing}
            />
            {isEditing ? (
              <>
                <select
                  className="border p-2 w-full mb-2"
                  value={executorRole}
                  onChange={(e) => {
                    setExecutorRole(e.target.value)
                    setExecutorId('')
                  }}
                >
                  <option value="">Выберите роль</option>
                  {allowedRoles().map((r) => (
                    <option key={r} value={r}>
                      {ROLE_NAMES[r]}
                    </option>
                  ))}
                </select>
                <select
                  className="border p-2 w-full mb-2"
                  value={executorId}
                  onChange={(e) => setExecutorId(e.target.value)}
                  disabled={!executorRole}
                >
                  <option value="" disabled>
                    Выберите исполнителя
                  </option>
                  {allowedUsers
                    .filter((u) => (executorRole ? u.role === executorRole : true))
                    .map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name}
                      </option>
                    ))}
                </select>
              </>
            ) : null}
            {(executorId || role === 'designer') && (
              isEditing ? (
                <>
                  <select
                    className="border p-2 w-full mb-2"
                    value={project}
                    onChange={(e) => setProject(e.target.value)}
                  >
                    <option value="">Проект не выбран</option>
                    {Array.isArray(projects) && projects.map(p => (
                      <option key={p.id} value={p.name}>{p.name}</option>
                    ))}
                  </select>
                  <select
                    className="border p-2 w-full mb-2"
                    value={taskType}
                    onChange={(e) => setTaskType(e.target.value)}
                  >
                    <option value="">Тип задачи не выбран</option>
                    {(
                      (Array.isArray(users) && users.find((u) => u.id === Number(executorId))?.role || role) === 'designer'
                        ? DESIGNER_TYPES
                        : (Array.isArray(users) && users.find((u) => u.id === Number(executorId))?.role || role) === 'admin'
                        ? ADMIN_TYPES
                        : MANAGER_TYPES
                    ).map((t) => (
                      <option key={t} value={t}>
                        {TYPE_ICONS[t]} {t}
                      </option>
                    ))}
                  </select>
                  {(Array.isArray(users) && users.find((u) => u.id === Number(executorId))?.role || role) === 'designer' && (
                    <select
                      className="border p-2 w-full mb-2"
                      value={taskFormat}
                      onChange={(e) => setTaskFormat(e.target.value)}
                    >
                      <option value="">Формат не выбран</option>
                      {DESIGNER_FORMATS.map((f) => (
                        <option key={f} value={f}>
                          {FORMAT_ICONS[f]} {f}
                        </option>
                      ))}
                    </select>
                  )}
                </>
              ) : (
                <div className="space-y-1 mb-2">
                  <div>Исполнитель: {getExecutorName(selectedTask?.executor_id)}</div>
                  {project && <div>Проект: {project}</div>}
                  {taskType && (
                    <div>
                      Тип задачи: {TYPE_ICONS[taskType]} {taskType}
                    </div>
                  )}
                  {taskFormat && (
                    <div>
                      Формат: {FORMAT_ICONS[taskFormat]} {taskFormat}
                    </div>
                  )}
                  <div>Время постановки задачи: {formatDate(selectedTask?.created_at)}</div>
                  {selectedTask?.finished_at && (
                    <div>Время завершения задачи: {formatDate(selectedTask?.finished_at)}</div>
                  )}
                  <div>Кто поставил задачу: {getUserName(selectedTask?.author_id)}</div>
                </div>
              )
            )}
            <div className="flex gap-2 mb-4">
              <input
                type="date"
                className="border p-2 flex-1"
                value={deadlineDate}
                onChange={(e) => setDeadlineDate(e.target.value)}
                disabled={!isEditing}
              />
              <input
                type="text"
                className="border p-2 w-24"
                placeholder="HH:MM"
                value={deadlineTime}
                onChange={(e) => {
                  let v = e.target.value.replace(/\D/g, '').slice(0, 4)
                  if (v.length >= 3) v = v.slice(0, 2) + ':' + v.slice(2)
                  setDeadlineTime(v)
                }}
                disabled={!isEditing}
              />
            </div>
            <div className="flex justify-end">
              <button
                className="mr-2 px-4 py-1 border rounded"
                onClick={() => { setShowModal(false); setSelectedTask(null); setIsEditing(false); }}
              >
                Отмена
              </button>
              {!isEditing && selectedTask && (
                <button
                  className="mr-2 px-4 py-1 border rounded"
                  onClick={() => setIsEditing(true)}
                >
                  Редактировать
                </button>
              )}
              {isEditing && (
                <button
                  className="bg-blue-500 text-white px-4 py-1 rounded"
                  onClick={selectedTask ? saveTask : createTask}
                >
                  Сохранить
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Tasks
