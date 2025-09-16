import { useState, useEffect } from 'react'
import { API_URL } from '../api'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts'
import { Users, TrendingUp, Award, Activity, Target } from 'lucide-react'

interface ServiceTypeData {
  service_type: string
  created: number
  completed: number
  efficiency: number
}

interface EmployeeServiceAnalytics {
  employee_id: number
  employee_name: string
  service_types: ServiceTypeData[]
  total_created: number
  total_completed: number
  overall_efficiency: number
}

interface ServiceTypesAnalytics {
  employees: EmployeeServiceAnalytics[]
  period_start: string
  period_end: string
  total_service_types: string[]
}

function ServiceTypesAnalytics() {
  const [analytics, setAnalytics] = useState<ServiceTypesAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [selectedEmployee, setSelectedEmployee] = useState<number | null>(null)
  const [users, setUsers] = useState<Array<{id: number, name: string}>>([])

  useEffect(() => {
    loadUsers()

    // Устанавливаем текущий месяц по умолчанию
    const now = new Date()
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1)
    setStartDate(firstDay.toISOString().split('T')[0])
    setEndDate(now.toISOString().split('T')[0])
  }, [])

  useEffect(() => {
    loadAnalytics()
  }, [startDate, endDate, selectedEmployee])

  const loadUsers = async () => {
    const token = localStorage.getItem('token')
    try {
      const response = await fetch(`${API_URL}/users/`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setUsers(data.filter((user: any) => user.is_active && user.role !== 'admin'))
      }
    } catch (error) {
      console.error('Error loading users:', error)
    }
  }

  const loadAnalytics = async () => {
    if (!startDate || !endDate) return

    const token = localStorage.getItem('token')
    setLoading(true)

    try {
      const params = new URLSearchParams()
      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)
      if (selectedEmployee) params.append('employee_id', selectedEmployee.toString())

      const response = await fetch(`${API_URL}/analytics/service-types?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` }
      })

      if (response.ok) {
        const data = await response.json()
        setAnalytics(data)
      }
    } catch (error) {
      console.error('Error loading analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  // Подготавливаем данные для общей гистограммы
  const prepareChartData = () => {
    if (!analytics) return []

    const serviceTypeMap: Record<string, { created: number; completed: number }> = {}

    analytics.employees.forEach(emp => {
      emp.service_types.forEach(service => {
        if (!serviceTypeMap[service.service_type]) {
          serviceTypeMap[service.service_type] = { created: 0, completed: 0 }
        }
        serviceTypeMap[service.service_type].created += service.created
        serviceTypeMap[service.service_type].completed += service.completed
      })
    })

    return Object.entries(serviceTypeMap).map(([type, data]) => ({
      service_type: type,
      Создано: data.created,
      Завершено: data.completed,
      Эффективность: data.created > 0 ? Math.round((data.completed / data.created) * 100) : 0
    }))
  }

  // Подготавливаем данные для pie chart эффективности
  const prepareEfficiencyData = () => {
    if (!analytics || analytics.employees.length === 0) return []

    return analytics.employees.map(emp => ({
      name: emp.employee_name,
      efficiency: emp.overall_efficiency,
      created: emp.total_created,
      completed: emp.total_completed
    }))
  }

  const chartData = prepareChartData()
  const efficiencyData = prepareEfficiencyData()

  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#8dd1e1', '#d084d0']

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Загрузка аналитики...</div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Аналитика по типам услуг
        </h1>
        <p className="text-gray-600">
          Анализ созданных и завершенных задач по типам услуг для каждого сотрудника
        </p>
      </div>

      {/* Фильтры */}
      <div className="bg-white p-4 rounded-lg shadow mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Период:</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-2 border rounded-lg text-sm"
            />
            <span className="text-gray-500">—</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-2 border rounded-lg text-sm"
            />
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Сотрудник:</label>
            <select
              value={selectedEmployee || ''}
              onChange={(e) => setSelectedEmployee(e.target.value ? parseInt(e.target.value) : null)}
              className="px-3 py-2 border rounded-lg text-sm"
            >
              <option value="">Все сотрудники</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>{user.name}</option>
              ))}
            </select>
          </div>

          {(startDate || endDate || selectedEmployee) && (
            <button
              onClick={() => {
                setStartDate('')
                setEndDate('')
                setSelectedEmployee(null)
              }}
              className="text-red-600 hover:text-red-800 px-2 py-1 text-sm"
            >
              Очистить фильтры
            </button>
          )}
        </div>
      </div>

      {analytics && (
        <>
          {/* Общая статистика */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Users className="h-6 w-6 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Активных сотрудников</p>
                  <p className="text-2xl font-bold text-gray-900">{analytics.employees.length}</p>
                </div>
              </div>
            </div>

            <div className="bg-white p-4 rounded-lg shadow">
              <div className="flex items-center">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Activity className="h-6 w-6 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Типов услуг</p>
                  <p className="text-2xl font-bold text-gray-900">{analytics.total_service_types.length}</p>
                </div>
              </div>
            </div>

            <div className="bg-white p-4 rounded-lg shadow">
              <div className="flex items-center">
                <div className="p-2 bg-yellow-100 rounded-lg">
                  <Target className="h-6 w-6 text-yellow-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Всего создано</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {analytics.employees.reduce((sum, emp) => sum + emp.total_created, 0)}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white p-4 rounded-lg shadow">
              <div className="flex items-center">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Award className="h-6 w-6 text-purple-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Всего завершено</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {analytics.employees.reduce((sum, emp) => sum + emp.total_completed, 0)}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Основная гистограмма */}
          <div className="bg-white p-6 rounded-lg shadow mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Статистика по типам услуг
            </h2>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="service_type"
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="Создано" fill="#8884d8" name="Создано" />
                  <Bar dataKey="Завершено" fill="#82ca9d" name="Завершено" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Эффективность сотрудников */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Эффективность сотрудников
              </h2>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={efficiencyData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, efficiency }) => `${name}: ${efficiency}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="efficiency"
                    >
                      {efficiencyData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Детальная статистика по сотрудникам */}
            <div className="bg-white p-6 rounded-lg shadow">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Детальная статистика
              </h2>
              <div className="space-y-4 max-h-80 overflow-y-auto">
                {analytics.employees.map((employee) => (
                  <div key={employee.employee_id} className="border-l-4 border-blue-500 pl-4">
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="font-semibold text-gray-900">{employee.employee_name}</h3>
                      <span className="text-sm text-gray-600">
                        {employee.overall_efficiency}% эффективность
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 mb-2">
                      Создано: {employee.total_created} | Завершено: {employee.total_completed}
                    </div>
                    <div className="space-y-1">
                      {employee.service_types.map((service) => (
                        <div key={service.service_type} className="flex justify-between text-xs">
                          <span className="text-gray-700">{service.service_type}:</span>
                          <span className="text-gray-600">
                            {service.created}/{service.completed} ({service.efficiency}%)
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default ServiceTypesAnalytics