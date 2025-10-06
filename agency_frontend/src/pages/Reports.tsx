import { useEffect, useState } from 'react'
import { API_URL } from '../api'
import EmployeeReport from './EmployeeReport'

const MONTH_NAMES = [
  'Январь',
  'Февраль',
  'Март',
  'Апрель',
  'Май',
  'Июнь',
  'Июль',
  'Август',
  'Сентябрь',
  'Октябрь',
  'Ноябрь',
  'Декабрь',
]

interface Project { id: number; name: string; logo?: string }
interface Expense { id: number; name: string; amount: number; comment?: string }
interface Receipt { id: number; name: string; amount: number; comment?: string }
interface ClientExpense { id: number; name: string; amount: number; comment?: string }

interface Report {
  project_id: number
  contract_amount: number
  receipts: number
  total_expenses: number
  debt: number
  expenses: Expense[]
  receipts_list: Receipt[]
  client_expenses: ClientExpense[]
}

function formatCurrency(n: number) {
  return n.toLocaleString('ru-RU') + ' сум'
}

function formatInput(value: string) {
  const digits = value.replace(/\D/g, '')
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

function parseNumber(value: string) {
  return parseFloat(value.replace(/[^0-9.,]/g, '').replace(/\s+/g, '').replace(',', '.')) || 0
}

function Reports() {
  const token = localStorage.getItem('token')
  
  // Получаем сохраненную вкладку из localStorage или используем 'projects' по умолчанию
  const getSavedSection = () => {
    const saved = localStorage.getItem('reports_section')
    if (saved === 'projects' || saved === 'employees' || saved === 'expenses') {
      return saved
    }
    return 'projects'
  }
  
  const [section, setSection] = useState<'projects' | 'employees' | 'expenses'>(getSavedSection())
  const [projects, setProjects] = useState<Project[]>([])
  const [projectId, setProjectId] = useState<number | ''>('')
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [report, setReport] = useState<Report | null>(null)
  
  // Сохраняем выбранную вкладку в localStorage при изменении
  useEffect(() => {
    localStorage.setItem('reports_section', section)
  }, [section])

  const [modal, setModal] = useState<'' | 'contract_amount' | 'expense' | 'receipt' | 'client_expense' | 'close_client_expense'>('')
  const [fieldValue, setFieldValue] = useState('')
  const [expName, setExpName] = useState('')
  const [expAmount, setExpAmount] = useState('')
  const [expComment, setExpComment] = useState('')
  const [recName, setRecName] = useState('')
  const [recAmount, setRecAmount] = useState('')
  const [recComment, setRecComment] = useState('')
  const [cExpName, setCExpName] = useState('')
  const [cExpAmount, setCExpAmount] = useState('')
  const [cExpAmountWithTax, setCExpAmountWithTax] = useState('')
  const [cExpComment, setCExpComment] = useState('')
  const [closeAmount, setCloseAmount] = useState('')
  const [closeAmountWithTax, setCloseAmountWithTax] = useState('')
  const [closeComment, setCloseComment] = useState('')
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null)
  const [editingReceipt, setEditingReceipt] = useState<Receipt | null>(null)
  const [editingClientExpense, setEditingClientExpense] = useState<ClientExpense | null>(null)
  const [tab, setTab] = useState<'expenses' | 'receipts' | 'client_expenses'>('expenses')
  const [taxOptions, setTaxOptions] = useState<{id:number; name:string; rate:number}[]>([])
  const [tax, setTax] = useState(1)

  // Для поступлений и обычных расходов: налог вычитается из суммы
  const applyTax = (amount: number) => amount * tax
  const removeTax = (amount: number) => amount / tax
  
  // Для клиентских расходов: налог добавляется к сумме
  // Если tax = 0.95 (ЯТТ 5%), то налог = 5%, сумма с налогом = сумма + (сумма * 0.05)
  // Если tax = 0.83 (ООО 17%), то налог = 17%, сумма с налогом = сумма + (сумма * 0.17)
  const applyClientTax = (amount: number) => amount + (amount * (1 - tax))  // Добавляем налог
  const removeClientTax = (amount: number) => amount / (1 + (1 - tax))  // Убираем налог
  
  const balanceAfterTax = report ? applyTax(report.receipts) : 0
  const positiveBalance = report ? report.receipts - report.total_expenses : 0
  const positiveBalanceTax = report ? balanceAfterTax - report.total_expenses : 0

  // Обработчики для клиентских расходов
  const handleCExpAmountChange = (value: string) => {
    setCExpAmount(formatInput(value))
    const amount = parseNumber(value)
    if (amount > 0) {
      setCExpAmountWithTax(formatInput(String(Math.round(applyClientTax(amount)))))
    } else {
      setCExpAmountWithTax('')
    }
  }

  const handleCExpAmountWithTaxChange = (value: string) => {
    setCExpAmountWithTax(formatInput(value))
    const amount = parseNumber(value)
    if (amount > 0) {
      setCExpAmount(formatInput(String(Math.round(removeClientTax(amount)))))
    } else {
      setCExpAmount('')
    }
  }

  // Обработчики для закрытия расходов
  const handleCloseAmountChange = (value: string) => {
    setCloseAmount(formatInput(value))
    const amount = parseNumber(value)
    if (amount > 0) {
      setCloseAmountWithTax(formatInput(String(Math.round(applyClientTax(amount)))))
    } else {
      setCloseAmountWithTax('')
    }
  }

  const handleCloseAmountWithTaxChange = (value: string) => {
    setCloseAmountWithTax(formatInput(value))
    const amount = parseNumber(value)
    if (amount > 0) {
      setCloseAmount(formatInput(String(Math.round(removeClientTax(amount)))))
    } else {
      setCloseAmount('')
    }
  }

  // Функция для закрытия модального окна и сброса всех значений
  const closeModal = () => {
    setModal('')
    // Сбрасываем значения для клиентских расходов
    setCExpName('')
    setCExpAmount('')
    setCExpAmountWithTax('')
    setCExpComment('')
    setEditingClientExpense(null)
    // Сбрасываем значения для закрытия расходов  
    setCloseAmount('')
    setCloseAmountWithTax('')
    setCloseComment('')
    // Сбрасываем другие значения
    setFieldValue('')
    setExpName('')
    setExpAmount('')
    setExpComment('')
    setRecName('')
    setRecAmount('')
    setRecComment('')
    setEditingExpense(null)
    setEditingReceipt(null)
  }

  const loadProjects = async () => {
    const res = await fetch(`${API_URL}/projects/`, { headers: { Authorization: `Bearer ${token}` } })
    if (res.ok) {
      const data = await res.json()
      const activeProjects = data.filter((p: any) => !p.is_archived)
      setProjects(activeProjects)
    }
  }


  const loadReport = async (pid: number, m: number = month) => {
    const res = await fetch(`${API_URL}/projects/${pid}/report?month=${m}`, { headers: { Authorization: `Bearer ${token}` } })
    if (res.ok) setReport(await res.json())
  }

  const loadTaxes = async () => {
    const res = await fetch(`${API_URL}/taxes/`, { headers: { Authorization: `Bearer ${token}` } })
    if (res.ok) {
      const data = await res.json()
      setTaxOptions(data)
    }
  }

  useEffect(() => {
    if (projectId && taxOptions.length) {
      const key = `report_tax_${projectId}`
      const saved = localStorage.getItem(key)
      if (saved && taxOptions.some(t => t.rate === parseFloat(saved))) {
        setTax(parseFloat(saved))
      } else {
        const def = taxOptions[0].rate
        setTax(def)
        localStorage.setItem(key, String(def))
      }
    }
  }, [projectId, taxOptions])

  useEffect(() => { loadProjects(); loadTaxes() }, [])
  useEffect(() => { if (projectId) loadReport(projectId as number, month) }, [projectId, month])

  const openEditField = (field: 'contract_amount') => {
    setFieldValue(report ? formatInput(String(report[field])) : '')
    setModal(field)
  }

  const submitField = async () => {
    if (!projectId || !modal) return
    const res = await fetch(`${API_URL}/projects/${projectId}/report?month=${month}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ [modal]: parseNumber(fieldValue) })
    })
    closeModal()
    if (res.ok) {
      const data = await res.json()
      setReport(data)
    } else {
      loadReport(projectId as number, month)
    }
  }

  const openExpense = (e?: Expense) => {
    if (e) {
      setEditingExpense(e)
      setExpName(e.name)
      setExpAmount(formatInput(String(e.amount)))
      setExpComment(e.comment || '')
    } else {
      setEditingExpense(null)
      setExpName('')
      setExpAmount('')
      setExpComment('')
    }
    setModal('expense')
  }

  const openReceipt = (r?: Receipt) => {
    if (r) {
      setEditingReceipt(r)
      setRecName(r.name)
      setRecAmount(formatInput(String(r.amount)))
      setRecComment(r.comment || '')
    } else {
      setEditingReceipt(null)
      setRecName('')
      setRecAmount('')
      setRecComment('')
    }
    setModal('receipt')
  }

  const openClientExpense = (e?: ClientExpense) => {
    if (e) {
      setEditingClientExpense(e)
      setCExpName(e.name)
      setCExpAmount(formatInput(String(e.amount)))
      setCExpAmountWithTax(formatInput(String(Math.round(applyClientTax(e.amount)))))
      setCExpComment(e.comment || '')
    } else {
      setEditingClientExpense(null)
      setCExpName('')
      setCExpAmount('')
      setCExpAmountWithTax('')
      setCExpComment('')
    }
    setModal('client_expense')
  }

  const openCloseClientExpense = (e: ClientExpense) => {
    setEditingClientExpense(e)
    setCloseAmount(formatInput(String(e.amount)))
    setCloseAmountWithTax(formatInput(String(Math.round(applyClientTax(e.amount)))))
    setCloseComment(e.comment || '')
    setModal('close_client_expense')
  }

  const submitExpense = async () => {
    if (!projectId) return
    const url = editingExpense
      ? `${API_URL}/expenses/${editingExpense.id}`
      : `${API_URL}/projects/${projectId}/expenses?month=${month}`
    const method = editingExpense ? 'PUT' : 'POST'
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: expName, amount: parseNumber(expAmount), comment: expComment })
    })
    closeModal()
    if (res.ok) {
      const exp: Expense = await res.json()
      setReport(r => {
        if (!r) return r
        let expenses = r.expenses
        let total = r.total_expenses
        if (editingExpense) {
          expenses = expenses.map(x => x.id === exp.id ? exp : x)
          total = total - editingExpense.amount + exp.amount
        } else {
          expenses = [...expenses, exp]
          total = total + exp.amount
        }
        return {
          ...r,
          expenses,
          total_expenses: total,
        }
      })
      setEditingExpense(null)
    } else {
      loadReport(projectId as number, month)
    }
  }

  const submitReceipt = async () => {
    if (!projectId) return
    const url = editingReceipt
      ? `${API_URL}/receipts/${editingReceipt.id}`
      : `${API_URL}/projects/${projectId}/receipts?month=${month}`
    const method = editingReceipt ? 'PUT' : 'POST'
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: recName, amount: parseNumber(recAmount), comment: recComment })
    })
    closeModal()
    if (res.ok) {
      const item: Receipt = await res.json()
      setReport(r => {
        if (!r) return r
        let list = r.receipts_list
        let sum = r.receipts
        if (editingReceipt) {
          list = list.map(x => x.id === item.id ? item : x)
          sum = sum - editingReceipt.amount + item.amount
        } else {
          list = [...list, item]
          sum = sum + item.amount
        }
        const clientSum = r.client_expenses.reduce((s,x)=>s+x.amount,0)
        const debt = r.contract_amount - sum + clientSum
        return { ...r, receipts: sum, receipts_list: list, debt }
      })
      setEditingReceipt(null)
    } else {
      loadReport(projectId as number, month)
    }
  }

  const submitClientExpense = async () => {
    if (!projectId) return
    const url = editingClientExpense
      ? `${API_URL}/client_expenses/${editingClientExpense.id}`
      : `${API_URL}/projects/${projectId}/client_expenses?month=${month}`
    const method = editingClientExpense ? 'PUT' : 'POST'
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ name: cExpName, amount: parseNumber(cExpAmount), comment: cExpComment })
    })
    closeModal()
    if (res.ok) {
      const item: ClientExpense = await res.json()
      setReport(r => {
        if (!r) return r
        let list = r.client_expenses
        let total = r.total_expenses
        if (editingClientExpense) {
          list = list.map(x => x.id === item.id ? item : x)
          total = total - editingClientExpense.amount + item.amount
        } else {
          list = [...list, item]
          total = total + item.amount
        }
        const clientSum = list.reduce((s,x)=>s+x.amount,0)
        const debt = r.contract_amount - r.receipts + clientSum
        return { ...r, client_expenses: list, debt, total_expenses: total }
      })
      setEditingClientExpense(null)
    } else {
      loadReport(projectId as number, month)
    }
  }

  const closeClientExpense = async () => {
    if (!editingClientExpense) return
    const res = await fetch(`${API_URL}/client_expenses/${editingClientExpense.id}/close`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ amount: parseNumber(closeAmount), comment: closeComment })
    })
    closeModal()
    if (res.ok) {
      const item = await res.json()
      setReport(r => {
        if (!r) return r
        let list = r.client_expenses
        let total = r.total_expenses
        if (item) {
          list = list.map(x => x.id === item.id ? item : x)
          total = total - editingClientExpense.amount + item.amount
        } else {
          list = list.filter(x => x.id !== editingClientExpense.id)
          total = total - editingClientExpense.amount
        }
        const clientSum = list.reduce((s,x)=>s+x.amount,0)
        const debt = r.contract_amount - r.receipts + clientSum
        return { ...r, client_expenses: list, debt, total_expenses: total }
      })
      setEditingClientExpense(null)
    } else {
      loadReport(projectId as number, month)
    }
  }


  const deleteExpense = async (id: number) => {
    await fetch(`${API_URL}/expenses/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
    if (projectId) loadReport(projectId as number, month)
  }

  const deleteReceipt = async (id: number) => {
    await fetch(`${API_URL}/receipts/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
    if (projectId) loadReport(projectId as number, month)
  }

  const deleteClientExpense = async (id: number) => {
    await fetch(`${API_URL}/client_expenses/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
    if (projectId) loadReport(projectId as number, month)
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Отчеты</h1>
      
      {/* Навигация по табам */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setSection('projects')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              section === 'projects'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Отчеты по проектам
          </button>
          <button
            onClick={() => setSection('employees')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              section === 'employees'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Отчет по сотрудникам
          </button>
          <button
            onClick={() => setSection('expenses')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              section === 'expenses'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Отчеты по расходам
          </button>
        </nav>
      </div>

      {/* Содержимое активной вкладки */}
      <div>
        {section === 'employees' ? (
          <EmployeeReport />
        ) : section === 'expenses' ? (
          <ExpenseReportsSection />
        ) : (
          <div>
            {!projectId ? (
              <div>
                <h2 className="text-xl font-semibold text-gray-800 mb-6">Выберите проект для просмотра отчета</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {projects.map(p => (
                    <div
                      key={p.id}
                      onClick={() => setProjectId(p.id)}
                      className="group bg-white rounded-xl shadow-sm hover:shadow-lg transition-all duration-300 cursor-pointer border border-gray-200 hover:border-blue-300 p-6 transform hover:-translate-y-1"
                    >
                      <div className="flex items-center space-x-4">
                        <div className="w-12 h-12 rounded-full bg-white border border-gray-200 flex items-center justify-center shadow-lg">
                          {p.logo ? (
                            <img 
                              src={`${API_URL}/${p.logo}`} 
                              alt={p.name}
                              className="w-8 h-8 object-cover rounded-full"
                              onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                target.style.display = 'none';
                                const fallback = target.nextElementSibling as HTMLElement;
                                if (fallback) fallback.style.display = 'block';
                              }}
                            />
                          ) : null}
                          <span className={`text-gray-700 font-bold text-lg ${p.logo ? 'hidden' : ''}`}>{p.name.charAt(0)}</span>
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-800 group-hover:text-blue-600 transition-colors">{p.name}</h3>
                          <p className="text-sm text-gray-500">📊 Отчет проекта</p>
                        </div>
                      </div>
                      <div className="mt-4 flex justify-end">
                        <svg className="w-5 h-5 text-gray-400 group-hover:text-blue-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-4">
                    <button
                      onClick={() => setProjectId('')}
                      className="flex items-center px-3 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all duration-200 group"
                    >
                      <svg className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                      </svg>
                      Назад к проектам
                    </button>
                    <h2 className="text-2xl font-bold text-gray-800">
                      {projects.find(p => p.id === projectId)?.name || 'Отчет проекта'}
                    </h2>
                  </div>
                </div>
                
                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
                  <div className="flex flex-wrap gap-4 items-center">
                    <div className="flex flex-col">
                      <label className="text-sm font-medium text-gray-600 mb-2">Месяц</label>
                      <select className="px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all" value={month} onChange={e => setMonth(Number(e.target.value))}>
                        {MONTH_NAMES.map((name, i) => (
                          <option key={i + 1} value={i + 1}>{name}</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex flex-col">
                      <label className="text-sm font-medium text-gray-600 mb-2">Налоговая ставка</label>
                      <select
                        className="px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                        value={tax}
                        onChange={e => {
                          const val = parseFloat(e.target.value)
                          setTax(val)
                          if (projectId) {
                            localStorage.setItem(`report_tax_${projectId}`, String(val))
                          }
                        }}
                      >
                        {taxOptions.map(opt => (
                          <option key={opt.id} value={opt.rate}>{opt.name}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
      {report && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
            <div 
              className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 cursor-pointer hover:shadow-md transition-shadow group"
              onClick={() => openEditField('contract_amount')}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                  <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <svg className="w-4 h-4 text-gray-400 group-hover:text-blue-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
              </div>
              <div className="text-sm font-medium text-gray-600 mb-1">Сумма контракта</div>
              <div className="text-2xl font-bold text-gray-900">{formatCurrency(report.contract_amount)}</div>
            </div>
            
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                  </svg>
                </div>
              </div>
              <div className="text-sm font-medium text-gray-600 mb-1">Поступления</div>
              <div className="text-2xl font-bold text-green-600">{formatCurrency(report.receipts)}</div>
            </div>
            
            <div className="bg-white rounded-xl shadow-sm border-l-4 border-red-500 p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
                  <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <div className="text-sm font-medium text-gray-600 mb-1">Долг</div>
              <div className="text-2xl font-bold text-red-600">{formatCurrency(report.debt)}</div>
            </div>
            
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
              <div className="text-sm font-medium text-gray-600 mb-1">Баланс после вычета налога</div>
              <div className="text-2xl font-bold text-purple-600">{formatCurrency(balanceAfterTax)}</div>
            </div>
            
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
                  <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
              </div>
              <div className="text-sm font-medium text-gray-600 mb-1">Общий расход</div>
              <div className="text-2xl font-bold text-orange-600">{formatCurrency(report.total_expenses)}</div>
            </div>
            
            <div className="bg-white rounded-xl shadow-sm border-l-4 border-emerald-500 p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
                  <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
              </div>
              <div className="text-sm font-medium text-gray-600 mb-1">Положительный баланс с учетом расходов</div>
              <div className="text-2xl font-bold text-emerald-600">{formatCurrency(positiveBalance)}</div>
            </div>
            
            <div className="bg-white rounded-xl shadow-sm border-l-4 border-teal-500 p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-teal-100 flex items-center justify-center">
                  <svg className="w-5 h-5 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
              </div>
              <div className="text-sm font-medium text-gray-600 mb-1">Баланс после вычета налога + расхода</div>
              <div className="text-2xl font-bold text-teal-600">{formatCurrency(positiveBalanceTax)}</div>
            </div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <div className="flex flex-wrap gap-2">
              <button 
                className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                  tab === 'receipts' 
                    ? 'bg-blue-500 text-white shadow-sm' 
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`} 
                onClick={() => setTab('receipts')}
              >
                💰 Поступления
              </button>
              <button 
                className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                  tab === 'expenses' 
                    ? 'bg-blue-500 text-white shadow-sm' 
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`} 
                onClick={() => setTab('expenses')}
              >
                💸 Расходы
              </button>
              <button 
                className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                  tab === 'client_expenses' 
                    ? 'bg-blue-500 text-white shadow-sm' 
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`} 
                onClick={() => setTab('client_expenses')}
              >
                🏢 Клиентские расходы
              </button>
            </div>
          </div>

          {tab === 'expenses' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium text-gray-900">Расходы</h3>
                <button 
                  className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-md transition-colors"
                  onClick={() => openExpense()}
                >
                  + Добавить
                </button>
              </div>
              
              {report.expenses.length > 0 ? (
                <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Наименование</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Сумма</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Комментарий</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Действия</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {report.expenses.map(e => (
                        <tr key={e.id}>
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">{e.name}</td>
                          <td className="px-4 py-3 text-sm font-semibold text-gray-900">{formatCurrency(e.amount)}</td>
                          <td className="px-4 py-3 text-sm text-gray-500">{e.comment || '—'}</td>
                          <td className="px-4 py-3 text-center space-x-3">
                            <button 
                              className="text-blue-600 hover:text-blue-900 text-sm"
                              onClick={() => openExpense(e)}
                            >
                              Редактировать
                            </button>
                            <button 
                              className="text-red-600 hover:text-red-900 text-sm"
                              onClick={() => deleteExpense(e.id)}
                            >
                              Удалить
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-12 text-center text-gray-500">
                  <p className="text-base">Нет расходов</p>
                  <p className="text-sm mt-1">Добавьте первый расход для отслеживания</p>
                </div>
              )}
            </div>
          )}

          {tab === 'receipts' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium text-gray-900">Поступления</h3>
                <button 
                  className="px-3 py-1.5 bg-green-500 hover:bg-green-600 text-white text-sm rounded-md transition-colors"
                  onClick={() => openReceipt()}
                >
                  + Добавить
                </button>
              </div>
              
              {report.receipts_list.length > 0 ? (
                <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Наименование</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Сумма</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Комментарий</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Действия</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {report.receipts_list.map(rp => (
                        <tr key={rp.id}>
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">{rp.name}</td>
                          <td className="px-4 py-3 text-sm font-semibold text-green-600">{formatCurrency(rp.amount)}</td>
                          <td className="px-4 py-3 text-sm text-gray-500">{rp.comment || '—'}</td>
                          <td className="px-4 py-3 text-center space-x-3">
                            <button 
                              className="text-blue-600 hover:text-blue-900 text-sm"
                              onClick={() => openReceipt(rp)}
                            >
                              Редактировать
                            </button>
                            <button 
                              className="text-red-600 hover:text-red-900 text-sm"
                              onClick={() => deleteReceipt(rp.id)}
                            >
                              Удалить
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-12 text-center text-gray-500">
                  <p className="text-base">Нет поступлений</p>
                  <p className="text-sm mt-1">Добавьте первое поступление для отслеживания</p>
                </div>
              )}
            </div>
          )}

          {tab === 'client_expenses' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-medium text-gray-900">Клиентские расходы</h3>
                <button 
                  className="px-3 py-1.5 bg-purple-500 hover:bg-purple-600 text-white text-sm rounded-md transition-colors"
                  onClick={() => openClientExpense()}
                >
                  + Добавить
                </button>
              </div>
              
              {report.client_expenses.length > 0 ? (
                <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Название</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Сумма</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">С налогом</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Комментарий</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Действия</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {report.client_expenses.map(c => (
                        <tr key={c.id}>
                          <td className="px-4 py-3 text-sm font-medium text-gray-900">{c.name}</td>
                          <td className="px-4 py-3 text-sm font-semibold text-purple-600">{formatCurrency(c.amount)}</td>
                          <td className="px-4 py-3 text-sm font-semibold text-purple-800">{formatCurrency(applyTax(c.amount))}</td>
                          <td className="px-4 py-3 text-sm text-gray-500">{c.comment || '—'}</td>
                          <td className="px-4 py-3 text-center">
                            <div className="flex flex-wrap justify-center gap-2">
                              <button 
                                className="text-blue-600 hover:text-blue-900 text-sm"
                                onClick={() => openClientExpense(c)}
                              >
                                Редактировать
                              </button>
                              <button 
                                className="text-red-600 hover:text-red-900 text-sm"
                                onClick={() => deleteClientExpense(c.id)}
                              >
                                Удалить
                              </button>
                              <button 
                                className="px-2 py-1 text-xs bg-green-50 text-green-600 hover:bg-green-100 rounded transition-colors"
                                onClick={() => openCloseClientExpense(c)}
                              >
                                Закрыть
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-12 text-center text-gray-500">
                  <p className="text-base">Нет клиентских расходов</p>
                  <p className="text-sm mt-1">Добавьте первый расход клиента для отслеживания</p>
                </div>
              )}
            </div>
          )}
          {modal && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
              <div className="bg-white p-4 rounded w-96 space-y-4">
                {modal === 'expense' ? (
                  <>
                    <h2 className="text-lg font-semibold">{editingExpense ? 'Редактировать расход' : 'Новый расход'}</h2>
                    <label className="block">
                      <span className="text-sm text-gray-500">Наименование</span>
                      <input 
                        className="border p-2 w-full" 
                        value={expName} 
                        onChange={e => setExpName(e.target.value)}
                        placeholder="Введите название расхода"
                      />
                    </label>
                    <label className="block">
                      <span className="text-sm text-gray-500">Сумма</span>
                      <input className="border p-2 w-full" value={expAmount} onChange={e => setExpAmount(formatInput(e.target.value))} />
                    </label>
                    <label className="block">
                      <span className="text-sm text-gray-500">Комментарий</span>
                      <input className="border p-2 w-full" value={expComment} onChange={e => setExpComment(e.target.value)} />
                    </label>
                    <div className="flex justify-end space-x-2">
                      <button className="px-3 py-1 border rounded" onClick={() => closeModal()}>Отмена</button>
                      <button className="px-3 py-1 bg-blue-500 text-white rounded" onClick={submitExpense}>Сохранить</button>
                    </div>
                  </>
                ) : modal === 'receipt' ? (
                  <>
                    <h2 className="text-lg font-semibold">{editingReceipt ? 'Редактировать поступление' : 'Новое поступление'}</h2>
                    <label className="block">
                      <span className="text-sm text-gray-500">Наименование</span>
                      <input className="border p-2 w-full" value={recName} onChange={e => setRecName(e.target.value)} />
                    </label>
                    <label className="block">
                      <span className="text-sm text-gray-500">Сумма</span>
                      <input className="border p-2 w-full" value={recAmount} onChange={e => setRecAmount(formatInput(e.target.value))} />
                    </label>
                    <label className="block">
                      <span className="text-sm text-gray-500">Комментарий</span>
                      <input className="border p-2 w-full" value={recComment} onChange={e => setRecComment(e.target.value)} />
                    </label>
                    <div className="flex justify-end space-x-2">
                      <button className="px-3 py-1 border rounded" onClick={() => closeModal()}>Отмена</button>
                      <button className="px-3 py-1 bg-blue-500 text-white rounded" onClick={submitReceipt}>Сохранить</button>
                    </div>
                  </>
                ) : modal === 'client_expense' ? (
                  <>
                    <h2 className="text-lg font-semibold">{editingClientExpense ? 'Редактировать клиентский расход' : 'Новый клиентский расход'}</h2>
                    <label className="block">
                      <span className="text-sm text-gray-500">Наименование</span>
                      <input className="border p-2 w-full" value={cExpName} onChange={e => setCExpName(e.target.value)} />
                    </label>
                    <label className="block">
                      <span className="text-sm text-gray-500">Сумма</span>
                      <input className="border p-2 w-full" value={cExpAmount} onChange={e => handleCExpAmountChange(e.target.value)} />
                    </label>
                    <label className="block">
                      <span className="text-sm text-gray-500">Сумма с учетом налога</span>
                      <input className="border p-2 w-full" value={cExpAmountWithTax} onChange={e => handleCExpAmountWithTaxChange(e.target.value)} />
                    </label>
                    <label className="block">
                      <span className="text-sm text-gray-500">Комментарий</span>
                      <input className="border p-2 w-full" value={cExpComment} onChange={e => setCExpComment(e.target.value)} />
                    </label>
                    <div className="flex justify-end space-x-2">
                      <button className="px-3 py-1 border rounded" onClick={() => closeModal()}>Отмена</button>
                      <button className="px-3 py-1 bg-blue-500 text-white rounded" onClick={submitClientExpense}>Сохранить</button>
                    </div>
                  </>
                ) : modal === 'close_client_expense' ? (
                  <>
                    <h2 className="text-lg font-semibold">Закрыть расход</h2>
                    <label className="block">
                      <span className="text-sm text-gray-500">Сумма</span>
                      <input className="border p-2 w-full" value={closeAmount} onChange={e => handleCloseAmountChange(e.target.value)} />
                    </label>
                    <label className="block">
                      <span className="text-sm text-gray-500">Сумма с учетом налога</span>
                      <input className="border p-2 w-full" value={closeAmountWithTax} onChange={e => handleCloseAmountWithTaxChange(e.target.value)} />
                    </label>
                    <label className="block">
                      <span className="text-sm text-gray-500">Комментарий</span>
                      <input className="border p-2 w-full" value={closeComment} onChange={e => setCloseComment(e.target.value)} />
                    </label>
                    <div className="flex justify-end space-x-2">
                      <button className="px-3 py-1 border rounded" onClick={() => closeModal()}>Отмена</button>
                      <button className="px-3 py-1 bg-blue-500 text-white rounded" onClick={closeClientExpense}>Сохранить</button>
                    </div>
                  </>
                ) : (
                  <>
                    <h2 className="text-lg font-semibold">Сумма контракта</h2>
                    <input className="border p-2 w-full" value={fieldValue} onChange={e => setFieldValue(formatInput(e.target.value))} />
                    <div className="flex justify-end space-x-2">
                      <button className="px-3 py-1 border rounded" onClick={() => closeModal()}>Отмена</button>
                      <button className="px-3 py-1 bg-blue-500 text-white rounded" onClick={submitField}>Сохранить</button>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </>
      )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// Компонент для отчетов по расходам
function ExpenseReportsSection() {
  const token = localStorage.getItem('token')
  const [expenseData, setExpenseData] = useState<any[]>([])
  const [generalExpenseData, setGeneralExpenseData] = useState<any[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<number | ''>('')
  const [loading, setLoading] = useState(false)
  const [generalLoading, setGeneralLoading] = useState(false)
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [activeTab, setActiveTab] = useState<'project-expenses' | 'general-expenses'>('project-expenses')

  const loadProjects = async () => {
    const res = await fetch(`${API_URL}/projects/`, { headers: { Authorization: `Bearer ${token}` } })
    if (res.ok) {
      const data = await res.json()
      setProjects(data.filter((p: any) => !p.is_archived))
    }
  }

  const loadExpenseData = async () => {
    if (!selectedProject || selectedProject === '') return

    setLoading(true)
    try {
      // Получаем затраты на проект из отчетов по проектам
      const projectReportRes = await fetch(`${API_URL}/projects/${selectedProject}/report?month=${month}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      let projectExpenses: any[] = []
      if (projectReportRes.ok) {
        const reportData = await projectReportRes.json()
        projectExpenses = reportData.expenses || []
      }

      // Получаем расходы операторов (только с почасовой оплатой)
      const operatorRes = await fetch(`${API_URL}/expense-reports/operators`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      let operatorExpenses: any[] = []
      if (operatorRes.ok) {
        const operatorData = await operatorRes.json()
        // Фильтруем только операторов с почасовой оплатой (!is_salaried)
        operatorExpenses = operatorData
          .filter((op: any) => !op.is_salaried)
          .map((op: any) => ({
            id: `operator_${op.operator_id}`,
            name: `Оператор: ${op.operator_name}`,
            amount: op.total_amount,
            type: 'operator',
            description: `${op.videos_completed} видео по ${formatCurrency(op.price_per_video || 0)} за видео`
          }))
      }

      // Получаем расходы сотрудников для конкретного проекта
      // Формируем параметры для фильтрации по месяцу
      const year = new Date().getFullYear()
      const monthStr = String(month).padStart(2, '0')
      const lastDay = new Date(year, month, 0).getDate()
      const employeeParams = new URLSearchParams()
      employeeParams.append('start_date', `${year}-${monthStr}-01`)
      employeeParams.append('end_date', `${year}-${monthStr}-${String(lastDay).padStart(2, '0')}`)
      employeeParams.append('all_users', 'true')

      const employeeRes = await fetch(`${API_URL}/employee-expenses/?${employeeParams}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      let employeeExpenses: any[] = []
      if (employeeRes.ok) {
        const employeeData = await employeeRes.json()
        // Фильтруем только расходы для выбранного проекта
        employeeExpenses = employeeData
          .filter((exp: any) => exp.project_id === selectedProject)
          .map((exp: any) => ({
            id: `employee_${exp.id}`,
            name: `${exp.name} (${exp.user?.name})`,
            amount: exp.amount,
            type: 'employee',
            description: exp.description || 'Расход сотрудника'
          }))
      }

      // Объединяем все расходы
      const allExpenses = [
        ...projectExpenses.map((exp: any) => ({ ...exp, type: 'project' })),
        ...operatorExpenses,
        ...employeeExpenses
      ]

      setExpenseData(allExpenses)
    } catch (error) {
      console.error('Error loading expense data:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadGeneralExpenseData = async () => {
    setGeneralLoading(true)
    try {
      // Вычисляем начало и конец выбранного месяца
      const year = new Date().getFullYear()
      const startDate = new Date(year, month - 1, 1)
      const endDate = new Date(year, month, 0) // Последний день месяца

      const startDateStr = startDate.toISOString().split('T')[0]
      const endDateStr = endDate.toISOString().split('T')[0]

      // Получаем операторов с фиксированной зарплатой (is_salaried = true)
      const operatorRes = await fetch(`${API_URL}/expense-reports/operators`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      let salariedOperators: any[] = []
      if (operatorRes.ok) {
        const operatorData = await operatorRes.json()
        // Фильтруем только операторов с фиксированной зарплатой (is_salaried)
        salariedOperators = operatorData
          .filter((op: any) => op.is_salaried)
          .map((op: any) => ({
            id: `salaried_operator_${op.operator_id}`,
            name: `Оператор (зарплата): ${op.operator_name}`,
            amount: op.monthly_salary || 0,
            type: 'salaried_operator',
            description: `${formatCurrency(op.monthly_salary || 0)} мес`
          }))
      }

      // Получаем общие расходы (common-expenses) с фильтром по дате
      const commonParams = new URLSearchParams()
      commonParams.append('start_date', startDateStr)
      commonParams.append('end_date', endDateStr)

      const commonRes = await fetch(`${API_URL}/common-expenses/?${commonParams}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      let commonExpenses: any[] = []
      if (commonRes.ok) {
        const commonData = await commonRes.json()
        commonExpenses = commonData.map((exp: any) => ({
          id: `common_${exp.id}`,
          name: exp.name,
          amount: exp.amount,
          type: 'common',
          description: exp.description || 'Общий расход организации',
          date: exp.date,
          creator_name: exp.creator_name
        }))
      }

      // Получаем расходы сотрудников без привязки к проекту с фильтром по дате
      const employeeParams = new URLSearchParams()
      employeeParams.append('all_users', 'true')
      employeeParams.append('start_date', startDateStr)
      employeeParams.append('end_date', endDateStr)

      const employeeRes = await fetch(`${API_URL}/employee-expenses/?${employeeParams}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      let employeeExpensesWithoutProject: any[] = []
      if (employeeRes.ok) {
        const employeeData = await employeeRes.json()
        // Фильтруем только расходы без проекта
        employeeExpensesWithoutProject = employeeData
          .filter((exp: any) => !exp.project_id)
          .map((exp: any) => ({
            id: `employee_no_project_${exp.id}`,
            name: `${exp.name} (${exp.user?.name || 'Неизвестный'})`,
            amount: exp.amount,
            type: 'employee_no_project',
            description: exp.description || 'Расход сотрудника без проекта',
            date: exp.date
          }))
      }

      // Объединяем все общие расходы
      const allGeneralExpenses = [
        ...salariedOperators,
        ...commonExpenses,
        ...employeeExpensesWithoutProject
      ]

      setGeneralExpenseData(allGeneralExpenses)
    } catch (error) {
      console.error('Error loading general expense data:', error)
    } finally {
      setGeneralLoading(false)
    }
  }

  useEffect(() => {
    loadProjects()
  }, [])

  useEffect(() => {
    if (selectedProject && selectedProject !== '') {
      loadExpenseData()
    }
  }, [selectedProject, month])

  useEffect(() => {
    if (activeTab === 'general-expenses') {
      loadGeneralExpenseData()
    }
  }, [activeTab, month])

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'project': return 'Затраты на проект'
      case 'operator': return 'Расходы операторов'
      case 'employee': return 'Расходы сотрудников'
      default: return 'Другое'
    }
  }

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'project':
        return <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">Проект</span>
      case 'operator':
        return <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded-full">Оператор</span>
      case 'employee':
        return <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">Сотрудник</span>
      default:
        return <span className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded-full">Другое</span>
    }
  }

  const totalAmount = expenseData.reduce((sum, item) => sum + item.amount, 0)

  return (
    <div>
      {/* Переключатель табов */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('project-expenses')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'project-expenses'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            📊 Расходы по проектам
          </button>
          <button
            onClick={() => setActiveTab('general-expenses')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'general-expenses'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            🏢 Общие расходы организации
          </button>
        </nav>
      </div>

      {activeTab === 'project-expenses' ? (
        <div>
          <h2 className="text-xl font-semibold text-gray-800 mb-6">Расходы по проектам</h2>

          {/* Фильтры */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="flex flex-col">
                <label className="text-sm font-medium text-gray-600 mb-2">Проект</label>
                <select
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  value={selectedProject}
                  onChange={e => setSelectedProject(e.target.value ? Number(e.target.value) : '')}
                >
                  <option value="">Выберите проект</option>
                  {projects.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col">
                <label className="text-sm font-medium text-gray-600 mb-2">Месяц</label>
                <select
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  value={month}
                  onChange={e => setMonth(Number(e.target.value))}
                >
                  {MONTH_NAMES.map((name, i) => (
                    <option key={i + 1} value={i + 1}>{name}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Загрузка расходов...</p>
            </div>
          ) : !selectedProject ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg">Выберите проект для просмотра расходов</p>
            </div>
          ) : expenseData.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg">Нет расходов для выбранного проекта</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Общая сводка */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Общие расходы по проекту: {projects.find(p => p.id === selectedProject)?.name}
                  </h3>
                  <div className="text-xl font-bold text-gray-900">
                    {formatCurrency(totalAmount)}
                  </div>
                </div>
              </div>

              {/* Расходы проектные */}
              {(() => {
                const projectExpenses = expenseData.filter(item => item.type === 'project')
                const projectTotal = projectExpenses.reduce((sum, item) => sum + item.amount, 0)

                return (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="bg-green-50 px-6 py-4 border-b border-green-200">
                      <div className="flex justify-between items-center">
                        <h4 className="text-lg font-semibold text-green-800">
                          🏗️ Расходы проектные
                        </h4>
                        <div className="text-lg font-bold text-green-800">
                          {formatCurrency(projectTotal)}
                        </div>
                      </div>
                    </div>
                    {projectExpenses.length === 0 ? (
                      <div className="px-6 py-8 text-center text-gray-500">
                        <p>Нет проектных расходов</p>
                      </div>
                    ) : (
                      <table className="min-w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Наименование</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Описание</th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Сумма</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {projectExpenses.map((item) => (
                            <tr key={item.id} className="hover:bg-green-50">
                              <td className="px-6 py-4">
                                <div className="text-sm font-medium text-gray-900">{item.name}</div>
                              </td>
                              <td className="px-6 py-4">
                                <div className="text-sm text-gray-500">{item.description || item.comment || '—'}</div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-right">
                                <div className="text-sm font-semibold text-gray-900">{formatCurrency(item.amount)}</div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )
              })()}

              {/* Расходы сотрудников */}
              {(() => {
                const employeeExpenses = expenseData.filter(item => item.type === 'employee')
                const employeeTotal = employeeExpenses.reduce((sum, item) => sum + item.amount, 0)

                return (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="bg-blue-50 px-6 py-4 border-b border-blue-200">
                      <div className="flex justify-between items-center">
                        <h4 className="text-lg font-semibold text-blue-800">
                          👥 Расходы сотрудников
                        </h4>
                        <div className="text-lg font-bold text-blue-800">
                          {formatCurrency(employeeTotal)}
                        </div>
                      </div>
                    </div>
                    {employeeExpenses.length === 0 ? (
                      <div className="px-6 py-8 text-center text-gray-500">
                        <p>Нет расходов сотрудников</p>
                      </div>
                    ) : (
                      <table className="min-w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Наименование</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Описание</th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Сумма</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {employeeExpenses.map((item) => (
                            <tr key={item.id} className="hover:bg-blue-50">
                              <td className="px-6 py-4">
                                <div className="text-sm font-medium text-gray-900">{item.name}</div>
                              </td>
                              <td className="px-6 py-4">
                                <div className="text-sm text-gray-500">{item.description || item.comment || '—'}</div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-right">
                                <div className="text-sm font-semibold text-gray-900">{formatCurrency(item.amount)}</div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )
              })()}

              {/* Расходы мобилографов */}
              {(() => {
                const operatorExpenses = expenseData.filter(item => item.type === 'operator')
                const operatorTotal = operatorExpenses.reduce((sum, item) => sum + item.amount, 0)

                return (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="bg-yellow-50 px-6 py-4 border-b border-yellow-200">
                      <div className="flex justify-between items-center">
                        <h4 className="text-lg font-semibold text-yellow-800">
                          📹 Расходы операторов
                        </h4>
                        <div className="text-lg font-bold text-yellow-800">
                          {formatCurrency(operatorTotal)}
                        </div>
                      </div>
                    </div>
                    {operatorExpenses.length === 0 ? (
                      <div className="px-6 py-8 text-center text-gray-500">
                        <p>Нет расходов операторов</p>
                      </div>
                    ) : (
                      <table className="min-w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Наименование</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Описание</th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Сумма</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {operatorExpenses.map((item) => (
                            <tr key={item.id} className="hover:bg-yellow-50">
                              <td className="px-6 py-4">
                                <div className="text-sm font-medium text-gray-900">{item.name}</div>
                              </td>
                              <td className="px-6 py-4">
                                <div className="text-sm text-gray-500">{item.description || item.comment || '—'}</div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-right">
                                <div className="text-sm font-semibold text-gray-900">{formatCurrency(item.amount)}</div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )
              })()}
            </div>
          )}
        </div>
      ) : (
        <div>
          <h2 className="text-xl font-semibold text-gray-800 mb-6">Общие расходы организации</h2>

          {/* Фильтр по месяцу для общих расходов */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="flex flex-col">
                <label className="text-sm font-medium text-gray-600 mb-2">Месяц</label>
                <select
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  value={month}
                  onChange={e => setMonth(Number(e.target.value))}
                >
                  {MONTH_NAMES.map((name, i) => (
                    <option key={i + 1} value={i + 1}>{name}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {generalLoading ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Загрузка общих расходов...</p>
            </div>
          ) : generalExpenseData.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg">Нет общих расходов организации</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Общая сводка */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Общие расходы организации
                  </h3>
                  <div className="text-xl font-bold text-gray-900">
                    {formatCurrency(generalExpenseData.reduce((sum, item) => sum + item.amount, 0))}
                  </div>
                </div>
              </div>

              {/* Операторы с фиксированной зарплатой */}
              {(() => {
                const salariedOperators = generalExpenseData.filter(item => item.type === 'salaried_operator')
                const salariedTotal = salariedOperators.reduce((sum, item) => sum + item.amount, 0)

                return (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="bg-purple-50 px-6 py-4 border-b border-purple-200">
                      <div className="flex justify-between items-center">
                        <h4 className="text-lg font-semibold text-purple-800">
                          💼 Операторы (фиксированная зарплата)
                        </h4>
                        <div className="text-lg font-bold text-purple-800">
                          {formatCurrency(salariedTotal)}
                        </div>
                      </div>
                    </div>
                    {salariedOperators.length === 0 ? (
                      <div className="px-6 py-8 text-center text-gray-500">
                        <p>Нет операторов с фиксированной зарплатой</p>
                      </div>
                    ) : (
                      <table className="min-w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Наименование</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Описание</th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Сумма</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {salariedOperators.map((item) => (
                            <tr key={item.id} className="hover:bg-purple-50">
                              <td className="px-6 py-4">
                                <div className="text-sm font-medium text-gray-900">{item.name}</div>
                              </td>
                              <td className="px-6 py-4">
                                <div className="text-sm text-gray-500">{item.description}</div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-right">
                                <div className="text-sm font-semibold text-gray-900">{formatCurrency(item.amount)}</div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )
              })()}

              {/* Общие расходы */}
              {(() => {
                const commonExpenses = generalExpenseData.filter(item => item.type === 'common')
                const commonTotal = commonExpenses.reduce((sum, item) => sum + item.amount, 0)

                return (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="bg-red-50 px-6 py-4 border-b border-red-200">
                      <div className="flex justify-between items-center">
                        <h4 className="text-lg font-semibold text-red-800">
                          🏢 Административные расходы
                        </h4>
                        <div className="text-lg font-bold text-red-800">
                          {formatCurrency(commonTotal)}
                        </div>
                      </div>
                    </div>
                    {commonExpenses.length === 0 ? (
                      <div className="px-6 py-8 text-center text-gray-500">
                        <p>Нет административных расходов</p>
                      </div>
                    ) : (
                      <table className="min-w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Наименование</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Описание</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Дата</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Добавил</th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Сумма</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {commonExpenses.map((item) => (
                            <tr key={item.id} className="hover:bg-red-50">
                              <td className="px-6 py-4">
                                <div className="text-sm font-medium text-gray-900">{item.name}</div>
                              </td>
                              <td className="px-6 py-4">
                                <div className="text-sm text-gray-500">{item.description}</div>
                              </td>
                              <td className="px-6 py-4">
                                <div className="text-sm text-gray-500">
                                  {item.date ? new Date(item.date).toLocaleDateString('ru-RU') : '—'}
                                </div>
                              </td>
                              <td className="px-6 py-4">
                                <div className="text-sm text-gray-500">{item.creator_name || '—'}</div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-right">
                                <div className="text-sm font-semibold text-gray-900">{formatCurrency(item.amount)}</div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )
              })()}

              {/* Расходы сотрудников без привязки к проектам */}
              {(() => {
                const employeeExpensesNoProject = generalExpenseData.filter(item => item.type === 'employee_no_project')
                const employeeNoProjectTotal = employeeExpensesNoProject.reduce((sum, item) => sum + item.amount, 0)

                return (
                  <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <div className="bg-blue-50 px-6 py-4 border-b border-blue-200">
                      <div className="flex justify-between items-center">
                        <h4 className="text-lg font-semibold text-blue-800">
                          👥 Расходы сотрудников без привязки к проектам
                        </h4>
                        <div className="text-lg font-bold text-blue-800">
                          {formatCurrency(employeeNoProjectTotal)}
                        </div>
                      </div>
                    </div>
                    {employeeExpensesNoProject.length === 0 ? (
                      <div className="px-6 py-8 text-center text-gray-500">
                        <p>Нет расходов сотрудников без привязки к проектам</p>
                      </div>
                    ) : (
                      <table className="min-w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Наименование</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Описание</th>
                            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Дата</th>
                            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Сумма</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {employeeExpensesNoProject.map((item) => (
                            <tr key={item.id} className="hover:bg-blue-50">
                              <td className="px-6 py-4">
                                <div className="text-sm font-medium text-gray-900">{item.name}</div>
                              </td>
                              <td className="px-6 py-4">
                                <div className="text-sm text-gray-500">{item.description}</div>
                              </td>
                              <td className="px-6 py-4">
                                <div className="text-sm text-gray-500">
                                  {item.date ? new Date(item.date).toLocaleDateString('ru-RU') : '—'}
                                </div>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-right">
                                <div className="text-sm font-semibold text-gray-900">{formatCurrency(item.amount)}</div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )
              })()}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Reports
