import { useEffect, useState } from 'react'
import { API_URL } from '../api'
import { formatDateShortUTC5, getCurrentTimeUTC5, formatDateUTC5, formatDeadline, formatDateAsIs } from '../utils/dateUtils'
import { usePersistedState } from '../utils/filterStorage'
import { isAdmin } from '../utils/roleUtils'

interface Task {
  id: number
  title: string
  description?: string
  status: string
  deadline?: string
  accepted_at?: string
  finished_at?: string
  resume_count?: number
  executor_id?: number
  author_id?: number
  created_at: string
  project?: string
  task_type?: string
  task_format?: string
  high_priority?: boolean
  is_recurring?: boolean
  recurrence_type?: string
  recurrence_time?: string
  recurrence_days?: string
  next_run_at?: string
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
const DIGITAL_TYPES = [
  'Настройка рекламы',
  'Анализ эффективности',
  'A/B тестирование', 
  'Настройка аналитики',
  'Оптимизация конверсий',
  'Email-маркетинг',
  'Контекстная реклама',
  'Таргетированная реклама',
  'SEO оптимизация',
  'Веб-аналитика',
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
  'Настройка рекламы': '🎯',
  'Анализ эффективности': '📈',
  'A/B тестирование': '🧪',
  'Настройка аналитики': '📊',
  'Оптимизация конверсий': '💰',
  'Email-маркетинг': '📧',
  'Контекстная реклама': '🔍',
  'Таргетированная реклама': '🎯',
  'SEO оптимизация': '🔍',
  'Веб-аналитика': '📊',
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
  return formatDateShortUTC5(iso)
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
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
        📋 Без дедлайна
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

// Helper function to translate recurrence types
const getRecurrenceTypeLabel = (type: string): string => {
  switch (type) {
    case 'daily': return 'Ежедневно'
    case 'weekly': return 'Еженедельно'
    case 'monthly': return 'Ежемесячно'
    default: return type
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
  const [deadlineTime, setDeadlineTime] = useState('')
  const [deadlineDate, setDeadlineDate] = useState('')
  const [project, setProject] = useState('')
  const [taskType, setTaskType] = useState('')
  const [taskFormat, setTaskFormat] = useState('')
  const [executorRole, setExecutorRole] = useState('')
  const [highPriority, setHighPriority] = useState(false)
  const [isRecurring, setIsRecurring] = useState(false)
  const [recurrenceType, setRecurrenceType] = useState('')
  const [recurrenceTime, setRecurrenceTime] = useState('')
  const [recurrenceDays, setRecurrenceDays] = useState<number[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [projects, setProjects] = useState<{id: number; name: string}[]>([])

  // Добавляем состояние для активной вкладки
  const [activeTab, setActiveTab] = useState<'regular' | 'recurring'>('regular')

  // Фильтры для обычных задач
  const [filterRole, setFilterRole] = usePersistedState('filter_tasks_regular_role', '')
  const [filterUser, setFilterUser] = useState(() => {
    try {
      const stored = localStorage.getItem('filter_tasks_regular_user')
      if (stored !== null) {
        const parsed = JSON.parse(stored)
        console.log('Initial filterUser from localStorage:', parsed)
        return parsed
      }
    } catch (e) {
      console.warn('Error parsing filterUser from localStorage:', e)
    }
    // Устанавливаем текущего пользователя по умолчанию только при первом запуске
    const userId = Number(localStorage.getItem('userId'))
    return userId ? String(userId) : ''
  })
  const [hasInitialized, setHasInitialized] = useState(false)
  const [filterDate, setFilterDate] = usePersistedState('filter_tasks_regular_date', 'all')
  const [customDate, setCustomDate] = usePersistedState('filter_tasks_regular_custom_date', '')
  const [filterStatus, setFilterStatus] = usePersistedState('filter_tasks_regular_status', 'in_progress')
  const [filterProject, setFilterProject] = usePersistedState('filter_tasks_regular_project', '')

  // Фильтры для повторяющихся задач (шаблонов)
  const [filterRoleRecurring, setFilterRoleRecurring] = usePersistedState('filter_tasks_recurring_role', '')
  const [filterUserRecurring, setFilterUserRecurring] = useState(() => {
    try {
      const stored = localStorage.getItem('filter_tasks_recurring_user')
      if (stored !== null) {
        return JSON.parse(stored)
      }
    } catch (e) {
      console.warn('Error parsing filterUserRecurring from localStorage:', e)
    }
    return ''
  })
  const [filterDateRecurring, setFilterDateRecurring] = usePersistedState('filter_tasks_recurring_date', 'all')
  const [customDateRecurring, setCustomDateRecurring] = usePersistedState('filter_tasks_recurring_custom_date', '')
  const [filterStatusRecurring, setFilterStatusRecurring] = usePersistedState('filter_tasks_recurring_status', '')
  const [filterProjectRecurring, setFilterProjectRecurring] = usePersistedState('filter_tasks_recurring_project', '')

  const role = localStorage.getItem('role') || ''
  const userId = Number(localStorage.getItem('userId'))

  // Helper function to get effective role (executor's role or current user's role)
  const getEffectiveRole = (executorId: number | string | null): string => {
    if (executorId && Array.isArray(users)) {
      const executor = users.find((u) => u.id === Number(executorId))
      return executor?.role || role
    }
    return role
  }

  // Сохраняем filterUser в localStorage при изменении
  useEffect(() => {
    console.log('Saving filterUser to localStorage:', filterUser)
    localStorage.setItem('filter_tasks_regular_user', JSON.stringify(filterUser))
  }, [filterUser])

  // Сохраняем filterUserRecurring в localStorage при изменении
  useEffect(() => {
    localStorage.setItem('filter_tasks_recurring_user', JSON.stringify(filterUserRecurring))
  }, [filterUserRecurring])

  useEffect(() => {
    // Устанавливаем текущего пользователя только при первом заходе, если в localStorage нет сохраненного значения
    if (!hasInitialized && userId) {
      const stored = localStorage.getItem('filter_tasks_regular_user')
      console.log('Initialization check:', { stored, filterUser, userId })

      // Если в localStorage нет значения, устанавливаем текущего пользователя
      if (stored === null) {
        console.log('No stored filter, setting default user filter to:', String(userId))
        setFilterUser(String(userId))
      }
      setHasInitialized(true)
    }
  }, [userId, hasInitialized])

  const allowedUsers = Array.isArray(users) ? users.filter((u) => {
    if (isAdmin(role)) return true
    if (role === 'designer') return u.role === 'designer'
    if (role === 'smm_manager')
      return u.role === 'designer' || u.role === 'smm_manager'
    return false
  }) : []

  const allowedRoles = () => {
    if (isAdmin(role)) return ['designer', 'smm_manager', 'admin']
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
      .then((data) => {
        console.log('Tasks from API:', data);
        setTasks(Array.isArray(data) ? data : []);
      })
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
      .then((data) => {
        const activeProjects = Array.isArray(data) ? data.filter((p: any) => !p.is_archived) : []
        setProjects(activeProjects)
      })
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

    // Фильтрация по вкладкам
    // Для обычных задач показываем только те, что никогда не были повторяющимися
    if (activeTab === 'regular' && t.is_recurring) return false
    // Для повторяющихся задач показываем все, что когда-либо были повторяющимися (включая остановленные)
    // Пока что используем существующую логику, но можно расширить если в базе есть поле was_recurring
    if (activeTab === 'recurring' && !t.is_recurring) return false

    // Используем разные фильтры в зависимости от активной вкладки
    const currentFilterStatus = activeTab === 'recurring' ? filterStatusRecurring : filterStatus
    const currentFilterRole = activeTab === 'recurring' ? filterRoleRecurring : filterRole
    const currentFilterUser = activeTab === 'recurring' ? filterUserRecurring : filterUser
    const currentFilterProject = activeTab === 'recurring' ? filterProjectRecurring : filterProject
    const currentFilterDate = activeTab === 'recurring' ? filterDateRecurring : filterDate
    const currentCustomDate = activeTab === 'recurring' ? customDateRecurring : customDate

    const execRole = users.find((u) => u.id === t.executor_id)?.role
    if (role === 'designer' && execRole !== 'designer') return false
    if (
      role === 'smm_manager' &&
      execRole !== 'designer' &&
      execRole !== 'smm_manager'
    )
      return false
    if (currentFilterStatus !== 'all') {
      if (currentFilterStatus === 'in_progress' && t.status !== 'in_progress' && t.status !== 'new') return false
      if (currentFilterStatus === 'overdue' && t.status !== 'overdue') return false
      if (currentFilterStatus === 'done' && t.status !== 'done') return false
    }
    if (currentFilterRole) {
      const exec = users.find((u) => u.id === t.executor_id)
      if (!exec || exec.role !== currentFilterRole) return false
    }
    if (currentFilterUser && String(t.executor_id) !== currentFilterUser) return false
    if (currentFilterProject && t.project !== currentFilterProject) return false
    if (currentFilterDate !== 'all') {
      const created = new Date(t.created_at)
      const now = new Date()
      const diff = now.getTime() - created.getTime()
      if (currentFilterDate === 'today' && diff > 86400000) return false
      if (currentFilterDate === 'week' && diff > 7 * 86400000) return false
      if (currentFilterDate === 'month' && diff > 30 * 86400000) return false
      if (currentFilterDate === 'custom' && currentCustomDate) {
        const sel = new Date(currentCustomDate)
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
      // First sort by priority: high priority tasks first
      if (a.high_priority && !b.high_priority) return -1
      if (!a.high_priority && b.high_priority) return 1
      
      // Then sort by creation date: newest first
      const dateA = new Date(a.created_at).getTime()
      const dateB = new Date(b.created_at).getTime()
      return dateB - dateA
    })

  const validateDeadline = () => {
    // Валидация времени удалена - пользователь может ставить задачи в любое время
    return true
  }

  const createTask = async () => {
    // Валидация времени убрана
    let deadlineStr: string | undefined
    if (deadlineTime.length === 5) {
      if (isRecurring) {
        // Для повторяющихся задач используем текущую дату
        const now = new Date()
        const [hh, mm] = deadlineTime.split(':').map(Number)
        const today = new Date(now)
        today.setHours(hh, mm, 0, 0)
        
        const y = today.getFullYear()
        const m = String(today.getMonth() + 1).padStart(2, '0')
        const d = String(today.getDate()).padStart(2, '0')
        deadlineStr = `${y}-${m}-${d}T${deadlineTime}`
      } else if (deadlineDate) {
        // Для обычных задач используем выбранную дату
        deadlineStr = `${deadlineDate}T${deadlineTime}`
      }
    }
    const payload = {
      title,
      description,
      project: project || undefined,
      task_type: taskType || undefined,
      task_format: taskFormat || undefined,
      executor_id: executorId ? Number(executorId) : undefined,
      deadline: deadlineStr,
      high_priority: highPriority,
      is_recurring: isRecurring,
      recurrence_type: isRecurring ? recurrenceType : undefined,
      recurrence_time: isRecurring ? recurrenceTime : undefined,
      recurrence_days: isRecurring && recurrenceDays.length > 0 ? recurrenceDays.join(',') : undefined,
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
    setDeadlineTime('')
    setDeadlineDate('')
    setHighPriority(false)
    setIsRecurring(false)
    setRecurrenceType('')
    setRecurrenceDays([])
    const res = await fetch(`${API_URL}/tasks/`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
    const data = await res.json()
    console.log('Tasks refreshed:', data);
    setTasks(Array.isArray(data) ? data : [])
  }

  const saveTask = async () => {
    if (!selectedTask) return
    // Валидация времени убрана
    let deadlineStr: string | undefined
    if (deadlineTime.length === 5) {
      if (isRecurring) {
        // Для повторяющихся задач используем текущую дату
        const now = new Date()
        const [hh, mm] = deadlineTime.split(':').map(Number)
        const today = new Date(now)
        today.setHours(hh, mm, 0, 0)
        
        const y = today.getFullYear()
        const m = String(today.getMonth() + 1).padStart(2, '0')
        const d = String(today.getDate()).padStart(2, '0')
        deadlineStr = `${y}-${m}-${d}T${deadlineTime}`
      } else if (deadlineDate) {
        // Для обычных задач используем выбранную дату
        deadlineStr = `${deadlineDate}T${deadlineTime}`
      }
    }
    const payload = {
      title,
      description,
      project: project || undefined,
      task_type: taskType || undefined,
      task_format: taskFormat || undefined,
      executor_id: executorId ? Number(executorId) : undefined,
      deadline: deadlineStr,
      high_priority: highPriority,
      is_recurring: isRecurring,
      recurrence_type: isRecurring ? recurrenceType : undefined,
      recurrence_time: isRecurring ? recurrenceTime : undefined,
      recurrence_days: isRecurring && recurrenceDays.length > 0 ? recurrenceDays.join(',') : undefined,
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
    setDeadlineTime('')
    setDeadlineDate('')
    setHighPriority(false)
    setIsRecurring(false)
    setRecurrenceType('')
    setRecurrenceDays([])
    const res = await fetch(`${API_URL}/tasks/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    const data = await res.json()
    console.log('Tasks after save:', data);
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

  // Функция для остановки повторений задачи
  const stopRecurring = async (id: number) => {
    const token = localStorage.getItem('token')
    try {
      // Используем более простой подход - отправляем PATCH запрос только с нужными полями
      const response = await fetch(`${API_URL}/tasks/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          is_recurring: false
        }),
      })

      if (response.ok) {
        // Обновляем список задач
        const res = await fetch(`${API_URL}/tasks/`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        const data = await res.json()
        setTasks(Array.isArray(data) ? data : [])

        // Если модальное окно открыто для этой задачи, обновляем состояние
        if (selectedTask && selectedTask.id === id) {
          setSelectedTask(prev => prev ? { ...prev, is_recurring: false } : null)
          setIsRecurring(false)
        }

        return true
      } else {
        // Если PATCH не поддерживается, пробуем стандартное обновление
        console.log('PATCH failed, trying PUT with full data')

        // Находим задачу в текущем состоянии
        const currentTask = tasks.find(t => t.id === id)
        if (!currentTask) {
          console.error('Task not found in current state')
          return false
        }

        // Создаем полную копию задачи с отключенными повторениями
        const updateData = {
          ...currentTask,
          is_recurring: false,
          recurrence_type: undefined,
          recurrence_time: undefined,
          recurrence_days: undefined,
          next_run_at: undefined
        }

        const putResponse = await fetch(`${API_URL}/tasks/${id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(updateData),
        })

        if (putResponse.ok) {
          // Обновляем список задач
          const res = await fetch(`${API_URL}/tasks/`, {
            headers: { Authorization: `Bearer ${token}` },
          })
          const data = await res.json()
          setTasks(Array.isArray(data) ? data : [])

          // Если модальное окно открыто для этой задачи, обновляем состояние
          if (selectedTask && selectedTask.id === id) {
            setSelectedTask(prev => prev ? { ...prev, is_recurring: false } : null)
            setIsRecurring(false)
          }

          return true
        } else {
          const errorData = await putResponse.json()
          console.error('PUT API Error:', putResponse.status, errorData)
        }
      }
    } catch (error) {
      console.error('Error stopping recurring task:', error)
    }
    return false
  }


  const togglePriority = async (id: number, currentPriority: boolean) => {
    try {
      console.log('Toggling priority for task', id, 'from', currentPriority, 'to', !currentPriority)
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/tasks/${id}/priority`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          high_priority: !currentPriority
        })
      })
      
      if (!response.ok) {
        console.error('Failed to toggle priority:', response.status, response.statusText)
        const errorText = await response.text()
        console.error('Error response:', errorText)
        return
      }
      
      console.log('Priority toggled successfully, updating local state')
      
      // Обновляем задачу в локальном состоянии, создавая новый массив для форсирования ререндера
      setTasks(prevTasks => {
        if (!Array.isArray(prevTasks)) return []
        const updatedTasks = prevTasks.map(t => 
          t.id === id ? { ...t, high_priority: !currentPriority } : t
        )
        console.log('Updated tasks:', updatedTasks.find(t => t.id === id))
        return [...updatedTasks] // Создаем новый массив для гарантированного ререндера
      })
      
      console.log('Local state updated')
    } catch (error) {
      console.error('Error toggling priority:', error)
    }
  }

  const acceptTask = async (id: number) => {
    const token = localStorage.getItem('token')
    const res = await fetch(`${API_URL}/tasks/${id}/accept`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      const updated = await res.json()
      setTasks(Array.isArray(tasks) ? tasks.map((t) => (t.id === id ? updated : t)) : [])
    }
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
        <div className="flex justify-between items-center mb-6">
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
              // Автоматически устанавливаем роль если доступна только одна
              const availableRoles = allowedRoles()
              if (availableRoles.length === 1) {
                setExecutorRole(availableRoles[0])
              } else {
                setExecutorRole('')
              }
              setHighPriority(false)
              setDeadlineTime('')
              setDeadlineDate('')
              // Автоматически устанавливаем тип задачи в зависимости от активной вкладки
              setIsRecurring(activeTab === 'recurring')
              setShowModal(true)
            }}
          >
            <span>+</span>
            <span>{activeTab === 'recurring' ? 'Создать повторяющуюся задачу' : 'Создать задачу'}</span>
          </button>
        </div>

        {/* Вкладки */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            <button
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                activeTab === 'regular'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('regular')}
            >
              <div className="flex items-center space-x-2">
                <span className="text-lg">📋</span>
                <span>Обычные задачи</span>
                <span className="inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white bg-blue-600 rounded-full">
                  {tasks.filter(t => !t.is_recurring).length}
                </span>
              </div>
            </button>
            <button
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                activeTab === 'recurring'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
              onClick={() => setActiveTab('recurring')}
            >
              <div className="flex items-center space-x-2">
                <span className="text-lg">🔄</span>
                <span>Шаблоны повторяющихся задач</span>
                <span className="inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white bg-green-600 rounded-full">
                  {tasks.filter(t => t.is_recurring).length}
                </span>
              </div>
            </button>
          </nav>
        </div>
        
        {/* Легенда статусов */}
        <div className="flex items-center gap-6 mt-4 p-3 bg-gray-50 rounded-lg">
          <span className="text-sm font-medium text-gray-700">Статусы задач:</span>
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span className="text-sm text-gray-600">Новая</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <span className="text-sm text-gray-600">В работе</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="text-sm text-gray-600">Выполнена</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span className="text-sm text-gray-600">Просрочена</span>
            </div>
          </div>
        </div>
      </div>
      <div className="bg-white p-6 shadow-sm border-b">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex flex-wrap gap-3">
            <select
              className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              value={activeTab === 'recurring' ? filterProjectRecurring : filterProject}
              onChange={(e) => activeTab === 'recurring' ? setFilterProjectRecurring(e.target.value) : setFilterProject(e.target.value)}
            >
              <option value="">Все проекты</option>
              {Array.isArray(projects) && projects.map(p => (
                <option key={p.id} value={p.name}>{p.name}</option>
              ))}
            </select>
            {role !== 'designer' && (
              <select
                className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                value={activeTab === 'recurring' ? filterRoleRecurring : filterRole}
                onChange={(e) => activeTab === 'recurring' ? setFilterRoleRecurring(e.target.value) : setFilterRole(e.target.value)}
              >
                <option value="">Все роли</option>
                <option value="designer">{ROLE_NAMES.designer}</option>
                <option value="smm_manager">{ROLE_NAMES.smm_manager}</option>
                <option value="digital">{ROLE_NAMES.digital}</option>
                {isAdmin(role) && (
                  <option value="admin">{ROLE_NAMES.admin}</option>
                )}
              </select>
            )}
            <select
              className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              value={activeTab === 'recurring' ? filterUserRecurring : filterUser}
              onChange={(e) => {
                const newValue = e.target.value
                console.log('onChange: Changing filterUser from', activeTab === 'recurring' ? filterUserRecurring : filterUser, 'to', newValue, 'type:', typeof newValue)
                if (activeTab === 'recurring') {
                  setFilterUserRecurring(newValue)
                } else {
                  setFilterUser(newValue)
                }
              }}
            >
              <option value="">Все сотрудники</option>
              {Array.isArray(users) && users
                .filter((u) =>
                  isAdmin(role)
                    ? (activeTab === 'recurring' ? filterRoleRecurring : filterRole)
                      ? u.role === (activeTab === 'recurring' ? filterRoleRecurring : filterRole)
                      : true
                    : !isAdmin(u.role) && ((activeTab === 'recurring' ? filterRoleRecurring : filterRole) ? u.role === (activeTab === 'recurring' ? filterRoleRecurring : filterRole) : true)
                )
                .map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name}
                  </option>
                ))}
            </select>
            <select
              className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              value={activeTab === 'recurring' ? filterDateRecurring : filterDate}
              onChange={(e) => activeTab === 'recurring' ? setFilterDateRecurring(e.target.value) : setFilterDate(e.target.value)}
            >
              <option value="all">За все время</option>
              <option value="today">За сегодня</option>
              <option value="week">За неделю</option>
              <option value="month">За месяц</option>
              <option value="custom">Выбрать дату</option>
            </select>
            {(activeTab === 'recurring' ? filterDateRecurring : filterDate) === 'custom' && (
              <input
                type="date"
                className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                value={activeTab === 'recurring' ? customDateRecurring : customDate}
                onChange={(e) => activeTab === 'recurring' ? setCustomDateRecurring(e.target.value) : setCustomDate(e.target.value)}
              />
            )}
            <select
              className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              value={activeTab === 'recurring' ? filterStatusRecurring : filterStatus}
              onChange={(e) => activeTab === 'recurring' ? setFilterStatusRecurring(e.target.value) : setFilterStatus(e.target.value)}
            >
              <option value="in_progress">В работе</option>
              <option value="overdue">Просроченные</option>
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
                    {activeTab === 'recurring' ? 'Расписание' : 'Дедлайн'}
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
                    className={`hover:bg-gray-50 transition-colors duration-150 ${
                      ''
                    }`}
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-3">
                        <div className="flex items-center space-x-2">
                          <div className={`w-3 h-3 rounded-full ${
                            t.status === 'new' ? 'bg-blue-500' :
                            t.status === 'in_progress' ? 'bg-yellow-500' :
                            t.status === 'overdue' ? 'bg-red-500' :
                            t.status === 'done' ? 'bg-green-500' :
                            'bg-gray-400'
                          }`}></div>
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
                            setHighPriority(t.high_priority || false)
                            setIsRecurring(t.is_recurring || false)
                            setRecurrenceType(t.recurrence_type || '')
                            // Парсим recurrence_days из строки в массив
                            if (t.recurrence_days) {
                              const days = t.recurrence_days.split(',').map(d => parseInt(d.trim())).filter(d => !isNaN(d))
                              setRecurrenceDays(days)
                            } else {
                              setRecurrenceDays([])
                            }
                            setRecurrenceTime(t.recurrence_time || '')
                            if (t.deadline) {
                              const d = new Date(t.deadline)
                              // Используем локальное время вместо UTC
                              const hours = d.getHours().toString().padStart(2, '0')
                              const minutes = d.getMinutes().toString().padStart(2, '0')
                              setDeadlineTime(`${hours}:${minutes}`)
                              
                              // Устанавливаем дату дедлайна
                              const year = d.getFullYear()
                              const month = (d.getMonth() + 1).toString().padStart(2, '0')
                              const day = d.getDate().toString().padStart(2, '0')
                              setDeadlineDate(`${year}-${month}-${day}`)
                            } else {
                              setDeadlineTime('')
                              setDeadlineDate('')
                            }
                          }}
                        >
                          <div className="flex items-center gap-2">
                            <button
                              className={`inline-flex items-center justify-center w-5 h-5 hover:scale-110 transition-all duration-200 ${
                                t.high_priority 
                                  ? 'text-yellow-500 drop-shadow-[0_0_8px_rgba(250,204,21,0.4)]' 
                                  : 'text-gray-400 hover:text-yellow-400'
                              }`}
                              title={t.high_priority ? 'Убрать высокий приоритет' : 'Поставить высокий приоритет'}
                              onClick={(e) => {
                                e.stopPropagation() // Предотвращаем открытие модального окна
                                togglePriority(t.id, t.high_priority || false)
                              }}
                            >
                              <svg 
                                width="16" 
                                height="16" 
                                viewBox="0 0 24 24" 
                                fill={t.high_priority ? "currentColor" : "none"}
                                stroke="currentColor" 
                                strokeWidth="2"
                              >
                                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                              </svg>
                            </button>
                            {t.title}
                            {t.is_recurring && (
                              <span className="text-blue-600 text-xs" title="Повторяющаяся задача">🔄</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">
                        <div className="truncate">{t.project || '-'}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg">{TYPE_ICONS[t.task_type || ''] || '📋'}</span>
                        <span className="text-sm text-gray-900 truncate">{t.task_type || '-'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">
                        <div className="truncate">{getUserName(t.author_id) || '-'}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">
                        <div className="truncate">{getExecutorName(t.executor_id) || '-'}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">
                        <div className="truncate">{formatDate(t.created_at)}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm">
                        {activeTab === 'recurring' && t.is_recurring ? (
                          <div className="space-y-1">
                            {t.recurrence_time && (
                              <div className="text-xs text-gray-600">
                                ⏰ {t.recurrence_time}
                              </div>
                            )}
                            {t.next_run_at && (
                              <div className="text-xs text-gray-600">
                                📅 След: {formatDateAsIs(t.next_run_at).split(' ')[0]}
                              </div>
                            )}
                            <div className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                              ✅ Активна
                            </div>
                          </div>
                        ) : activeTab === 'recurring' && !t.is_recurring ? (
                          <div className="space-y-1">
                            <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                              ⏸️ Остановлена
                            </div>
                            <div className="text-xs text-gray-500">
                              Повторения отключены
                            </div>
                          </div>
                        ) : t.status === 'new' ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                            🆕 Новая
                          </span>
                        ) : t.status === 'overdue' ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            ⏰ Просрочена
                          </span>
                        ) : t.status === 'done' ? (
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
                        {(() => {
                          const isOverdue = t.deadline && t.status !== 'done' && new Date(t.deadline) < new Date()
                          const canManage = t.executor_id === userId || t.author_id === userId || isAdmin(role) || isOverdue

                          // Для повторяющихся задач - специальные действия с обычным функционалом
                          if (activeTab === 'recurring') {
                            // Если задача больше не повторяющаяся (остановлена), показываем обычные действия
                            if (!t.is_recurring) {
                              // Обычные действия для остановленных повторяющихся задач
                              if (t.status === 'new') {
                                return (
                                  <>
                                    {canManage && (
                                      <button
                                        className="inline-flex items-center px-3 py-1.5 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                                        onClick={() => deleteTask(t.id)}
                                      >
                                        Удалить
                                      </button>
                                    )}
                                    {t.executor_id === userId && (
                                      <button
                                        className="inline-flex items-center px-3 py-1.5 border border-blue-300 text-xs font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                                        onClick={() => acceptTask(t.id)}
                                      >
                                        Принять в работу
                                      </button>
                                    )}
                                  </>
                                )
                              } else if (t.status === 'in_progress') {
                                return (
                                  <>
                                    {canManage && (
                                      <button
                                        className="inline-flex items-center px-3 py-1.5 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                                        onClick={() => deleteTask(t.id)}
                                      >
                                        Удалить
                                      </button>
                                    )}
                                    {canManage && (
                                      <button
                                        className="inline-flex items-center px-3 py-1.5 border border-green-300 text-xs font-medium rounded-md text-green-700 bg-green-50 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
                                        onClick={() => toggleStatus(t.id, 'done')}
                                      >
                                        Завершить
                                      </button>
                                    )}
                                  </>
                                )
                              } else {
                                return (
                                  <>
                                    {canManage && (
                                      <button
                                        className="inline-flex items-center px-3 py-1.5 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                                        onClick={() => deleteTask(t.id)}
                                      >
                                        Удалить
                                      </button>
                                    )}
                                    {(t.executor_id === userId || t.author_id === userId || isAdmin(role)) && (
                                      <button
                                        className="inline-flex items-center px-3 py-1.5 border border-yellow-300 text-xs font-medium rounded-md text-yellow-700 bg-yellow-50 hover:bg-yellow-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 transition-colors"
                                        onClick={() => toggleStatus(t.id, 'in_progress')}
                                      >
                                        Возобновить
                                      </button>
                                    )}
                                  </>
                                )
                              }
                            }
                            // Для активных повторяющихся задач
                            else if (t.is_recurring) {
                              // Для новых повторяющихся задач
                              if (t.status === 'new') {
                                return (
                                  <>
                                    {canManage && (
                                      <button
                                        className="inline-flex items-center px-3 py-1.5 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                                        onClick={() => deleteTask(t.id)}
                                        title="Полностью удалить повторяющуюся задачу"
                                      >
                                        🗑️ Удалить
                                      </button>
                                    )}
                                    {t.executor_id === userId && (
                                      <button
                                        className="inline-flex items-center px-3 py-1.5 border border-blue-300 text-xs font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                                        onClick={() => acceptTask(t.id)}
                                      >
                                        Принять в работу
                                      </button>
                                    )}
                                  </>
                                )
                              }
                              // Для активных повторяющихся задач (в работе)
                              else if (t.status === 'in_progress') {
                                return (
                                  <>
                                    {canManage && (
                                      <button
                                        className="inline-flex items-center px-3 py-1.5 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                                        onClick={() => deleteTask(t.id)}
                                        title="Полностью удалить повторяющуюся задачу"
                                      >
                                        🗑️ Удалить
                                      </button>
                                    )}
                                    {canManage && (
                                      <button
                                        className="inline-flex items-center px-3 py-1.5 border border-orange-300 text-xs font-medium rounded-md text-orange-700 bg-orange-50 hover:bg-orange-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 transition-colors"
                                        onClick={() => toggleStatus(t.id, 'done')}
                                        title="Приостановить автосоздание задач по этому шаблону"
                                      >
                                        ⏸️ Приостановить
                                      </button>
                                    )}
                                  </>
                                )
                              }
                              // Для завершенных повторяющихся задач (приостановленных)
                              else {
                                return (
                                  <>
                                    {canManage && (
                                      <button
                                        className="inline-flex items-center px-3 py-1.5 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                                        onClick={() => deleteTask(t.id)}
                                        title="Полностью удалить повторяющуюся задачу"
                                      >
                                        🗑️ Удалить
                                      </button>
                                    )}
                                    {(t.executor_id === userId || t.author_id === userId || isAdmin(role)) && (
                                      <button
                                        className="inline-flex items-center px-3 py-1.5 border border-green-300 text-xs font-medium rounded-md text-green-700 bg-green-50 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
                                        onClick={() => toggleStatus(t.id, 'in_progress')}
                                        title="Возобновить автосоздание задач по этому шаблону"
                                      >
                                        ▶️ Возобновить
                                      </button>
                                    )}
                                  </>
                                )
                              }
                            }
                          }

                          // Для новых задач
                          if (t.status === 'new') {
                            return (
                              <>
                                {canManage && (
                                  <button
                                    className="inline-flex items-center px-3 py-1.5 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                                    onClick={() => deleteTask(t.id)}
                                  >
                                    Удалить
                                  </button>
                                )}
                                {t.executor_id === userId && (
                                  <button
                                    className="inline-flex items-center px-3 py-1.5 border border-blue-300 text-xs font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                                    onClick={() => acceptTask(t.id)}
                                  >
                                    Принять в работу
                                  </button>
                                )}
                              </>
                            )
                          }
                          // Для активных задач (в работе)
                          else if (t.status === 'in_progress') {
                            return (
                              <>
                                {canManage && (
                                  <button
                                    className="inline-flex items-center px-3 py-1.5 border border-red-300 text-xs font-medium rounded-md text-red-700 bg-red-50 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                                    onClick={() => deleteTask(t.id)}
                                  >
                                    Удалить
                                  </button>
                                )}
                                {canManage && (
                                  <button
                                    className="inline-flex items-center px-3 py-1.5 border border-green-300 text-xs font-medium rounded-md text-green-700 bg-green-50 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
                                    onClick={() => toggleStatus(t.id, 'done')}
                                  >
                                    Завершить
                                  </button>
                                )}
                                {isOverdue && !canManage && (
                                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                    Просрочено
                                  </span>
                                )}
                              </>
                            )
                          }
                          // Для завершенных задач
                          else {
                            return (
                              (t.executor_id === userId || t.author_id === userId || isAdmin(role)) && (
                                <button
                                  className="inline-flex items-center px-3 py-1.5 border border-yellow-300 text-xs font-medium rounded-md text-yellow-700 bg-yellow-50 hover:bg-yellow-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 transition-colors"
                                  onClick={() => toggleStatus(t.id, 'in_progress')}
                                >
                                  Возобновить
                                </button>
                              )
                            )
                          }
                        })()}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {sortedTasks.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 text-6xl mb-4">
                {activeTab === 'recurring' ? '🔄' : '📋'}
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {activeTab === 'recurring' ? 'Нет повторяющихся задач' : 'Нет задач'}
              </h3>
              <p className="text-gray-500">
                {activeTab === 'recurring'
                  ? 'Здесь пока нет ни одной повторяющейся задачи. Создайте автоматически повторяющуюся задачу!'
                  : 'Пока что здесь нет ни одной задачи. Создайте первую задачу!'
                }
              </p>
              {activeTab === 'recurring' && (
                <div className="mt-6 p-4 bg-blue-50 rounded-lg max-w-lg mx-auto">
                  <h4 className="font-medium text-blue-900 mb-2">Что такое шаблоны повторяющихся задач?</h4>
                  <p className="text-sm text-blue-700 mb-2">
                    Шаблоны повторяющихся задач автоматически создают новые задачи по расписанию (ежедневно, еженедельно или ежемесячно).
                    Это удобно для регулярных задач как публикации в соцсетях, отчеты или встречи. Каждая новая задача создаётся со статусом "Новая".
                  </p>
                  <p className="text-sm text-blue-700">
                    <strong>💡 Управление автосозданием:</strong> Нажмите "⏸️ Приостановить" чтобы временно остановить создание новых задач по шаблону.
                    Нажмите "▶️ Возобновить" чтобы снова запустить автосоздание.
                  </p>
                </div>
              )}
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
            
            {/* При создании новой задачи сначала выбираем роль, исполнителя и проект, а затем название */}
            {isEditing && !selectedTask ? (
              <>
                {/* Выбор роли исполнителя (показываем только если доступно больше одной роли или для дизайнеров) */}
                {(allowedRoles().length > 1 || role === 'designer') && (
                  <select
                    className="border p-2 w-full mb-2"
                    value={executorRole}
                    onChange={(e) => {
                      setExecutorRole(e.target.value)
                      setExecutorId('')
                    }}
                  >
                    <option value="">
                      {allowedRoles().length === 1 ? 
                        `Роль исполнителя: ${ROLE_NAMES[allowedRoles()[0]]}` : 
                        'Выберите роль исполнителя'
                      }
                    </option>
                    {allowedRoles().map((r) => (
                      <option key={r} value={r}>
                        {ROLE_NAMES[r]}
                      </option>
                    ))}
                  </select>
                )}
                
                {/* Выбор конкретного исполнителя */}
                <select
                  className="border p-2 w-full mb-2"
                  value={executorId}
                  onChange={(e) => setExecutorId(e.target.value)}
                  disabled={allowedRoles().length > 1 && !executorRole}
                >
                  <option value="" disabled>
                    {allowedRoles().length > 1 && !executorRole ? 
                      'Сначала выберите роль исполнителя' : 
                      'Выберите исполнителя'
                    }
                  </option>
                  {allowedUsers
                    .filter((u) => {
                      // Если выбрана роль, фильтруем по ней
                      if (executorRole) return u.role === executorRole
                      // Если роль одна, показываем пользователей этой роли
                      if (allowedRoles().length === 1) return u.role === allowedRoles()[0]
                      // Иначе показываем всех доступных пользователей
                      return true
                    })
                    .map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name} ({ROLE_NAMES[u.role]})
                      </option>
                    ))}
                </select>
                
                {/* Выбор проекта (показывается после выбора исполнителя) */}
                {executorId && (
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
                )}
                
                {/* Выбор типа задачи (показывается после выбора проекта или если проект не обязателен) */}
                {executorId && (
                  <select
                    className="border p-2 w-full mb-2"
                    value={taskType}
                    onChange={(e) => setTaskType(e.target.value)}
                  >
                    <option value="">Тип задачи не выбран</option>
                    {(
                      getEffectiveRole(executorId) === 'designer'
                        ? DESIGNER_TYPES
                        : getEffectiveRole(executorId) === 'digital'
                        ? DIGITAL_TYPES
                        : isAdmin(getEffectiveRole(executorId))
                        ? ADMIN_TYPES
                        : MANAGER_TYPES
                    ).map((t) => (
                      <option key={t} value={t}>
                        {TYPE_ICONS[t]} {t}
                      </option>
                    ))}
                  </select>
                )}
                
                {/* Выбор формата (только для дизайнеров) */}
                {executorId && getEffectiveRole(executorId) === 'designer' && (
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
                
                {/* Название и описание задачи (показывается только после выбора всех обязательных полей) */}
                {executorId && (
                  <>
                    <input
                      className="border p-2 w-full mb-2"
                      placeholder="Заголовок"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                    />
                    <textarea
                      className="border p-2 w-full mb-2"
                      placeholder="Описание"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                    />
                  </>
                )}
              </>
            ) : (
              <>
                {/* При редактировании задачи показываем все поля сразу */}
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
                {isEditing && allowedRoles().length > 0 ? (
                  <>
                    {/* Выбор роли исполнителя (показываем только если доступно больше одной роли или для дизайнеров) */}
                    {(allowedRoles().length > 1 || role === 'designer') && (
                      <select
                        className="border p-2 w-full mb-2"
                        value={executorRole}
                        onChange={(e) => {
                          setExecutorRole(e.target.value)
                          setExecutorId('')
                        }}
                      >
                        <option value="">
                          {allowedRoles().length === 1 ? 
                            `Роль исполнителя: ${ROLE_NAMES[allowedRoles()[0]]}` : 
                            'Выберите роль исполнителя'
                          }
                        </option>
                        {allowedRoles().map((r) => (
                          <option key={r} value={r}>
                            {ROLE_NAMES[r]}
                          </option>
                        ))}
                      </select>
                    )}
                    
                    {/* Выбор конкретного исполнителя */}
                    <select
                      className="border p-2 w-full mb-2"
                      value={executorId}
                      onChange={(e) => setExecutorId(e.target.value)}
                      disabled={allowedRoles().length > 1 && !executorRole}
                    >
                      <option value="" disabled>
                        {allowedRoles().length > 1 && !executorRole ? 
                          'Сначала выберите роль исполнителя' : 
                          'Выберите исполнителя'
                        }
                      </option>
                      {allowedUsers
                        .filter((u) => {
                          // Если выбрана роль, фильтруем по ней
                          if (executorRole) return u.role === executorRole
                          // Если роль одна, показываем пользователей этой роли
                          if (allowedRoles().length === 1) return u.role === allowedRoles()[0]
                          // Иначе показываем всех доступных пользователей
                          return true
                        })
                        .map((u) => (
                          <option key={u.id} value={u.id}>
                            {u.name} ({ROLE_NAMES[u.role]})
                          </option>
                        ))}
                    </select>
                  </>
                ) : null}
                {executorId && isEditing ? (
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
                          getEffectiveRole(executorId) === 'designer'
                            ? DESIGNER_TYPES
                            : getEffectiveRole(executorId) === 'digital'
                            ? DIGITAL_TYPES
                            : isAdmin(getEffectiveRole(executorId))
                            ? ADMIN_TYPES
                            : MANAGER_TYPES
                        ).map((t) => (
                          <option key={t} value={t}>
                            {TYPE_ICONS[t]} {t}
                          </option>
                        ))}
                      </select>
                      {getEffectiveRole(executorId) === 'designer' && (
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
                ) : null}
              </>
            )}
            {executorId && !isEditing ? (
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
                  <div className="flex items-center gap-2">
                    Приоритет: 
                    {selectedTask?.high_priority ? (
                      <span className="flex items-center gap-1 text-yellow-500">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="2">
                          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                        </svg>
                        Высокий
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-gray-400">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                        </svg>
                        Обычный
                      </span>
                    )}
                  </div>
                  <div>Время постановки задачи: {formatDateAsIs(selectedTask?.created_at || '')}</div>
                  {selectedTask?.accepted_at && (
                    <div>Время принятия в работу: {formatDateAsIs(selectedTask.accepted_at)}</div>
                  )}
                  {selectedTask?.deadline && (
                    <div>Дедлайн: {formatDateAsIs(selectedTask.deadline)}</div>
                  )}
                  {selectedTask?.finished_at && (
                    <div>Время завершения задачи: {formatDateAsIs(selectedTask.finished_at)}</div>
                  )}
                  {selectedTask?.resume_count !== undefined && selectedTask.resume_count > 0 && (
                    <div className="flex items-center gap-2">
                      <span>Количество возобновлений:</span>
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                        🔄 {selectedTask.resume_count} раз{selectedTask.resume_count > 1 ? (selectedTask.resume_count > 4 ? '' : 'а') : ''}
                      </span>
                    </div>
                  )}
                  <div>Кто поставил задачу: {getUserName(selectedTask?.author_id)}</div>
                </div>
            ) : null}
            

            {/* Высокий приоритет */}
            {isEditing && (
              <div className="flex items-center gap-2 mb-4">
                <input
                  type="checkbox"
                  id="highPriority"
                  className="w-4 h-4"
                  checked={highPriority}
                  onChange={(e) => setHighPriority(e.target.checked)}
                />
                <label htmlFor="highPriority" className="text-sm font-medium text-gray-700">
                  Высокий приоритет
                </label>
              </div>
            )}

            {/* Повторяющаяся задача */}
            {isEditing && (
              <div className="mb-4 p-4 border rounded-lg bg-gray-50">
                <div className="flex items-center gap-2 mb-3">
                  <input
                    type="checkbox"
                    id="isRecurring"
                    className="w-4 h-4"
                    checked={isRecurring}
                    onChange={(e) => setIsRecurring(e.target.checked)}
                  />
                  <label htmlFor="isRecurring" className="text-sm font-medium text-gray-700">
                    🔄 Повторяющаяся задача
                  </label>
                </div>
                
                {isRecurring && (
                  <div className="ml-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Тип повторения:
                    </label>
                    <select
                      className="border p-2 w-full rounded-md mb-3"
                      value={recurrenceType}
                      onChange={(e) => {
                        setRecurrenceType(e.target.value)
                        setRecurrenceDays([]) // Сбрасываем выбранные дни при смене типа
                      }}
                    >
                      <option value="">Выберите тип повторения</option>
                      <option value="daily">Ежедневно</option>
                      <option value="weekly">Еженедельно</option>
                      <option value="monthly">Ежемесячно</option>
                    </select>
                    
                    {/* Выбор дней в зависимости от типа повторения */}
                    {recurrenceType === 'daily' && (
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Дни недели:
                        </label>
                        <div className="flex flex-wrap gap-2">
                          {[
                            { value: 1, label: 'Пн' },
                            { value: 2, label: 'Вт' },
                            { value: 3, label: 'Ср' },
                            { value: 4, label: 'Чт' },
                            { value: 5, label: 'Пт' },
                            { value: 6, label: 'Сб' },
                            { value: 7, label: 'Вс' }
                          ].map(day => (
                            <label key={day.value} className="flex items-center gap-1">
                              <input
                                type="checkbox"
                                checked={recurrenceDays.includes(day.value)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setRecurrenceDays([...recurrenceDays, day.value])
                                  } else {
                                    setRecurrenceDays(recurrenceDays.filter(d => d !== day.value))
                                  }
                                }}
                              />
                              <span className="text-sm">{day.label}</span>
                            </label>
                          ))}
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          Выберите дни недели для ежедневного повторения
                        </p>
                      </div>
                    )}
                    
                    {recurrenceType === 'weekly' && (
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Дни недели:
                        </label>
                        <div className="flex flex-wrap gap-2">
                          {[
                            { value: 1, label: 'Пн' },
                            { value: 2, label: 'Вт' },
                            { value: 3, label: 'Ср' },
                            { value: 4, label: 'Чт' },
                            { value: 5, label: 'Пт' },
                            { value: 6, label: 'Сб' },
                            { value: 7, label: 'Вс' }
                          ].map(day => (
                            <label key={day.value} className="flex items-center gap-1">
                              <input
                                type="checkbox"
                                checked={recurrenceDays.includes(day.value)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setRecurrenceDays([...recurrenceDays, day.value])
                                  } else {
                                    setRecurrenceDays(recurrenceDays.filter(d => d !== day.value))
                                  }
                                }}
                              />
                              <span className="text-sm">{day.label}</span>
                            </label>
                          ))}
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          Выберите дни недели для еженедельного повторения
                        </p>
                      </div>
                    )}
                    
                    {recurrenceType === 'monthly' && (
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          День месяца:
                        </label>
                        <select
                          className="border p-2 w-full rounded-md"
                          value={recurrenceDays.length > 0 ? recurrenceDays[0] : ''}
                          onChange={(e) => {
                            const day = parseInt(e.target.value)
                            if (day) {
                              setRecurrenceDays([day])
                            } else {
                              setRecurrenceDays([])
                            }
                          }}
                        >
                          <option value="">Выберите день месяца</option>
                          {Array.from({ length: 31 }, (_, i) => i + 1).map(day => (
                            <option key={day} value={day}>{day}</option>
                          ))}
                        </select>
                        <p className="text-xs text-gray-500 mt-1">
                          Выберите день месяца для ежемесячного повторения
                        </p>
                      </div>
                    )}
                    
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Время создания задачи:
                    </label>
                    <input
                      type="time"
                      className="border p-2 w-full rounded-md"
                      value={recurrenceTime}
                      onChange={(e) => setRecurrenceTime(e.target.value)}
                      placeholder="16:45"
                    />
                    
                    <p className="text-xs text-gray-500 mt-1">
                      Задача будет создаваться в указанное время. Если время еще не наступило сегодня - создастся сегодня, иначе в следующий период.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Информация о повторяющейся задаче для просмотра */}
            {!isEditing && selectedTask?.is_recurring && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 text-blue-800 flex-1">
                    <span className="text-lg">🔄</span>
                    <div>
                      <div className="font-medium">Повторяющаяся задача</div>
                      <div className="text-sm">
                        Тип повторения: {getRecurrenceTypeLabel(selectedTask.recurrence_type)}
                      </div>
                      {selectedTask.recurrence_time && (
                        <div className="text-sm">
                          Время создания: {selectedTask.recurrence_time}
                        </div>
                      )}
                      {selectedTask.recurrence_days && (
                        <div className="text-sm">
                          {selectedTask.recurrence_type === 'monthly' ? 'День месяца:' : 'Дни:'} {
                            selectedTask.recurrence_type === 'monthly'
                              ? selectedTask.recurrence_days
                              : selectedTask.recurrence_days.split(',').map(d => {
                                  const dayNames = { '1': 'Пн', '2': 'Вт', '3': 'Ср', '4': 'Чт', '5': 'Пт', '6': 'Сб', '7': 'Вс' }
                                  return dayNames[d.trim()] || d.trim()
                                }).join(', ')
                          }
                        </div>
                      )}
                      {selectedTask.next_run_at && (
                        <div className="text-sm">
                          Следующая генерация: {formatDateAsIs(selectedTask.next_run_at)}
                        </div>
                      )}
                    </div>
                  </div>
                  {/* Кнопка остановки повторений */}
                  {(selectedTask.author_id === userId || isAdmin(role)) && (
                    <button
                      className="inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-md text-red-700 bg-red-50 border border-red-200 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
                      onClick={async () => {
                        if (selectedTask && window.confirm('Вы уверены, что хотите остановить автоматическое создание этой задачи? Задача станет обычной и больше не будет повторяться.')) {
                          const success = await stopRecurring(selectedTask.id)
                          if (success) {
                            alert('Повторения задачи остановлены. Задача теперь обычная.')
                          } else {
                            alert('Ошибка при остановке повторений. Попробуйте еще раз.')
                          }
                        }
                      }}
                      title="Остановить автоматическое создание задачи"
                    >
                      ⏸️ Остановить повторения
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Дедлайн */}
            {isEditing && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-700 mb-2">Дедлайн</h3>
                
                {/* Для повторяющихся задач только время */}
                {isRecurring ? (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Время дедлайна:
                    </label>
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
                    />
                  </div>
                ) : (
                  /* Для обычных задач дата и время */
                  <div className="space-y-2">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Дата дедлайна:
                      </label>
                      <input
                        type="date"
                        className="border p-2 rounded"
                        value={deadlineDate}
                        onChange={(e) => setDeadlineDate(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Время дедлайна:
                      </label>
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
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="flex justify-end">
              <button
                className="mr-2 px-4 py-1 border rounded"
                onClick={() => { setShowModal(false); setSelectedTask(null); setIsEditing(false); }}
              >
                Закрыть
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
