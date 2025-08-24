import { useState, useEffect } from 'react'
import { API_URL } from '../api'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import {
  TrendingUp,
  Users,
  CheckSquare,
  Calendar,
  Clock,
  Target,
  Award,
  Activity
} from 'lucide-react'

interface AnalyticsData {
  tasksStats: {
    total: number
    completed: number
    inProgress: number
    overdue: number
    totalTrend?: number
    completedTrend?: number
    overdueTrend?: number
  }
  projectsStats: {
    total: number
    active: number
    completed: number
  }
  teamProductivity: Array<{
    name: string
    tasksAssigned: number
    tasksCompleted: number
    efficiency: number
  }>
  tasksByPeriod: Array<{
    period: string
    created: number
    completed: number
  }>
  tasksByType: Array<{
    name: string
    value: number
    color: string
  }>
}

interface User {
  id: number
  name: string
  role: string
}

interface Task {
  id: number
  title: string
  status: string
  created_at: string
  deadline?: string | null
  executor_id?: number
  author_id?: number
  finished_at?: string | null
}

function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState('month')
  const [users, setUsers] = useState<User[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [digitalTasks, setDigitalTasks] = useState<any[]>([])
  const [customStartDate, setCustomStartDate] = useState('')
  const [customEndDate, setCustomEndDate] = useState('')
  const [teamFilter, setTeamFilter] = useState<'all' | 'active'>('active')

  useEffect(() => {
    fetchData()
  }, [timeRange, customStartDate, customEndDate, teamFilter])

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token')
      const headers = { Authorization: `Bearer ${token}` }
      
      // Загружаем пользователей, задачи и проекты
      const [usersRes, tasksRes, digitalProjectsRes, projectsRes] = await Promise.all([
        fetch(`${API_URL}/users/`, { headers }),
        fetch(`${API_URL}/tasks/`, { headers }),
        fetch(`${API_URL}/digital/projects`, { headers }),
        fetch(`${API_URL}/projects/`, { headers })
      ])
      
      const usersData = usersRes.ok ? await usersRes.json() : []
      const tasksData = tasksRes.ok ? await tasksRes.json() : []
      const digitalProjects = digitalProjectsRes.ok ? await digitalProjectsRes.json() : []
      const projectsData = projectsRes.ok ? await projectsRes.json() : []
      
      // Загружаем задачи из Digital проектов
      const digitalTasksPromises = digitalProjects.map(async (project: any) => {
        try {
          const tasksRes = await fetch(`${API_URL}/digital/projects/${project.id}/tasks`, { headers })
          if (tasksRes.ok) {
            const projectTasks = await tasksRes.json()
            return projectTasks.map((task: any) => ({
              ...task,
              executor_id: project.executor_id,
              project_name: project.project_name,
              service_name: project.service_name
            }))
          }
          return []
        } catch {
          return []
        }
      })
      
      const digitalTasksArrays = await Promise.all(digitalTasksPromises)
      const digitalTasksData = digitalTasksArrays.flat()
      
      setUsers(usersData)
      setTasks(tasksData)
      setDigitalTasks(digitalTasksData)
      
      // Вычисляем аналитику
      const analyticsData = calculateAnalytics(usersData, tasksData, digitalTasksData, projectsData)
      setData(analyticsData)
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setLoading(false)
    }
  }

  const calculateAnalytics = (users: User[], tasks: Task[], digitalTasks: any[], projects: any[]): AnalyticsData => {
    const allTasks = [...tasks, ...digitalTasks]
    
    // Фильтруем задачи по времени
    const filteredTasks = filterTasksByTimeRange(allTasks)
    const previousPeriodTasks = filterTasksByPreviousPeriod(allTasks)
    
    // Статистика задач
    const completedTasks = filteredTasks.filter(t => t.status === 'done' || t.status === 'completed')
    const inProgressTasks = filteredTasks.filter(t => t.status !== 'done' && t.status !== 'completed')
    const overdueTasks = filteredTasks.filter(t => t.deadline && new Date(t.deadline) < new Date() && t.status !== 'done' && t.status !== 'completed')
    
    // Статистика за предыдущий период для трендов
    const previousCompletedTasks = previousPeriodTasks.filter(t => t.status === 'done' || t.status === 'completed')
    const previousOverdueTasks = previousPeriodTasks.filter(t => t.deadline && new Date(t.deadline) < new Date() && t.status !== 'done' && t.status !== 'completed')
    
    // Задачи по типам (по ролям исполнителей) - используем все задачи
    const tasksByRole = calculateTasksByRole(users, tasks, digitalTasks)
    
    // Производительность команды
    const teamProductivity = calculateTeamProductivity(users, allTasks)
    
    // Динамика задач по периодам
    const tasksByPeriod = calculateTasksByPeriod(allTasks)
    
    // Расчет трендов
    const totalTrend = calculateTrend(filteredTasks.length, previousPeriodTasks.length)
    const completedTrend = calculateTrend(completedTasks.length, previousCompletedTasks.length)
    const overdueTrend = calculateTrend(overdueTasks.length, previousOverdueTasks.length)
    
    return {
      tasksStats: {
        total: filteredTasks.length,
        completed: completedTasks.length,
        inProgress: inProgressTasks.length,
        overdue: overdueTasks.length,
        totalTrend,
        completedTrend,
        overdueTrend
      },
      projectsStats: {
        total: projects.length,
        active: projects.length,
        completed: 0
      },
      teamProductivity,
      tasksByPeriod,
      tasksByType: tasksByRole
    }
  }
  
  const filterTasksByTimeRange = (tasks: Task[]) => {
    const now = new Date()
    let startDate: Date
    let endDate: Date = now
    
    if (timeRange === 'custom') {
      if (!customStartDate || !customEndDate) return tasks
      startDate = new Date(customStartDate)
      endDate = new Date(customEndDate)
    } else {
      switch (timeRange) {
        case 'week':
          startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
          break
        case 'month':
          startDate = new Date(now.getFullYear(), now.getMonth(), 1)
          break
        case 'year':
          startDate = new Date(now.getFullYear(), 0, 1)
          break
        default:
          return tasks
      }
    }
    
    return tasks.filter(task => {
      const taskDate = new Date(task.created_at)
      return taskDate >= startDate && taskDate <= endDate
    })
  }

  const filterTasksByPreviousPeriod = (tasks: Task[]) => {
    const now = new Date()
    let startDate: Date
    let endDate: Date
    
    if (timeRange === 'custom') {
      if (!customStartDate || !customEndDate) return []
      const currentStart = new Date(customStartDate)
      const currentEnd = new Date(customEndDate)
      const periodLength = currentEnd.getTime() - currentStart.getTime()
      endDate = new Date(currentStart.getTime() - 24 * 60 * 60 * 1000) // День до начала текущего периода
      startDate = new Date(endDate.getTime() - periodLength)
    } else {
      switch (timeRange) {
        case 'week':
          endDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
          startDate = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000)
          break
        case 'month':
          endDate = new Date(now.getFullYear(), now.getMonth(), 0) // Последний день предыдущего месяца
          startDate = new Date(now.getFullYear(), now.getMonth() - 1, 1) // Первый день предыдущего месяца
          break
        case 'year':
          endDate = new Date(now.getFullYear() - 1, 11, 31) // 31 декабря предыдущего года
          startDate = new Date(now.getFullYear() - 1, 0, 1) // 1 января предыдущего года
          break
        default:
          return []
      }
    }
    
    return tasks.filter(task => {
      const taskDate = new Date(task.created_at)
      return taskDate >= startDate && taskDate <= endDate
    })
  }

  const calculateTrend = (currentValue: number, previousValue: number): number => {
    if (previousValue === 0) {
      return currentValue > 0 ? 100 : 0
    }
    return Math.round(((currentValue - previousValue) / previousValue) * 100)
  }
  
  const calculateTasksByRole = (users: User[], tasks: Task[], digitalTasks: any[]) => {
    const roleCategories = {
      'Дизайн-задачи': ['designer'],
      'Digital-задачи': [], // Digital задачи определяются по источнику
      'СММ-задачи': ['smm_manager'],
      'Админ-задачи': ['admin']
    }
    
    const result = Object.entries(roleCategories).map(([categoryName, roles]) => {
      let count = 0
      
      if (categoryName === 'Digital-задачи') {
        // Считаем все Digital задачи
        count = digitalTasks.length
      } else {
        // Считаем все задачи по ролям исполнителей
        count = tasks.filter(task => {
          const executor = users.find(u => u.id === task.executor_id)
          return executor && roles.includes(executor.role)
        }).length
      }
      
      const colors = {
        'Дизайн-задачи': '#8B5CF6',
        'Digital-задачи': '#06B6D4', 
        'СММ-задачи': '#10B981',
        'Админ-задачи': '#F59E0B'
      }
      
      return {
        name: categoryName,
        value: count,
        color: colors[categoryName as keyof typeof colors]
      }
    })
    
    return result
  }
  
  const calculateTeamProductivity = (users: User[], allTasks: Task[]) => {
    // Фильтруем пользователей в зависимости от выбранного фильтра
    const filteredUsers = teamFilter === 'active' 
      ? users.filter(user => user.role !== 'inactive') 
      : users

    return filteredUsers.map(user => {
      const userTasks = allTasks.filter(t => t.executor_id === user.id)
      const completedTasks = userTasks.filter(t => t.status === 'done' || t.status === 'completed')
      
      return {
        name: user.name,
        tasksAssigned: userTasks.length, // Общее количество задач
        tasksCompleted: completedTasks.length, // Завершенные задачи
        efficiency: userTasks.length > 0 ? Math.round((completedTasks.length / userTasks.length) * 100) : 0
      }
    })
  }
  
  const calculateTasksByPeriod = (allTasks: Task[]) => {
    const now = new Date()
    let periods: any[] = []
    
    if (timeRange === 'week') {
      // Находим понедельник текущей недели
      const today = new Date(now)
      const dayOfWeek = today.getDay() // 0 = воскресенье, 1 = понедельник, ..., 6 = суббота
      const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek // Если воскресенье, то -6, иначе 1 - dayOfWeek
      const monday = new Date(today.getTime() + mondayOffset * 24 * 60 * 60 * 1000)
      
      // Группируем по дням с понедельника по воскресенье
      for (let i = 0; i < 7; i++) {
        const date = new Date(monday.getTime() + i * 24 * 60 * 60 * 1000)
        const dayName = date.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric' })
        const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate())
        const dayEnd = new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59)
        
        const created = allTasks.filter(t => {
          const taskDate = new Date(t.created_at)
          return taskDate >= dayStart && taskDate <= dayEnd
        }).length
        
        const completed = allTasks.filter(t => {
          if (!t.finished_at) return false
          const finishedDate = new Date(t.finished_at)
          return finishedDate >= dayStart && finishedDate <= dayEnd
        }).length
        
        periods.push({ period: dayName, created, completed })
      }
    } else if (timeRange === 'year') {
      // Группируем по месяцам с января по декабрь текущего года
      for (let month = 0; month < 12; month++) {
        const date = new Date(now.getFullYear(), month, 1)
        const monthName = date.toLocaleDateString('ru-RU', { month: 'short' })
        const monthStart = new Date(date.getFullYear(), date.getMonth(), 1)
        const monthEnd = new Date(date.getFullYear(), date.getMonth() + 1, 0)
        
        const created = allTasks.filter(t => {
          const taskDate = new Date(t.created_at)
          return taskDate >= monthStart && taskDate <= monthEnd
        }).length
        
        const completed = allTasks.filter(t => {
          if (!t.finished_at) return false
          const finishedDate = new Date(t.finished_at)
          return finishedDate >= monthStart && finishedDate <= monthEnd
        }).length
        
        periods.push({ period: monthName, created, completed })
      }
    } else if (timeRange === 'custom' && customStartDate && customEndDate) {
      // Группируем по дням в произвольном периоде
      const startDate = new Date(customStartDate)
      const endDate = new Date(customEndDate)
      const diffTime = Math.abs(endDate.getTime() - startDate.getTime())
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
      
      for (let i = 0; i <= diffDays; i++) {
        const date = new Date(startDate.getTime() + i * 24 * 60 * 60 * 1000)
        const dayName = date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
        const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate())
        const dayEnd = new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59)
        
        const created = allTasks.filter(t => {
          const taskDate = new Date(t.created_at)
          return taskDate >= dayStart && taskDate <= dayEnd
        }).length
        
        const completed = allTasks.filter(t => {
          if (!t.finished_at) return false
          const finishedDate = new Date(t.finished_at)
          return finishedDate >= dayStart && finishedDate <= dayEnd
        }).length
        
        periods.push({ period: dayName, created, completed })
      }
    } else {
      // По умолчанию - группируем по дням за текущий месяц
      const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)
      const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0)
      
      for (let day = 1; day <= monthEnd.getDate(); day++) {
        const date = new Date(now.getFullYear(), now.getMonth(), day)
        const dayName = day.toString()
        const dayStart = new Date(date.getFullYear(), date.getMonth(), date.getDate())
        const dayEnd = new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59)
        
        const created = allTasks.filter(t => {
          const taskDate = new Date(t.created_at)
          return taskDate >= dayStart && taskDate <= dayEnd
        }).length
        
        const completed = allTasks.filter(t => {
          if (!t.finished_at) return false
          const finishedDate = new Date(t.finished_at)
          return finishedDate >= dayStart && finishedDate <= dayEnd
        }).length
        
        periods.push({ period: dayName, created, completed })
      }
    }
    
    return periods
  }

  const displayData = data || {
    tasksStats: { 
      total: 0, 
      completed: 0, 
      inProgress: 0, 
      overdue: 0,
      totalTrend: 0,
      completedTrend: 0,
      overdueTrend: 0
    },
    projectsStats: { total: 0, active: 0, completed: 0 },
    teamProductivity: [],
    tasksByPeriod: [],
    tasksByType: []
  }

  const getPeriodName = () => {
    switch (timeRange) {
      case 'week':
        return 'предыдущей недели'
      case 'month':
        return 'предыдущего месяца'
      case 'year':
        return 'предыдущего года'
      case 'custom':
        return 'предыдущего периода'
      default:
        return 'предыдущего периода'
    }
  }

  const StatCard = ({ title, value, icon: Icon, trend, color }: any) => (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {trend !== undefined && trend !== null && (
            <p className={`text-sm mt-1 flex items-center ${trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-gray-600'}`}>
              <TrendingUp className="w-4 h-4 mr-1" />
              {trend === 0 ? '0' : `${trend > 0 ? '+' : ''}${trend}`}% от {getPeriodName()}
            </p>
          )}
        </div>
        <div className={`p-3 rounded-full ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  )

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-gray-200 h-32 rounded-xl"></div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-gray-200 h-80 rounded-xl"></div>
            <div className="bg-gray-200 h-80 rounded-xl"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-7xl mx-auto bg-gray-50 min-h-screen">
      {/* Заголовок */}
      <div className="mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Аналитика</h1>
            <p className="text-gray-600 mt-1">Обзор производительности и статистики</p>
          </div>
          <div className="mt-4 sm:mt-0">
            <div className="flex flex-col sm:flex-row gap-2">
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="border border-gray-300 rounded-lg px-4 py-2 bg-white shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="week">Неделя</option>
                <option value="month">Месяц</option>
                <option value="year">Год</option>
                <option value="custom">Произвольный период</option>
              </select>
              
              {timeRange === 'custom' && (
                <div className="flex gap-2">
                  <input
                    type="date"
                    value={customStartDate}
                    onChange={(e) => setCustomStartDate(e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-2 bg-white shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Начало"
                  />
                  <input
                    type="date"
                    value={customEndDate}
                    onChange={(e) => setCustomEndDate(e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-2 bg-white shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Конец"
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Статистические карточки */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Всего задач"
          value={displayData.tasksStats.total}
          icon={CheckSquare}
          trend={displayData.tasksStats.totalTrend}
          color="bg-blue-500"
        />
        <StatCard
          title="Завершено задач"
          value={displayData.tasksStats.completed}
          icon={Target}
          trend={displayData.tasksStats.completedTrend}
          color="bg-green-500"
        />
        <StatCard
          title="Активных проектов"
          value={displayData.projectsStats.active}
          icon={Activity}
          trend={null}
          color="bg-purple-500"
        />
        <StatCard
          title="Просроченных задач"
          value={displayData.tasksStats.overdue}
          icon={Clock}
          trend={displayData.tasksStats.overdueTrend}
          color="bg-red-500"
        />
      </div>

      {/* Графики */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* График задач по месяцам */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Динамика задач</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={displayData?.tasksByPeriod || []}>
              <defs>
                <linearGradient id="colorCreated" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
              <XAxis dataKey="period" stroke="#6B7280" />
              <YAxis stroke="#6B7280" />
              <Tooltip 
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #E5E7EB',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                }}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="created"
                stroke="#3B82F6"
                fillOpacity={1}
                fill="url(#colorCreated)"
                name="Создано"
              />
              <Area
                type="monotone"
                dataKey="completed"
                stroke="#10B981"
                fillOpacity={1}
                fill="url(#colorCompleted)"
                name="Завершено"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Круговая диаграмма типов задач */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Задачи по типам</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={displayData?.tasksByType || []}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                dataKey="value"
              >
                {(displayData?.tasksByType || []).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #E5E7EB',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                }}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Производительность команды */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900">Производительность команды</h3>
          <div className="mt-2 sm:mt-0">
            <select
              value={teamFilter}
              onChange={(e) => setTeamFilter(e.target.value as 'all' | 'active')}
              className="border border-gray-300 rounded-lg px-4 py-2 bg-white shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            >
              <option value="active">Производительность текущей команды</option>
              <option value="all">Производительность всех работников 8BIT</option>
            </select>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={displayData?.teamProductivity || []}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis dataKey="name" stroke="#6B7280" />
            <YAxis stroke="#6B7280" />
            <Tooltip 
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #E5E7EB',
                borderRadius: '8px',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            />
            <Legend />
            <Bar 
              dataKey="tasksAssigned" 
              fill="#3B82F6" 
              name="Общее количество задач"
              radius={[4, 4, 0, 0]}
            />
            <Bar 
              dataKey="tasksCompleted" 
              fill="#10B981" 
              name="Завершено задач"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default Analytics