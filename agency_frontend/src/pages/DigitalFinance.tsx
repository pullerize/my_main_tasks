import { useEffect, useState } from 'react';
import { API_URL } from '../api';
import { getCurrentTimeUTC5, getCurrentDateUTC5 } from '../utils/dateUtils';

interface Tax {
  id: number;
  name: string;
  rate: number;
}

interface DigitalProject {
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
}

interface FinancialData {
  id: number;
  project_id: number;
  tax_id?: number;
  cost_without_tax?: number;
  cost_with_tax?: number;
  created_at: string;
  updated_at: string;
}

interface Expense {
  id: number;
  project_id: number;
  description: string;
  amount: number;
  date: string;
  created_at: string;
}

export default function DigitalFinance() {
  const token = localStorage.getItem('token');
  const [projects, setProjects] = useState<DigitalProject[]>([]);
  const [taxes, setTaxes] = useState<Tax[]>([]);
  const [financialData, setFinancialData] = useState<Record<number, FinancialData>>({});
  const [expensesData, setExpensesData] = useState<Record<number, Expense[]>>({});
  const [loading, setLoading] = useState(true);
  const [expandedProject, setExpandedProject] = useState<number | null>(null);
  const [showExpenseModal, setShowExpenseModal] = useState<number | null>(null);
  const [newExpense, setNewExpense] = useState({ description: '', amount: '', amountWithTax: '' });
  const [subscriptionProjects, setSubscriptionProjects] = useState<Set<number>>(new Set());
  const [services, setServices] = useState<any[]>([]);
  // Инициализируем с текущим месяцем сразу
  const getCurrentMonthRange = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    
    const formatDate = (date: Date) => {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    };
    
    return {
      from: formatDate(firstDay),
      to: formatDate(lastDay)
    };
  };

  const currentMonth = getCurrentMonthRange();
  const [dateFromFilter, setDateFromFilter] = useState<string>(currentMonth.from);
  const [dateToFilter, setDateToFilter] = useState<string>(currentMonth.to);
  const [serviceFilter, setServiceFilter] = useState<string>('');

  const load = async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const [projectsRes, taxesRes, servicesRes] = await Promise.all([
        fetch(`${API_URL}/digital/projects`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/taxes/`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/digital/services`, { headers: { Authorization: `Bearer ${token}` } })
      ]);

      if (projectsRes.ok) {
        const data = await projectsRes.json();
        const projectsList = Array.isArray(data) ? data : [];
        setProjects(projectsList);
        
        // Загружаем финансовые данные для каждого проекта
        await loadFinancialData(projectsList);
      }

      if (taxesRes.ok) {
        const taxData = await taxesRes.json();
        setTaxes(Array.isArray(taxData) ? taxData : []);
      }

      if (servicesRes.ok) {
        const serviceData = await servicesRes.json();
        setServices(Array.isArray(serviceData) ? serviceData : []);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    }
    setLoading(false);
  };

  const loadFinancialData = async (projectsList: DigitalProject[]) => {
    if (!token) return;

    try {
      const financialPromises = projectsList.map(async (project) => {
        const [financeRes, expensesRes] = await Promise.all([
          fetch(`${API_URL}/digital/projects/${project.id}/finance`, { 
            headers: { Authorization: `Bearer ${token}` } 
          }),
          fetch(`${API_URL}/digital/projects/${project.id}/expenses`, { 
            headers: { Authorization: `Bearer ${token}` } 
          })
        ]);

        const results = await Promise.all([
          financeRes.ok ? financeRes.json() : null,
          expensesRes.ok ? expensesRes.json() : []
        ]);

        return {
          projectId: project.id,
          finance: results[0],
          expenses: results[1]
        };
      });

      const results = await Promise.all(financialPromises);
      
      const newFinancialData: Record<number, FinancialData> = {};
      const newExpensesData: Record<number, Expense[]> = {};

      results.forEach(({ projectId, finance, expenses }) => {
        if (finance && finance.id > 0) {
          newFinancialData[projectId] = finance;
        }
        newExpensesData[projectId] = expenses || [];
      });

      setFinancialData(newFinancialData);
      setExpensesData(newExpensesData);
    } catch (error) {
      console.error('Failed to load financial data:', error);
    }
  };

  useEffect(() => {
    console.log('Component mounted with date range:', { 
      from: dateFromFilter, 
      to: dateToFilter,
      currentDate: getCurrentTimeUTC5()
    });
    
    load();
  }, []);

  const updateFinancialData = async (projectId: number, updates: Partial<FinancialData>) => {
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/digital/projects/${projectId}/finance`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tax_id: updates.tax_id,
          cost_without_tax: updates.cost_without_tax,
          cost_with_tax: updates.cost_with_tax
        }),
      });

      if (response.ok) {
        const savedData = await response.json();
        setFinancialData(prev => ({
          ...prev,
          [projectId]: savedData
        }));
      } else {
        console.error('Failed to save financial data');
      }
    } catch (error) {
      console.error('Error saving financial data:', error);
    }
  };

  const calculateTaxes = (amount: number, taxRate: number, isWithTax: boolean) => {
    if (isWithTax) {
      // Если введена стоимость с налогом, вычисляем без налога
      const withoutTax = amount / taxRate;
      return {
        cost_without_tax: Math.round(withoutTax * 100) / 100,
        cost_with_tax: amount
      };
    } else {
      // Если введена стоимость без налога, вычисляем с налогом
      const withTax = amount * taxRate;
      return {
        cost_without_tax: amount,
        cost_with_tax: Math.round(withTax * 100) / 100
      };
    }
  };

  const handleCostChange = async (projectId: number, value: string) => {
    const amount = parseFloat(value) || 0;
    const projectData = financialData[projectId];
    const selectedTax = taxes.find(t => t.id === projectData?.tax_id);
    
    // Если выбран налог, автоматически рассчитываем сумму после налогообложения
    if (selectedTax && amount > 0) {
      const afterTax = amount * selectedTax.rate;
      await updateFinancialData(projectId, {
        cost_without_tax: amount,
        cost_with_tax: Math.round(afterTax * 100) / 100,
        tax_id: projectData?.tax_id
      });
    } else {
      await updateFinancialData(projectId, {
        cost_without_tax: amount || undefined,
        tax_id: projectData?.tax_id
      });
    }
  };

  const handleTaxChange = async (projectId: number, taxId: number) => {
    const projectData = financialData[projectId];
    
    // Пересчитать сумму после налогообложения
    const selectedTax = taxes.find(t => t.id === taxId);
    if (selectedTax && projectData?.cost_without_tax) {
      const afterTax = projectData.cost_without_tax * selectedTax.rate;
      await updateFinancialData(projectId, {
        tax_id: taxId,
        cost_with_tax: Math.round(afterTax * 100) / 100,
        cost_without_tax: projectData.cost_without_tax
      });
    } else {
      await updateFinancialData(projectId, { 
        tax_id: taxId,
        cost_without_tax: projectData?.cost_without_tax,
        cost_with_tax: projectData?.cost_with_tax
      });
    }
  };

  const getExpenseTaxRate = (projectId: number) => {
    const data = financialData[projectId];
    const selectedTax = taxes.find(t => t.id === data?.tax_id);
    if (!selectedTax) return 0;
    return 1 - selectedTax.rate; // Налоговая ставка для расходов
  };

  const addExpense = async (projectId: number) => {
    if (!newExpense.description.trim() || (!newExpense.amount && !newExpense.amountWithTax) || !token) return;
    
    // Используем сумму без налога для сохранения
    const baseAmount = newExpense.amount ? parseFloat(newExpense.amount) : 
      parseFloat(newExpense.amountWithTax) / (1 + getExpenseTaxRate(projectId));
    
    try {
      const response = await fetch(`${API_URL}/digital/projects/${projectId}/expenses`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          description: newExpense.description.trim(),
          amount: baseAmount,
          date: getCurrentDateUTC5()
        }),
      });

      if (response.ok) {
        const savedExpense = await response.json();
        setExpensesData(prev => ({
          ...prev,
          [projectId]: [...(prev[projectId] || []), savedExpense]
        }));
        setNewExpense({ description: '', amount: '', amountWithTax: '' });
        setShowExpenseModal(null);
      } else {
        console.error('Failed to save expense');
      }
    } catch (error) {
      console.error('Error saving expense:', error);
    }
  };

  const removeExpense = async (projectId: number, expenseId: number) => {
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/digital/projects/${projectId}/expenses/${expenseId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setExpensesData(prev => ({
          ...prev,
          [projectId]: (prev[projectId] || []).filter(e => e.id !== expenseId)
        }));
      } else {
        console.error('Failed to delete expense');
      }
    } catch (error) {
      console.error('Error deleting expense:', error);
    }
  };

  const getTotalExpenses = (projectId: number) => {
    const expenses = expensesData[projectId] || [];
    return expenses.reduce((sum, expense) => sum + expense.amount, 0);
  };

  const getTaxAmount = (projectId: number) => {
    const data = financialData[projectId];
    const selectedTax = taxes.find(t => t.id === data?.tax_id);
    if (!data?.cost_without_tax || !selectedTax) return 0;
    
    // Налог рассчитывается как разность между стоимостью и суммой после применения коэффициента
    // ЯТТ 0.95 - остается 95% от стоимости, налог 5%
    // ООО 0.83 - остается 83% от стоимости, налог 17%
    // Нал 1.0 - остается 100% от стоимости, налог 0%
    const amountAfterTax = data.cost_without_tax * selectedTax.rate;
    return data.cost_without_tax - amountAfterTax;
  };

  const getExecutorPercent = (projectId: number) => {
    // Если проект имеет подписку, процент исполнителя не взимается
    if (subscriptionProjects.has(projectId)) return 0;
    
    const data = financialData[projectId];
    const revenue = data?.cost_without_tax || 0;
    const taxAmount = getTaxAmount(projectId);
    const expenses = getTotalExpenses(projectId);
    return (revenue - taxAmount - expenses) * 0.2; // 20%
  };

  const getTotalProjectCosts = (projectId: number) => {
    const taxAmount = getTaxAmount(projectId);
    const expenses = getTotalExpenses(projectId);
    const executorPercent = getExecutorPercent(projectId);
    return taxAmount + expenses + executorPercent;
  };

  const getProfit = (projectId: number) => {
    const data = financialData[projectId];
    const revenue = data?.cost_without_tax || 0;
    const totalCosts = getTotalProjectCosts(projectId);
    return revenue - totalCosts;
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ru-RU').format(amount) + ' сум';
  };

  const toggleSubscription = (projectId: number) => {
    setSubscriptionProjects(prev => {
      const newSet = new Set(prev);
      if (newSet.has(projectId)) {
        newSet.delete(projectId);
      } else {
        // Ограничиваем максимум 5 подписок
        if (newSet.size < 5) {
          newSet.add(projectId);
        }
      }
      return newSet;
    });
  };

  const filterProjects = (projectsToFilter: DigitalProject[]) => {
    return projectsToFilter.filter(project => {
      // Фильтр по диапазону дат (проект показывается если его период пересекается с фильтром)
      if (dateFromFilter || dateToFilter) {
        const projectCreatedDate = new Date(project.created_at).toISOString().split('T')[0];
        const projectDeadlineDate = project.deadline ? new Date(project.deadline).toISOString().split('T')[0] : projectCreatedDate;
        
        // Период проекта: от даты создания до дедлайна (или только дата создания если дедлайна нет)
        const projectStartDate = projectCreatedDate;
        const projectEndDate = projectDeadlineDate;
        
        // Проверяем пересечение периодов
        if (dateFromFilter && projectEndDate < dateFromFilter) return false; // Проект закончился до начала фильтра
        if (dateToFilter && projectStartDate > dateToFilter) return false; // Проект начался после окончания фильтра
      }

      // Фильтр по услуге
      if (serviceFilter && serviceFilter !== 'all') {
        if (project.service !== serviceFilter) return false;
      }

      return true;
    });
  };

  if (loading) {
    return (
      <div className="w-full overflow-hidden bg-gray-50 min-h-screen">
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-400 text-4xl">⏳ Загрузка...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full overflow-hidden bg-gray-50 min-h-screen">
      <div className="bg-white shadow-sm border-b p-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Digital Финансы</h1>
            <p className="text-gray-600 mt-1">Управляйте финансами digital проектов</p>
            {/* Отладочная информация */}
            <div className="mt-2 text-xs text-gray-500">
              Текущий диапазон: {dateFromFilter} - {dateToFilter} | 
              Текущая дата: {new Date().toLocaleDateString('ru-RU')} |
              Месяц: {new Date().getMonth() + 1}
            </div>
          </div>
        </div>
      </div>
      
      <div className="p-6">
        {/* Filters */}
        {projects.length > 0 && (
          <div className="mb-6 grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Date range filter */}
            <div className="flex flex-col">
              <label className="text-sm font-medium text-gray-700 mb-2">
                📅 От даты
              </label>
              <input
                type="date"
                value={dateFromFilter}
                onChange={(e) => setDateFromFilter(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div className="flex flex-col">
              <label className="text-sm font-medium text-gray-700 mb-2">
                📅 До даты
              </label>
              <input
                type="date"
                value={dateToFilter}
                onChange={(e) => setDateToFilter(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Service filter */}
            <div className="flex flex-col">
              <label className="text-sm font-medium text-gray-700 mb-2">
                🔧 Фильтр по услугам
              </label>
              <select
                value={serviceFilter}
                onChange={(e) => setServiceFilter(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Все услуги</option>
                {services.map(service => (
                  <option key={service.id} value={service.name}>
                    {service.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Subscription counter */}
            <div className="flex flex-col justify-end">
              <div className="flex items-center space-x-2 px-4 py-2 bg-yellow-50 border border-yellow-200 rounded-lg h-10">
                <span>💎</span>
                <span className="text-sm text-yellow-800">
                  Подписки: {subscriptionProjects.size}/5
                </span>
              </div>
            </div>

            {/* Clear filters button */}
            {(dateFromFilter || dateToFilter || serviceFilter) && (
              <div className="md:col-span-4 flex justify-start">
                <button
                  onClick={() => {
                    const newRange = getCurrentMonthRange();
                    console.log('Resetting to current month:', newRange);
                    
                    setDateFromFilter(newRange.from);
                    setDateToFilter(newRange.to);
                    setServiceFilter('');
                  }}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-colors flex items-center space-x-2"
                >
                  <span>✕</span>
                  <span>Сбросить к текущему месяцу</span>
                </button>
              </div>
            )}
          </div>
        )}

        {projects.length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
            <div className="text-center">
              <div className="text-gray-400 text-6xl mb-4">📊</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Нет проектов</h3>
              <p className="text-gray-500">Сначала создайте проекты во вкладке "Задачи"</p>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[200px]">
                      Проект
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[150px]">
                      Тип услуги
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[120px]">
                      Исполнитель
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[130px]">
                      Стоимость
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[100px]">
                      Расходы
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider min-w-[100px]">
                      Прибыль
                    </th>
                    <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider w-12">
                      
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filterProjects(projects).map(project => {
                    const data = financialData[project.id];
                    const profit = getProfit(project.id);
                    
                    return (
                      <tr 
                        key={project.id} 
                        className="hover:bg-gray-50 transition-colors duration-150 cursor-pointer"
                        onClick={() => setExpandedProject(expandedProject === project.id ? null : project.id)}
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center space-x-3">
                            {project.logo && (
                              <img src={`${API_URL}/${project.logo}`} alt={project.project} className="w-8 h-8 rounded-full" />
                            )}
                            <div className="flex items-center space-x-2">
                              <div className="text-sm font-medium text-gray-900 truncate max-w-[140px]">
                                {project.project}
                              </div>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  toggleSubscription(project.id);
                                }}
                                className={`p-1 rounded-full transition-all duration-200 ${
                                  subscriptionProjects.has(project.id)
                                  ? 'bg-yellow-100 text-yellow-600 hover:bg-yellow-200' 
                                  : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
                                }`}
                                title={subscriptionProjects.has(project.id) ? "Убрать из подписки" : "Добавить в подписку"}
                                disabled={!subscriptionProjects.has(project.id) && subscriptionProjects.size >= 5}
                              >
                                <span className="text-sm">
                                  {subscriptionProjects.has(project.id) ? '💎' : '◇'}
                                </span>
                              </button>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm text-gray-900">{project.service}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm text-gray-900">{project.executor}</div>
                        </td>
                        <td className="px-6 py-4" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="text"
                            className="text-sm border border-gray-300 rounded-md px-2 py-1 w-32 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            placeholder="0 сум"
                            value={data?.cost_without_tax ? formatCurrency(data.cost_without_tax) : ''}
                            onChange={(e) => {
                              const value = e.target.value.replace(/\D/g, '');
                              handleCostChange(project.id, value);
                            }}
                          />
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-sm font-medium text-red-600">
                            -{formatCurrency(getTotalProjectCosts(project.id))}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`text-sm font-medium ${profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {profit > 0 ? '+' : ''}{formatCurrency(Math.abs(profit))}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedProject(expandedProject === project.id ? null : project.id);
                            }}
                          >
                            <svg 
                              className={`w-4 h-4 transition-transform duration-200 ${expandedProject === project.id ? 'rotate-180' : ''}`}
                              fill="none" 
                              stroke="currentColor" 
                              viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Expanded expenses section */}
        {expandedProject && (
          <div className="mt-6 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Детали проекта: {projects.find(p => p.id === expandedProject)?.project}
                </h3>
                <button
                  onClick={() => setShowExpenseModal(expandedProject)}
                  className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white px-4 py-2 rounded-lg font-medium shadow-lg transform hover:scale-105 transition-all duration-200 flex items-center space-x-2"
                >
                  <span>+</span>
                  <span>Добавить расход</span>
                </button>
              </div>

              {/* Financial details */}
              <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Tax selection */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Вид налога
                  </label>
                  <select
                    className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    value={financialData[expandedProject]?.tax_id || ''}
                    onChange={(e) => handleTaxChange(expandedProject, parseInt(e.target.value))}
                  >
                    <option value="">Выберите налог</option>
                    {taxes.map(tax => (
                      <option key={tax.id} value={tax.id}>
                        {tax.name} (коэф. {tax.rate})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Tax amount */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Сумма налога
                  </label>
                  <div className="text-lg font-semibold text-red-600">
                    -{formatCurrency(getTaxAmount(expandedProject))}
                  </div>
                </div>

                {/* Project expenses */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Расходы проекта
                  </label>
                  <div className="text-lg font-semibold text-red-600">
                    -{formatCurrency(getTotalExpenses(expandedProject))}
                  </div>
                </div>

                {/* Executor percentage */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Процент исполнителя (20%)
                    </label>
                    {subscriptionProjects.has(expandedProject) && (
                      <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full flex items-center space-x-1">
                        <span>💎</span>
                        <span>Подписка</span>
                      </span>
                    )}
                  </div>
                  <div className={`text-lg font-semibold ${subscriptionProjects.has(expandedProject) ? 'text-green-600' : 'text-red-600'}`}>
                    {subscriptionProjects.has(expandedProject) 
                      ? '0 сум (включено в ЗП)' 
                      : `-${formatCurrency(getExecutorPercent(expandedProject))}`
                    }
                  </div>
                </div>
              </div>
            </div>
            
            <div className="p-6">
              <h4 className="text-md font-semibold text-gray-900 mb-4">Расходы</h4>
              <div className="space-y-3">
                {(expensesData[expandedProject] || []).map(expense => (
                  <div key={expense.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <div className="flex-1">
                      <div className="text-sm font-medium text-gray-900">{expense.description}</div>
                      <div className="text-xs text-gray-500">{expense.date}</div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className="text-sm font-medium text-red-600">-{formatCurrency(expense.amount)}</span>
                      <button
                        onClick={() => removeExpense(expandedProject, expense.id)}
                        className="text-red-500 hover:text-red-700 text-sm"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
                
                {(expensesData[expandedProject] || []).length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    Нет расходов для этого проекта
                  </div>
                )}
              </div>
              
              <div className="mt-6 pt-4 border-t border-gray-200">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-center">
                    <div className="text-sm text-gray-600 mb-1">Общие расходы проекта</div>
                    <div className="text-2xl font-bold text-blue-600">
                      -{formatCurrency(getTotalProjectCosts(expandedProject))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Add expense modal */}
      {showExpenseModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-96 overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Добавить расход</h3>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Описание расхода
                </label>
                <input
                  type="text"
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  placeholder="Например: Реклама в Google Ads"
                  value={newExpense.description}
                  onChange={(e) => setNewExpense(prev => ({ ...prev, description: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Сумма
                </label>
                <input
                  type="text"
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  placeholder="0 сум"
                  value={newExpense.amount ? formatCurrency(parseFloat(newExpense.amount) || 0) : ''}
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, '');
                    if (value && showExpenseModal) {
                      const taxRate = getExpenseTaxRate(showExpenseModal);
                      const amountWithTax = parseFloat(value) * (1 + taxRate);
                      setNewExpense(prev => ({ 
                        ...prev, 
                        amount: value, 
                        amountWithTax: String(Math.round(amountWithTax))
                      }));
                    } else {
                      setNewExpense(prev => ({ ...prev, amount: value, amountWithTax: '' }));
                    }
                  }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Сумма с учетом налога
                </label>
                <input
                  type="text"
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  placeholder="0 сум"
                  value={newExpense.amountWithTax ? formatCurrency(parseFloat(newExpense.amountWithTax) || 0) : ''}
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, '');
                    if (value && showExpenseModal) {
                      const taxRate = getExpenseTaxRate(showExpenseModal);
                      const baseAmount = parseFloat(value) / (1 + taxRate);
                      setNewExpense(prev => ({ 
                        ...prev, 
                        amountWithTax: value, 
                        amount: String(Math.round(baseAmount))
                      }));
                    } else {
                      setNewExpense(prev => ({ ...prev, amountWithTax: value, amount: '' }));
                    }
                  }}
                />
              </div>
            </div>
            <div className="p-6 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
              <button
                className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100 transition-colors font-medium"
                onClick={() => {
                  setShowExpenseModal(null);
                  setNewExpense({ description: '', amount: '', amountWithTax: '' });
                }}
              >
                Отмена
              </button>
              <button
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={() => addExpense(showExpenseModal)}
                disabled={!newExpense.description.trim() || (!newExpense.amount && !newExpense.amountWithTax)}
              >
                Добавить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
