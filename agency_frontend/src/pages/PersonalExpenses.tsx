import { useEffect, useState } from 'react'
import { API_URL } from '../api'
import { isAdmin } from '../utils/roleUtils'

function formatInput(value: string) {
  const digits = value.replace(/\D/g, '')
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

function parseNumber(value: string) {
  return parseFloat(value.replace(/[^0-9.,]/g, '').replace(/\s+/g, '').replace(',', '.')) || 0
}

interface EmployeeExpense {
  id: number
  name: string
  amount: number
  description?: string
  date?: string
  project_id?: number
  project?: {
    id: number
    name: string
  }
  created_at: string
}

interface CommonExpense {
  id: number
  category_id?: number
  name: string
  amount: number
  description?: string
  date?: string
  created_at: string
  creator_name?: string
}

interface Project {
  id: number
  name: string
  logo?: string
}


function PersonalExpenses() {
  const [tab, setTab] = useState<'personal' | 'company'>('personal')
  const [expenses, setExpenses] = useState<EmployeeExpense[]>([])
  const [companyExpenses, setCompanyExpenses] = useState<CommonExpense[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<EmployeeExpense | CommonExpense | null>(null)
  const [name, setName] = useState('')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [date, setDate] = useState('')
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null)
  
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role')
  const userIsAdmin = isAdmin(role)

  const loadExpenses = async () => {
    if (!token) {
      setExpenses([])
      return
    }

    try {
      const res = await fetch(`${API_URL}/employee-expenses/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setExpenses(Array.isArray(data) ? data : [])
      } else {
        setExpenses([])
      }
    } catch (error) {
      setExpenses([])
    }
  }

  const loadCompanyExpenses = async () => {
    if (!token || !userIsAdmin) {
      setCompanyExpenses([])
      return
    }

    try {
      const res = await fetch(`${API_URL}/common-expenses/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setCompanyExpenses(Array.isArray(data) ? data : [])
      } else {
        setCompanyExpenses([])
      }
    } catch (error) {
      setCompanyExpenses([])
    }
  }

  const loadProjects = async () => {
    if (!token) {
      setProjects([])
      return
    }

    try {
      const res = await fetch(`${API_URL}/projects/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setProjects(Array.isArray(data) ? data : [])
      } else {
        setProjects([])
      }
    } catch (error) {
      setProjects([])
    }
  }


  useEffect(() => {
    loadExpenses()
    loadProjects()
    if (userIsAdmin) {
      loadCompanyExpenses()
    }
  }, [])

  const openAddModal = () => {
    setEditing(null)
    setName('')
    setAmount('')
    setDescription('')
    setDate(new Date().toISOString().split('T')[0]) // Default to today
    setSelectedProjectId(null)
    setShowModal(true)
  }

  const openEditModal = (expense: EmployeeExpense | CommonExpense) => {
    setEditing(expense)
    setName(expense.name)
    setAmount(formatInput(String(expense.amount || 0)))
    setDescription(expense.description || '')
    setDate(expense.date || '')
    if ('project_id' in expense) {
      setSelectedProjectId(expense.project_id || null)
    } else {
      setSelectedProjectId(null)
    }
    setShowModal(true)
  }

  const saveExpense = async () => {
    if (!name || !amount) return

    const isCompanyExpense = tab === 'company'
    const payload: any = {
      name,
      amount: parseNumber(amount),
      description: description || null,
      date: date || null
    }

    if (isCompanyExpense) {
      payload.category_id = null
    } else {
      // Only add project_id for personal expenses
      payload.project_id = selectedProjectId
    }

    const endpoint = isCompanyExpense ? 'common-expenses' : 'employee-expenses'

    try {
      if (editing) {
        await fetch(`${API_URL}/${endpoint}/${editing.id}`, {
          method: 'PUT',
          headers: { 
            'Content-Type': 'application/json', 
            Authorization: `Bearer ${token}` 
          },
          body: JSON.stringify(payload),
        })
      } else {
        await fetch(`${API_URL}/${endpoint}/`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json', 
            Authorization: `Bearer ${token}` 
          },
          body: JSON.stringify(payload),
        })
      }
      setShowModal(false)
      if (isCompanyExpense) {
        loadCompanyExpenses()
      } else {
        loadExpenses()
      }
    } catch (error) {
      console.error('Error saving expense:', error)
    }
  }

  const deleteExpense = async (id: number) => {
    if (!confirm('Вы уверены, что хотите удалить этот расход?')) return

    const isCompanyExpense = tab === 'company'
    const endpoint = isCompanyExpense ? 'common-expenses' : 'employee-expenses'

    try {
      await fetch(`${API_URL}/${endpoint}/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (isCompanyExpense) {
        loadCompanyExpenses()
      } else {
        loadExpenses()
      }
    } catch (error) {
      console.error('Error deleting expense:', error)
    }
  }

  const currentExpenses = tab === 'company' ? companyExpenses : expenses
  const totalAmount = currentExpenses.reduce((sum, expense) => sum + expense.amount, 0)

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="pt-8 pb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-light text-gray-900">Мои расходы</h1>
              <p className="text-sm text-gray-500 mt-1">
                {userIsAdmin ? 'Личные и корпоративные расходы' : 'Личные расходы'}
              </p>
            </div>
            <button 
              className="inline-flex items-center px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 shadow-sm"
              onClick={openAddModal}
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4v16m8-8H4" />
              </svg>
              Добавить расход
            </button>
          </div>
        </div>

        {/* Admin Tabs */}
        {userIsAdmin && (
          <div className="mb-8">
            <div className="bg-white rounded-lg p-1 shadow-sm border border-gray-200 inline-flex">
              <button
                onClick={() => setTab('personal')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                  tab === 'personal'
                    ? 'bg-gray-900 text-white shadow-sm'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                Личные
              </button>
              <button
                onClick={() => setTab('company')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                  tab === 'company'
                    ? 'bg-gray-900 text-white shadow-sm'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
              >
                Компания
              </button>
            </div>
          </div>
        )}

        {/* Summary Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">Общая сумма</p>
              <p className="text-2xl font-light text-gray-900 mt-1">{totalAmount.toLocaleString('ru-RU')} <span className="text-lg text-gray-500">сум</span></p>
            </div>
            <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center">
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
              </svg>
            </div>
          </div>
        </div>

        {/* Expenses Table */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="text-lg font-medium text-gray-900">Расходы</h2>
          </div>
          
          {currentExpenses.length === 0 ? (
            <div className="text-center py-16 px-6">
              <div className="w-16 h-16 bg-gray-100 rounded-full mx-auto flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-sm font-medium text-gray-900 mb-1">Нет расходов</h3>
              <p className="text-sm text-gray-500">Начните добавлять расходы для отслеживания финансов</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="px-6 py-3 text-left text-sm font-medium text-gray-900">
                      Наименование
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-medium text-gray-900">
                      Сумма
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-medium text-gray-900">
                      Дата
                    </th>
                    {tab === 'personal' && (
                      <th className="px-6 py-3 text-left text-sm font-medium text-gray-900">
                        Проект
                      </th>
                    )}
                    <th className="px-6 py-3 text-left text-sm font-medium text-gray-900">
                      Комментарий
                    </th>
                    <th className="px-6 py-3 text-right text-sm font-medium text-gray-900">
                      Действия
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {currentExpenses.map((expense) => (
                    <tr key={expense.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors duration-150">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{expense.name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 font-semibold">
                          {expense.amount.toLocaleString('ru-RU')} сум
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {expense.date ? new Date(expense.date).toLocaleDateString('ru-RU') : '-'}
                        </div>
                      </td>
                      {tab === 'personal' && (
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {expense.project ? expense.project.name : '-'}
                          </div>
                        </td>
                      )}
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900 max-w-xs truncate">
                          {expense.description || '-'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex justify-end space-x-2">
                          <button
                            onClick={() => openEditModal(expense)}
                            className="p-1.5 text-gray-400 hover:text-gray-600 transition-colors duration-150"
                            title="Редактировать"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => deleteExpense(expense.id)}
                            className="p-1.5 text-gray-400 hover:text-red-500 transition-colors duration-150"
                            title="Удалить"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-medium text-gray-900">
                {editing ? 'Редактировать расход' : 'Новый расход'}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Наименование
                </label>
                <input 
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all duration-200 bg-gray-50 focus:bg-white" 
                  placeholder="Например: Обед, Транспорт, Канцелярия" 
                  value={name} 
                  onChange={e => setName(e.target.value)} 
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Сумма
                </label>
                <div className="relative">
                  <input 
                    className="w-full px-4 py-3 pr-12 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all duration-200 bg-gray-50 focus:bg-white" 
                    placeholder="100 000" 
                    value={amount} 
                    onChange={e => setAmount(formatInput(e.target.value))} 
                  />
                  <span className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 text-sm">
                    сум
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Дата
                </label>
                <input
                  type="date"
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all duration-200 bg-gray-50 focus:bg-white"
                  value={date}
                  onChange={e => setDate(e.target.value)}
                />
              </div>

              {tab === 'personal' && (
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Проект (опционально)
                  </label>
                  <select
                    className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all duration-200 bg-gray-50 focus:bg-white"
                    value={selectedProjectId || ''}
                    onChange={e => setSelectedProjectId(e.target.value ? Number(e.target.value) : null)}
                  >
                    <option value="">Без привязки к проекту</option>
                    {projects.map(project => (
                      <option key={project.id} value={project.id}>
                        {project.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-900 mb-2">
                  Комментарий
                </label>
                <textarea 
                  className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:ring-2 focus:ring-gray-900 focus:border-transparent transition-all duration-200 bg-gray-50 focus:bg-white resize-none" 
                  placeholder="Дополнительная информация о расходе" 
                  rows={3}
                  value={description} 
                  onChange={e => setDescription(e.target.value)} 
                />
              </div>
            </div>

            <div className="flex gap-3 mt-8 pt-6 border-t border-gray-100">
              <button 
                className="flex-1 px-4 py-3 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium transition-all duration-200"
                onClick={() => setShowModal(false)}
              >
                Отмена
              </button>
              <button 
                className="flex-1 px-4 py-3 bg-gray-900 hover:bg-gray-800 text-white rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={saveExpense}
                disabled={!name || !amount}
              >
                {editing ? 'Сохранить' : 'Добавить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PersonalExpenses