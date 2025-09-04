import { useEffect, useState } from 'react'
import { API_URL } from '../api'

interface ProjectExpense {
  id: number
  project_id: number
  project_name: string
  category_id?: number
  category_name?: string
  name: string
  amount: number
  description?: string
  date: string
  created_at: string
  created_by?: number
  creator_name?: string
}

interface Project {
  id: number
  name: string
}

interface Category {
  id: number
  name: string
}

function ProjectExpenses() {
  const [expenses, setExpenses] = useState<ProjectExpense[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  
  // Filters
  const [selectedProject, setSelectedProject] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  const token = localStorage.getItem('token')

  const formatCurrency = (amount: number) => {
    return amount.toLocaleString('ru-RU') + ' сум'
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU')
  }

  const loadExpenses = async () => {
    if (!token) return

    setLoading(true)
    
    try {
      // Build query parameters
      const params = new URLSearchParams()
      if (selectedProject) params.append('project_id', selectedProject)
      if (selectedCategory) params.append('category_id', selectedCategory)
      if (startDate) params.append('start_date', startDate)
      if (endDate) params.append('end_date', endDate)
      params.append('limit', '1000') // Get more records

      const response = await fetch(`${API_URL}/project-expenses/detailed?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      
      if (response.ok) {
        const data = await response.json()
        setExpenses(data)
      } else {
        console.error('Failed to load expenses')
        setExpenses([])
      }
    } catch (error) {
      console.error('Error loading expenses:', error)
      setExpenses([])
    } finally {
      setLoading(false)
    }
  }

  const loadProjects = async () => {
    if (!token) return

    try {
      const response = await fetch(`${API_URL}/projects/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      
      if (response.ok) {
        const data = await response.json()
        setProjects(data)
      }
    } catch (error) {
      console.error('Error loading projects:', error)
    }
  }

  const loadCategories = async () => {
    if (!token) return

    try {
      const response = await fetch(`${API_URL}/expense-categories/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      
      if (response.ok) {
        const data = await response.json()
        setCategories(data)
      }
    } catch (error) {
      console.error('Error loading categories:', error)
    }
  }

  useEffect(() => {
    loadProjects()
    loadCategories()
  }, [token])

  useEffect(() => {
    loadExpenses()
  }, [token, selectedProject, selectedCategory, startDate, endDate])

  const totalAmount = expenses.reduce((sum, expense) => sum + expense.amount, 0)

  if (!token) {
    return <div className="p-4">Необходимо войти в систему</div>
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Расходы по проектам</h1>
      
      {/* Filters */}
      <div className="mb-4 grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Проект</label>
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="border rounded px-3 py-2 w-full"
          >
            <option value="">Все проекты</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Категория</label>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="border rounded px-3 py-2 w-full"
          >
            <option value="">Все категории</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Начальная дата</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="border rounded px-3 py-2 w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Конечная дата</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="border rounded px-3 py-2 w-full"
          />
        </div>
      </div>

      {/* Summary */}
      <div className="mb-4 p-4 bg-gray-100 rounded">
        <div className="text-lg font-semibold">
          Общая сумма расходов: {formatCurrency(totalAmount)}
        </div>
        <div className="text-sm text-gray-600">
          Всего записей: {expenses.length}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center py-4">Загрузка...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse border">
            <thead>
              <tr className="bg-gray-50">
                <th className="border px-4 py-2 text-left">Дата</th>
                <th className="border px-4 py-2 text-left">Проект</th>
                <th className="border px-4 py-2 text-left">Название</th>
                <th className="border px-4 py-2 text-left">Категория</th>
                <th className="border px-4 py-2 text-right">Сумма</th>
                <th className="border px-4 py-2 text-left">Описание</th>
                <th className="border px-4 py-2 text-left">Создал</th>
              </tr>
            </thead>
            <tbody>
              {expenses.length === 0 ? (
                <tr>
                  <td colSpan={7} className="border px-4 py-2 text-center text-gray-500">
                    Расходы не найдены
                  </td>
                </tr>
              ) : (
                expenses.map((expense) => (
                  <tr key={expense.id} className="hover:bg-gray-50">
                    <td className="border px-4 py-2">
                      {formatDate(expense.date)}
                    </td>
                    <td className="border px-4 py-2">
                      <span className="font-medium text-blue-600">
                        {expense.project_name}
                      </span>
                    </td>
                    <td className="border px-4 py-2">
                      {expense.name}
                    </td>
                    <td className="border px-4 py-2">
                      <span className="text-sm bg-gray-200 px-2 py-1 rounded">
                        {expense.category_name || 'Без категории'}
                      </span>
                    </td>
                    <td className="border px-4 py-2 text-right font-semibold">
                      {formatCurrency(expense.amount)}
                    </td>
                    <td className="border px-4 py-2 text-sm text-gray-600 max-w-xs">
                      {expense.description && (
                        <div className="truncate" title={expense.description}>
                          {expense.description}
                        </div>
                      )}
                    </td>
                    <td className="border px-4 py-2 text-sm">
                      {expense.creator_name || 'Неизвестно'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default ProjectExpenses