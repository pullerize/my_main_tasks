import React, { useState, useEffect } from 'react';
import { 
  Filter, 
  Download, 
  Calendar, 
  TrendingUp, 
  DollarSign, 
  Building, 
  Users,
  Video,
  ChevronDown,
  ChevronUp,
  User,
  FolderOpen
} from 'lucide-react';
import { authFetch, API_URL } from '../api';

interface ExpenseReportSummary {
  total_expenses: number;
  project_expenses: number;
  employee_expenses: number;
}

interface EmployeeExpense {
  id: number;
  name: string;
  amount: number;
  description?: string;
  date: string;
  user_id: number;
}

interface EmployeeExpenseReport {
  user_id: number;
  user_name: string;
  role: string;
  total_amount: number;
  expenses: EmployeeExpense[];
}

interface OperatorExpenseReport {
  operator_id: number;
  operator_name: string;
  role: string;
  is_salaried: boolean;
  monthly_salary?: number;
  price_per_video?: number;
  videos_completed: number;
  total_amount: number;
}

interface ProjectExpense {
  id: number;
  project_id: number;
  project_name: string;
  category_id?: number;
  category_name?: string;
  name: string;
  amount: number;
  description?: string;
  date: string;
  created_at: string;
  created_by?: number;
  creator_name?: string;
}

interface ProjectExpenseReport {
  project_id: number;
  project_name: string;
  total_amount: number;
  expenses: ProjectExpense[];
}

interface Category {
  id: number;
  name: string;
}

interface CommonExpense {
  id: number;
  category_id?: number;
  category_name?: string;
  name: string;
  amount: number;
  description?: string;
  date: string;
  created_at: string;
  created_by?: number;
  creator_name?: string;
}

interface User {
  id: number;
  name: string;
  role: string;
}

interface Project {
  id: number;
  name: string;
}

const ExpenseReports: React.FC = () => {
  const [summary, setSummary] = useState<ExpenseReportSummary | null>(null);
  const [employeeReports, setEmployeeReports] = useState<EmployeeExpenseReport[]>([]);
  const [operatorReports, setOperatorReports] = useState<OperatorExpenseReport[]>([]);
  const [projectExpenseReports, setProjectExpenseReports] = useState<ProjectExpenseReport[]>([]);
  const [commonExpenses, setCommonExpenses] = useState<CommonExpense[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedEmployee, setExpandedEmployee] = useState<number | null>(null);
  const [expandedProject, setExpandedProject] = useState<number | null>(null);
  const [employeeTableExpanded, setEmployeeTableExpanded] = useState(true);
  const [operatorTableExpanded, setOperatorTableExpanded] = useState(true);
  const [projectTableExpanded, setProjectTableExpanded] = useState(true);
  const [companyTableExpanded, setCompanyTableExpanded] = useState(true);
  
  const [filters, setFilters] = useState({
    start_date: getCurrentMonthStart(),
    end_date: getCurrentMonthEnd()
  });

  const roleOptions = [
    { value: '', label: 'Все роли' },
    { value: 'admin', label: 'Администратор' },
    { value: 'smm_manager', label: 'SMM менеджер' },
    { value: 'head_smm', label: 'Главный SMM' },
    { value: 'designer', label: 'Дизайнер' },
    { value: 'digital', label: 'Digital' },
  ];

  function getCurrentMonthStart() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0'); // +1 because getMonth() is 0-based
    return `${year}-${month}-01`;
  }

  function getCurrentMonthEnd() {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1; // +1 because getMonth() is 0-based
    const lastDay = new Date(year, month, 0).getDate(); // 0 day of next month = last day of current month
    const monthStr = String(month).padStart(2, '0');
    const dayStr = String(lastDay).padStart(2, '0');
    return `${year}-${monthStr}-${dayStr}`;
  }

  function getTodayDates() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`;
    return { start_date: dateStr, end_date: dateStr };
  }

  function getCurrentWeekDates() {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek; // Monday is 1, Sunday is 0
    
    const monday = new Date(today);
    monday.setDate(today.getDate() + mondayOffset);
    
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    
    const formatDate = (date: Date) => {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    };
    
    return {
      start_date: formatDate(monday),
      end_date: formatDate(sunday)
    };
  }

  function getCurrentYearDates() {
    const now = new Date();
    const year = now.getFullYear();
    return {
      start_date: `${year}-01-01`,
      end_date: `${year}-12-31`
    };
  }

  function formatNumber(num: number): string {
    return num.toLocaleString('ru-RU').replace(/,/g, ' ');
  }

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    loadReports();
  }, [filters]);

  const loadInitialData = async () => {
    try {
      const [categoriesRes] = await Promise.all([
        authFetch(`${API_URL}/expense-categories/`)
      ]);
      
      setCategories(await categoriesRes.json());
    } catch (error) {
      console.error('Failed to load initial data:', error);
    }
  };

  const loadReports = async () => {
    setLoading(true);
    try {
      const queryParams = new URLSearchParams();
      if (filters.start_date) queryParams.append('start_date', filters.start_date);
      if (filters.end_date) queryParams.append('end_date', filters.end_date);

      // For project expenses, we need different query params
      const projectQueryParams = new URLSearchParams();
      if (filters.start_date) projectQueryParams.append('start_date', filters.start_date);
      if (filters.end_date) projectQueryParams.append('end_date', filters.end_date);
      projectQueryParams.append('limit', '1000');

      const [summaryRes, employeesRes, operatorsRes, projectExpensesRes, commonExpensesRes] = await Promise.all([
        authFetch(`${API_URL}/expense-reports/summary?${queryParams}`),
        authFetch(`${API_URL}/expense-reports/employees?${queryParams}`),
        authFetch(`${API_URL}/expense-reports/operators?${queryParams}`),
        authFetch(`${API_URL}/project-expenses/detailed?${projectQueryParams}`),
        authFetch(`${API_URL}/common-expenses/?${queryParams}&limit=1000`)
      ]);

      setSummary(await summaryRes.json());
      setEmployeeReports(await employeesRes.json());
      setOperatorReports(await operatorsRes.json());
      setCommonExpenses(await commonExpensesRes.json());
      
      // Group project expenses by project
      const projectExpensesData = await projectExpensesRes.json();
      const groupedProjectExpenses = groupProjectExpensesByProject(projectExpensesData);
      setProjectExpenseReports(groupedProjectExpenses);
    } catch (error) {
      console.error('Failed to load reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const resetFilters = () => {
    setFilters({
      start_date: getCurrentMonthStart(),
      end_date: getCurrentMonthEnd()
    });
  };

  const setDateFilter = (dates: { start_date: string; end_date: string }) => {
    setFilters(dates);
  };

  const toggleEmployeeExpanded = (userId: number) => {
    setExpandedEmployee(expandedEmployee === userId ? null : userId);
  };

  const toggleProjectExpanded = (projectId: number) => {
    setExpandedProject(expandedProject === projectId ? null : projectId);
  };

  const groupProjectExpensesByProject = (expenses: ProjectExpense[]): ProjectExpenseReport[] => {
    const grouped = expenses.reduce((acc, expense) => {
      const projectId = expense.project_id;
      if (!acc[projectId]) {
        acc[projectId] = {
          project_id: projectId,
          project_name: expense.project_name,
          total_amount: 0,
          expenses: []
        };
      }
      acc[projectId].expenses.push(expense);
      acc[projectId].total_amount += expense.amount;
      return acc;
    }, {} as Record<number, ProjectExpenseReport>);

    return Object.values(grouped);
  };

  const exportToCSV = () => {
    const csvData = [
      ['Тип', 'Наименование', 'Роль/Проект', 'Сумма (сум)', 'Дата', 'Описание'],
      ...employeeReports.map(emp => [
        'Сотрудник',
        emp.user_name,
        emp.role,
        emp.total_amount,
        '',
        ''
      ]),
      ...operatorReports.map(op => [
        'Оператор',
        op.operator_name,
        op.role === 'mobile' ? 'Мобилограф' : 'Видеограф',
        op.total_amount,
        '',
        ''
      ]),
      ...projectExpenseReports.flatMap(project => 
        project.expenses.map(exp => [
          'Проект',
          exp.name,
          project.project_name,
          exp.amount,
          new Date(exp.date).toLocaleDateString('ru-RU'),
          exp.description || ''
        ])
      ),
      ...commonExpenses.map(exp => [
        'Организация',
        exp.name,
        exp.category_name || 'Без категории',
        exp.amount,
        new Date(exp.date).toLocaleDateString('ru-RU'),
        exp.description || ''
      ])
    ];

    const csvContent = csvData.map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `expense-report-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const getRoleLabel = (role: string): string => {
    const option = roleOptions.find(r => r.value === role);
    return option ? option.label : role;
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Загружаем отчеты по расходам...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold text-gray-900">Отчеты по расходам</h1>
            <button
              onClick={exportToCSV}
              className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
            >
              <Download size={16} />
              Экспорт CSV
            </button>
          </div>

          {/* Date Filters */}
          <div className="space-y-4">
            {/* Quick Date Buttons */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setDateFilter(getTodayDates())}
                className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors text-sm font-medium"
              >
                За сегодня
              </button>
              <button
                onClick={() => setDateFilter(getCurrentWeekDates())}
                className="px-4 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors text-sm font-medium"
              >
                За неделю
              </button>
              <button
                onClick={() => setDateFilter({ start_date: getCurrentMonthStart(), end_date: getCurrentMonthEnd() })}
                className="px-4 py-2 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition-colors text-sm font-medium"
              >
                За месяц
              </button>
              <button
                onClick={() => setDateFilter(getCurrentYearDates())}
                className="px-4 py-2 bg-orange-100 text-orange-700 rounded-lg hover:bg-orange-200 transition-colors text-sm font-medium"
              >
                За год
              </button>
            </div>
            
            {/* Custom Date Range */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Дата от
                </label>
                <input
                  type="date"
                  value={filters.start_date}
                  onChange={(e) => handleFilterChange('start_date', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Дата до
                </label>
                <input
                  type="date"
                  value={filters.end_date}
                  onChange={(e) => handleFilterChange('end_date', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={resetFilters}
                  className="w-full flex items-center justify-center gap-2 bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
                >
                  <Filter size={16} />
                  Сброс
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Summary Cards - не зависят от фильтров */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <DollarSign className="h-6 w-6 text-blue-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Общие расходы</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatNumber(summary.total_expenses)} сум
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Building className="h-6 w-6 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Проектные расходы</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatNumber(summary.project_expenses)} сум
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Users className="h-6 w-6 text-purple-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Расходы сотрудников</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {formatNumber(summary.employee_expenses)} сум
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Employee Expenses Table */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Users className="h-5 w-5 text-blue-600" />
                Расходы сотрудников
              </h2>
              <button
                onClick={() => setEmployeeTableExpanded(!employeeTableExpanded)}
                className="p-1 text-gray-500 hover:text-gray-700 transition-colors"
                title={employeeTableExpanded ? "Свернуть таблицу" : "Развернуть таблицу"}
              >
                {employeeTableExpanded ? (
                  <ChevronUp className="h-5 w-5" />
                ) : (
                  <ChevronDown className="h-5 w-5" />
                )}
              </button>
            </div>
            <div className="bg-gradient-to-r from-purple-100 to-purple-50 px-4 py-2 rounded-lg border border-purple-200">
              <div className="text-sm text-purple-600 font-medium">Общая сумма</div>
              <div className="text-xl font-bold text-purple-900">
                {formatNumber(employeeReports.reduce((sum, report) => sum + report.total_amount, 0))} сум
              </div>
            </div>
          </div>
          {employeeTableExpanded && (
            <div className="overflow-x-auto">
              <table className="w-full table-auto">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Сотрудник</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Роль</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">Общие расходы</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-900">Действия</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {employeeReports.map((report) => (
                  <React.Fragment key={report.user_id}>
                    <tr className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4 text-gray-400" />
                          <span className="font-medium text-gray-900">{report.user_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
                          {getRoleLabel(report.role)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-semibold text-gray-900">
                          {formatNumber(report.total_amount)} сум
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {report.expenses.length > 0 && (
                          <button
                            onClick={() => toggleEmployeeExpanded(report.user_id)}
                            className="text-blue-600 hover:text-blue-800"
                          >
                            {expandedEmployee === report.user_id ? (
                              <ChevronUp className="h-5 w-5" />
                            ) : (
                              <ChevronDown className="h-5 w-5" />
                            )}
                          </button>
                        )}
                      </td>
                    </tr>
                    {expandedEmployee === report.user_id && (
                      <tr>
                        <td colSpan={4} className="px-8 py-4 bg-gray-50">
                          <div className="space-y-2">
                            <h4 className="font-medium text-gray-700 mb-2">Детализация расходов:</h4>
                            {report.expenses.map((expense) => (
                              <div key={expense.id} className="flex justify-between items-center py-2 border-b border-gray-200">
                                <div>
                                  <span className="font-medium">{expense.name}</span>
                                  {expense.description && (
                                    <span className="text-sm text-gray-500 ml-2">({expense.description})</span>
                                  )}
                                </div>
                                <div className="text-right">
                                  <span className="font-medium">{formatNumber(expense.amount)} сум</span>
                                  <span className="text-sm text-gray-500 ml-2">
                                    {new Date(expense.date).toLocaleDateString('ru-RU')}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
                {employeeReports.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                      Нет данных о расходах сотрудников
                    </td>
                  </tr>
                )}
              </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Operator Expenses Table */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <Video className="h-5 w-5 text-purple-600" />
                Расходы операторов
              </h2>
              <button
                onClick={() => setOperatorTableExpanded(!operatorTableExpanded)}
                className="p-1 text-gray-500 hover:text-gray-700 transition-colors"
                title={operatorTableExpanded ? "Свернуть таблицу" : "Развернуть таблицу"}
              >
                {operatorTableExpanded ? (
                  <ChevronUp className="h-5 w-5" />
                ) : (
                  <ChevronDown className="h-5 w-5" />
                )}
              </button>
            </div>
            <div className="bg-gradient-to-r from-orange-100 to-orange-50 px-4 py-2 rounded-lg border border-orange-200">
              <div className="text-sm text-orange-600 font-medium">Общая сумма</div>
              <div className="text-xl font-bold text-orange-900">
                {formatNumber(operatorReports.reduce((sum, report) => sum + report.total_amount, 0))} сум
              </div>
            </div>
          </div>
          {operatorTableExpanded && (
            <div className="overflow-x-auto">
              <table className="w-full table-auto">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Оператор</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Роль</th>
                  <th className="px-4 py-3 text-center text-sm font-medium text-gray-900">Видео завершено</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">Ставка</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">Общая сумма</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {operatorReports.map((report) => (
                  <tr key={report.operator_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <span className="font-medium text-gray-900">{report.operator_name}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        report.role === 'mobile' 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-purple-100 text-purple-800'
                      }`}>
                        {report.role === 'mobile' ? 'Мобилограф' : 'Видеограф'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {report.is_salaried ? (
                        <div>
                          <span className="font-medium">{report.videos_completed}</span>
                          <div className="text-xs text-gray-500">не влияет на оплату</div>
                        </div>
                      ) : (
                        <span className="font-medium">{report.videos_completed}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {report.is_salaried ? (
                        <div>
                          <span className="text-sm text-gray-600">Зарплата: </span>
                          <span className="font-medium">{formatNumber(report.monthly_salary || 0)} сум/мес</span>
                        </div>
                      ) : (
                        <div>
                          <span className="text-sm text-gray-600">За видео: </span>
                          <span className="font-medium">{formatNumber(report.price_per_video || 0)} сум</span>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="font-semibold text-gray-900">
                        {formatNumber(report.total_amount)} сум
                      </span>
                    </td>
                  </tr>
                ))}
                {operatorReports.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                      Нет данных о расходах операторов
                    </td>
                  </tr>
                )}
              </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Project Expenses Table */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <FolderOpen className="h-5 w-5 text-green-600" />
                Расходы по проектам
              </h2>
              <button
                onClick={() => setProjectTableExpanded(!projectTableExpanded)}
                className="p-1 text-gray-500 hover:text-gray-700 transition-colors"
                title={projectTableExpanded ? "Свернуть таблицу" : "Развернуть таблицу"}
              >
                {projectTableExpanded ? (
                  <ChevronUp className="h-5 w-5" />
                ) : (
                  <ChevronDown className="h-5 w-5" />
                )}
              </button>
            </div>
            <div className="bg-gradient-to-r from-green-100 to-green-50 px-4 py-2 rounded-lg border border-green-200">
              <div className="text-sm text-green-600 font-medium">Общая сумма</div>
              <div className="text-xl font-bold text-green-900">
                {formatNumber(projectExpenseReports.reduce((sum, report) => sum + report.total_amount, 0))} сум
              </div>
            </div>
          </div>
          {projectTableExpanded && (
            <div className="overflow-x-auto">
              <table className="w-full table-auto">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Проект</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">Общие расходы</th>
                    <th className="px-4 py-3 text-center text-sm font-medium text-gray-900">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {projectExpenseReports.map((report) => (
                    <React.Fragment key={report.project_id}>
                      <tr className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <FolderOpen className="h-4 w-4 text-green-500" />
                            <span className="font-medium text-gray-900">{report.project_name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="font-semibold text-gray-900">
                            {formatNumber(report.total_amount)} сум
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {report.expenses.length > 0 && (
                            <button
                              onClick={() => toggleProjectExpanded(report.project_id)}
                              className="text-green-600 hover:text-green-800"
                            >
                              {expandedProject === report.project_id ? (
                                <ChevronUp className="h-5 w-5" />
                              ) : (
                                <ChevronDown className="h-5 w-5" />
                              )}
                            </button>
                          )}
                        </td>
                      </tr>
                      {expandedProject === report.project_id && (
                        <tr>
                          <td colSpan={3} className="px-8 py-4 bg-gray-50">
                            <div className="space-y-2">
                              <h4 className="font-medium text-gray-700 mb-2">Детализация расходов:</h4>
                              {report.expenses.map((expense) => (
                                <div key={expense.id} className="flex justify-between items-center py-2 border-b border-gray-200">
                                  <div className="flex-1">
                                    <div className="flex items-center justify-between">
                                      <span className="font-medium">{expense.name}</span>
                                      <div className="text-right">
                                        <span className="font-medium">{formatNumber(expense.amount)} сум</span>
                                        <span className="text-sm text-gray-500 ml-2">
                                          {new Date(expense.date).toLocaleDateString('ru-RU')}
                                        </span>
                                      </div>
                                    </div>
                                    <div className="flex items-center justify-between mt-1">
                                      <div className="flex items-center gap-2">
                                        {expense.category_name && (
                                          <span className="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded">
                                            {expense.category_name}
                                          </span>
                                        )}
                                        {expense.description && (
                                          <span className="text-sm text-gray-500">({expense.description})</span>
                                        )}
                                      </div>
                                      {expense.creator_name && (
                                        <span className="text-sm text-gray-500">
                                          Создал: {expense.creator_name}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                  {projectExpenseReports.length === 0 && (
                    <tr>
                      <td colSpan={3} className="px-4 py-8 text-center text-gray-500">
                        Нет данных о расходах по проектам
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Company Expenses Table */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-orange-600" />
                Расходы организации
              </h2>
              <button
                onClick={() => setCompanyTableExpanded(!companyTableExpanded)}
                className="p-1 text-gray-500 hover:text-gray-700 transition-colors"
                title={companyTableExpanded ? "Свернуть таблицу" : "Развернуть таблицу"}
              >
                {companyTableExpanded ? (
                  <ChevronUp className="h-5 w-5" />
                ) : (
                  <ChevronDown className="h-5 w-5" />
                )}
              </button>
            </div>
            <div className="bg-gradient-to-r from-orange-100 to-orange-50 px-4 py-2 rounded-lg border border-orange-200">
              <div className="text-sm text-orange-600 font-medium">Общая сумма</div>
              <div className="text-xl font-bold text-orange-900">
                {formatNumber(commonExpenses.reduce((sum, expense) => sum + expense.amount, 0))} сум
              </div>
            </div>
          </div>
          {companyTableExpanded && (
            <div className="overflow-x-auto">
              <table className="w-full table-auto">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Дата</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Название</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Категория</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">Сумма</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Описание</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Создал</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {commonExpenses.map((expense) => (
                    <tr key={expense.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className="text-sm">
                          {new Date(expense.date).toLocaleDateString('ru-RU')}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Building className="h-4 w-4 text-gray-500" />
                          <span className="font-medium text-gray-900">
                            {expense.name}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
                          {expense.category_name || 'Без категории'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="font-semibold text-gray-900">
                          {formatNumber(expense.amount)} сум
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="max-w-xs">
                          {expense.description ? (
                            <span className="text-sm text-gray-600 truncate" title={expense.description}>
                              {expense.description}
                            </span>
                          ) : (
                            <span className="text-sm text-gray-400">-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-gray-600">
                          {expense.creator_name || 'Неизвестно'}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {commonExpenses.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                        Нет данных о расходах организации
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ExpenseReports;