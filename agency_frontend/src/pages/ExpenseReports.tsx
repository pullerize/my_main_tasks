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

interface ProjectExpenseSummary {
  project_id: number;
  project_name: string;
  project_costs: number;
  employee_expenses: number;
  operator_expenses: number;
  total_expenses: number;
}

interface Project {
  id: number;
  name: string;
}

interface EmployeeExpense {
  id: number;
  name: string;
  amount: number;
  description?: string;
  date: string;
  user_id: number;
  project_id?: number;
  created_at?: string;
  user?: User;
  project?: Project;
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
  console.log('=== ExpenseReports component mounted ===');
  const [summary, setSummary] = useState<ExpenseReportSummary | null>(null);
  const [employeeReports, setEmployeeReports] = useState<EmployeeExpenseReport[]>([]);
  const [operatorReports, setOperatorReports] = useState<OperatorExpenseReport[]>([]);
  const [projectExpenseReports, setProjectExpenseReports] = useState<ProjectExpenseReport[]>([]);
  const [projectExpenseSummary, setProjectExpenseSummary] = useState<ProjectExpenseSummary[]>([]);
  const [employeeExpensesWithProject, setEmployeeExpensesWithProject] = useState<EmployeeExpense[]>([]);
  const [employeeExpensesWithoutProject, setEmployeeExpensesWithoutProject] = useState<EmployeeExpense[]>([]);
  const [commonExpenses, setCommonExpenses] = useState<CommonExpense[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('project-expenses');
  const [projectSubTab, setProjectSubTab] = useState('summary');
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  const [expandedEmployee, setExpandedEmployee] = useState<number | null>(null);
  const [expandedProject, setExpandedProject] = useState<number | null>(null);
  const [employeeTableExpanded, setEmployeeTableExpanded] = useState(true);
  const [operatorTableExpanded, setOperatorTableExpanded] = useState(true);
  const [projectTableExpanded, setProjectTableExpanded] = useState(true);
  const [companyTableExpanded, setCompanyTableExpanded] = useState(true);
  const [selectedExpense, setSelectedExpense] = useState<any>(null);
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [newExpense, setNewExpense] = useState({
    name: '',
    amount: '',
    description: '',
    project_id: ''
  });
  
  const [filters, setFilters] = useState({
    start_date: getCurrentMonthStart(),
    end_date: getCurrentMonthEnd()
  });

  const roleOptions = [
    { value: '', label: 'Все роли' },
    { value: 'admin', label: 'Администратор' },
    { value: 'smm_manager', label: 'SMM менеджер' },
    { value: 'designer', label: 'Дизайнер' },
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
    loadReports(); // Load reports on mount
  }, []);

  useEffect(() => {
    loadReports();
  }, [filters, selectedProject, activeTab]); // Added activeTab to dependencies

  const loadInitialData = async () => {
    try {
      const [categoriesRes, projectsRes] = await Promise.all([
        authFetch(`${API_URL}/expense-categories/`),
        authFetch(`${API_URL}/projects`)
      ]);

      setCategories(await categoriesRes.json());
      setProjects(await projectsRes.json());
    } catch (error) {
      console.error('Failed to load initial data:', error);
    }
  };

  const loadReports = async () => {
    console.log('[DEBUG] loadReports called, activeTab:', activeTab);
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

      // Build query params for project summary with dates
      const projectSummaryParams = new URLSearchParams();
      if (selectedProject) projectSummaryParams.append('project_id', String(selectedProject));
      if (filters.start_date) projectSummaryParams.append('start_date', filters.start_date);
      if (filters.end_date) projectSummaryParams.append('end_date', filters.end_date);
      console.log('[DEBUG] Project summary params:', projectSummaryParams.toString(), 'filters:', filters);

      // Build query params for employee expenses - ALWAYS fetch all with all_users=true
      const employeeExpensesParams = new URLSearchParams();
      employeeExpensesParams.append('all_users', 'true'); // Get all users' expenses for reports
      // Don't add date filters here - we want all expenses for the general tab
      console.log('[DEBUG] Employee expenses params:', employeeExpensesParams.toString());
      console.log('[DEBUG] About to fetch:', `${API_URL}/employee-expenses/?${employeeExpensesParams}`);

      console.log('[DEBUG] Building requests array...');
      const requests = [
        authFetch(`${API_URL}/expense-reports/summary?${queryParams}`),
        authFetch(`${API_URL}/expense-reports/employees?${queryParams}`),
        authFetch(`${API_URL}/expense-reports/operators?${queryParams}`),
        authFetch(`${API_URL}/employee-expenses/?${employeeExpensesParams}`),
        authFetch(`${API_URL}/common-expenses/?${queryParams}&limit=1000`),
        authFetch(`${API_URL}/projects`)
      ];
      console.log('[DEBUG] Requests array length:', requests.length);

      // Only fetch project-specific data if on project-expenses tab
      if (activeTab === 'project-expenses') {
        requests.push(
          authFetch(`${API_URL}/project-expenses/detailed?${projectQueryParams}`),
          authFetch(`${API_URL}/expense-reports/projects?${projectSummaryParams}`)
        );
      }

      const responses = await Promise.all(requests);

      setSummary(await responses[0].json());
      setEmployeeReports(await responses[1].json());
      setOperatorReports(await responses[2].json());

      // Employee expenses
      const employeeExpensesData = await responses[3].json();
      console.log('[DEBUG] Employee expenses data received from backend:', employeeExpensesData.length, 'items');
      console.log('[DEBUG] First few items:', employeeExpensesData.slice(0, 3));

      const commonExpensesData = await responses[4].json();
      console.log('Common expenses data:', commonExpensesData);
      setCommonExpenses(commonExpensesData);

      // Set projects
      setProjects(await responses[5].json());

      // Handle project-specific data
      if (activeTab === 'project-expenses' && responses.length > 6) {
        const projectExpensesData = await responses[6].json();
        const groupedProjectExpenses = groupProjectExpensesByProject(projectExpensesData);
        setProjectExpenseReports(groupedProjectExpenses);
        setProjectExpenseSummary(await responses[7].json());
      }

      // Split employee expenses into two groups: with project and without project
      // For "with project" - apply selectedProject filter if set
      const withProject = employeeExpensesData.filter((expense: EmployeeExpense) =>
        selectedProject ? expense.project_id === selectedProject : expense.project_id
      );
      // For "without project" - always show all expenses without project_id (no filter)
      const withoutProject = employeeExpensesData.filter((expense: EmployeeExpense) => !expense.project_id);

      console.log('[DEBUG] With project filter (selectedProject=' + selectedProject + '):', withProject.length, 'items');
      console.log('[DEBUG] Without project (all):', withoutProject.length, 'items');
      setEmployeeExpensesWithProject(withProject);
      setEmployeeExpensesWithoutProject(withoutProject);

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
    console.log('[DEBUG] setDateFilter called with:', dates);
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

  const handleCreateExpense = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newExpense.name || !newExpense.amount || !newExpense.project_id) {
      alert('Пожалуйста, заполните все обязательные поля');
      return;
    }

    try {
      const response = await authFetch(`${API_URL}/employee-expenses`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...newExpense,
          amount: parseFloat(newExpense.amount),
          project_id: parseInt(newExpense.project_id)
        }),
      });

      if (response.ok) {
        setNewExpense({ name: '', amount: '', description: '', project_id: '' });
        loadReports();
      }
    } catch (error) {
      console.error('Error creating expense:', error);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
    }).format(amount);
  };

  const handleExpenseClick = (expense: any, type: 'employee' | 'project' | 'common') => {
    console.log('Expense clicked:', expense, 'Type:', type);
    setSelectedExpense({ ...expense, type });
    setShowExpenseModal(true);
    console.log('Modal should show now, selectedExpense:', { ...expense, type }, 'showModal:', true);
  };

  const closeExpenseModal = () => {
    setShowExpenseModal(false);
    setSelectedExpense(null);
  };

  const ExpenseDetailModal = () => {
    console.log('ExpenseDetailModal render check:', { selectedExpense, showExpenseModal });
    console.log('ExpenseDetailModal - selectedExpense type:', typeof selectedExpense);
    console.log('ExpenseDetailModal - showExpenseModal type:', typeof showExpenseModal);

    if (!selectedExpense || !showExpenseModal) {
      console.log('ExpenseDetailModal - not rendering because:', {
        hasSelectedExpense: !!selectedExpense,
        showModal: showExpenseModal
      });
      return null;
    }

    console.log('ExpenseDetailModal - rendering modal');

    return (
      <div
        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999]"
        onClick={closeExpenseModal}
      >
        <div
          className="bg-white rounded-lg p-6 max-w-md w-full mx-4 relative z-[10000]"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Подробная информация о расходе</h3>
            <button
              onClick={closeExpenseModal}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Название</label>
              <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{selectedExpense.name}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Сумма</label>
              <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{formatCurrency(selectedExpense.amount)}</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Дата</label>
              <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">
                {new Date(selectedExpense.date).toLocaleDateString('ru-RU')}
              </p>
            </div>

            {selectedExpense.description && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Описание</label>
                <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{selectedExpense.description}</p>
              </div>
            )}

            {selectedExpense.type === 'employee' && selectedExpense.user && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Сотрудник</label>
                <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{selectedExpense.user.name}</p>
              </div>
            )}

            {selectedExpense.type === 'employee' && selectedExpense.project && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Проект</label>
                <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{selectedExpense.project.name}</p>
              </div>
            )}

            {selectedExpense.type === 'project' && selectedExpense.project_name && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Проект</label>
                <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{selectedExpense.project_name}</p>
              </div>
            )}

            {selectedExpense.category_name && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Категория</label>
                <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{selectedExpense.category_name}</p>
              </div>
            )}

            {selectedExpense.creator_name && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Создал</label>
                <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{selectedExpense.creator_name}</p>
              </div>
            )}

            {selectedExpense.created_at && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Дата создания</label>
                <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">
                  {new Date(selectedExpense.created_at).toLocaleString('ru-RU')}
                </p>
              </div>
            )}
          </div>

          <div className="mt-6 flex justify-end">
            <button
              onClick={closeExpenseModal}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              Закрыть
            </button>
          </div>
        </div>
      </div>
    );
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
    <div className="bg-gray-50 min-h-screen">
      <div className="w-full">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex justify-between items-center mb-6">
            <h1 className="text-2xl font-bold text-gray-900">Отчеты по расходам</h1>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  console.log('Test modal button clicked');
                  setSelectedExpense({
                    id: 999,
                    name: 'Тестовый расход',
                    amount: 1000,
                    date: '2024-01-01',
                    description: 'Тестовое описание',
                    type: 'test'
                  });
                  setShowExpenseModal(true);
                }}
                className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                🧪 Тест модалки
              </button>
              <button
                onClick={exportToCSV}
                className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
              >
                <Download size={16} />
                Экспорт CSV
              </button>
            </div>
          </div>

          {/* Main Tabs */}
          <div className="border-b border-gray-200 mb-6">
            <nav className="flex space-x-8">
              {[
                { key: 'project-expenses', label: 'Расходы по проектам', icon: '📊' },
                { key: 'general-expenses', label: 'Общие расходы организации', icon: '🏢' }
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                    activeTab === tab.key
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span>{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Date Filters - only for project expenses */}
          {activeTab === 'project-expenses' && (
            <div className="space-y-4">
              {/* Project Filter */}
              <div className="flex justify-between items-center">
                <select
                  value={selectedProject?.toString() || ''}
                  onChange={(e) => setSelectedProject(e.target.value ? parseInt(e.target.value) : null)}
                  className="border border-gray-300 rounded-md px-3 py-2 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Все проекты</option>
                  {projects.map(project => (
                    <option key={project.id} value={project.id.toString()}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>

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
          )}
        </div>

        {/* Tab Content */}
        {activeTab === 'project-expenses' && (
          <div className="bg-white rounded-lg shadow-sm">
            <div className="border-b border-gray-200">
              <nav className="flex space-x-8 px-6">
                {[
                  { key: 'summary', label: 'Сводка', icon: '📊' },
                  { key: 'project-costs', label: 'Затраты на проект', icon: '💰' },
                  { key: 'operator-expenses', label: 'Расходы операторов', icon: '🎥' },
                  { key: 'employee-expenses', label: 'Расходы сотрудников', icon: '👥' }
                ].map(tab => (
                  <button
                    key={tab.key}
                    onClick={() => setProjectSubTab(tab.key)}
                    className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center gap-2 ${
                      projectSubTab === tab.key
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    <span>{tab.icon}</span>
                    {tab.label}
                  </button>
                ))}
              </nav>
            </div>

            {/* Project Sub-tab Content */}
            {projectSubTab === 'summary' && (
              <div className="p-6">
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {projectExpenseSummary.map((project) => (
                    <div key={project.project_id} className="bg-white border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="text-sm font-medium text-gray-900">{project.project_name}</h3>
                        <span className="text-blue-500">📊</span>
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Затраты на проект:</span>
                          <span className="text-sm">{formatCurrency(project.project_costs)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Расходы операторов:</span>
                          <span className="text-sm">{formatCurrency(project.operator_expenses)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Расходы сотрудников:</span>
                          <span className="text-sm">{formatCurrency(project.employee_expenses)}</span>
                        </div>
                        <div className="flex justify-between border-t pt-2">
                          <span className="font-medium">Итого:</span>
                          <span className="font-medium">{formatCurrency(project.total_expenses)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {projectSubTab === 'project-costs' && (
              <div className="p-6">
                <div className="mb-4">
                  <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    <span className="text-green-500">📈</span>
                    Затраты на проекты
                  </h2>
                </div>
                <div className="space-y-4">
                  {projectExpenseSummary.map((project) => (
                    <div key={project.project_id} className="flex justify-between items-center p-4 border border-gray-200 rounded-lg">
                      <div>
                        <h3 className="font-medium">{project.project_name}</h3>
                        <p className="text-sm text-gray-600">Прямые затраты проекта</p>
                      </div>
                      <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded-md text-sm font-medium">
                        {formatCurrency(project.project_costs)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {projectSubTab === 'operator-expenses' && (
              <div className="p-6">
                <div className="mb-4">
                  <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                    <span className="text-yellow-500">💰</span>
                    Расходы операторов
                  </h2>
                </div>
                <div className="text-center py-8 text-gray-500">
                  <p>Интеграция с календарем съемок в разработке</p>
                  <p className="text-sm mt-2">Здесь будут отображаться расходы операторов по проектам</p>
                </div>
              </div>
            )}

            {projectSubTab === 'employee-expenses' && (
              <div className="p-6 space-y-6">
                <div className="border border-gray-200 rounded-lg p-6">
                  <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-4">
                    <span className="text-blue-500">➕</span>
                    Добавить расход сотрудника
                  </h2>
                  <form onSubmit={handleCreateExpense} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <input
                        type="text"
                        placeholder="Название расхода"
                        value={newExpense.name}
                        onChange={(e) => setNewExpense({...newExpense, name: e.target.value})}
                        className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      />
                      <input
                        type="number"
                        placeholder="Сумма"
                        value={newExpense.amount}
                        onChange={(e) => setNewExpense({...newExpense, amount: e.target.value})}
                        className="border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      />
                    </div>
                    <input
                      type="text"
                      placeholder="Описание (необязательно)"
                      value={newExpense.description}
                      onChange={(e) => setNewExpense({...newExpense, description: e.target.value})}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <select
                      value={newExpense.project_id}
                      onChange={(e) => setNewExpense({...newExpense, project_id: e.target.value})}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    >
                      <option value="">Выберите проект</option>
                      {projects.map(project => (
                        <option key={project.id} value={project.id.toString()}>
                          {project.name}
                        </option>
                      ))}
                    </select>
                    <button
                      type="submit"
                      className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      Добавить расход
                    </button>
                  </form>
                </div>

                <div className="border border-gray-200 rounded-lg p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-4">
                    Расходы сотрудников ({employeeExpensesWithProject.length})
                  </h2>
                  <div className="mb-2 text-xs text-gray-500">
                    Debug: employeeExpensesWithProject.length = {employeeExpensesWithProject.length}<br/>
                    Debug: selectedProject = {selectedProject}<br/>
                    Debug: loading = {loading.toString()}
                  </div>
                  <div className="space-y-4">
                    {employeeExpensesWithProject.length === 0 ? (
                      <p className="text-center text-gray-500 py-4">
                        Нет расходов сотрудников для выбранного проекта
                      </p>
                    ) : (
                      employeeExpensesWithProject.map((expense) => (
                        <div
                          key={expense.id}
                          className="flex justify-between items-center p-4 border border-gray-200 rounded-lg cursor-pointer hover:bg-blue-50 hover:border-blue-300 transition-colors"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            console.log('Employee expense clicked:', expense);
                            handleExpenseClick(expense, 'employee');
                          }}
                          style={{ minHeight: '60px' }}
                        >
                          <div>
                            <h3 className="font-medium">{expense.name}</h3>
                            <p className="text-sm text-gray-600">
                              {expense.user?.name} • {expense.project?.name} • {new Date(expense.date).toLocaleDateString('ru-RU')}
                            </p>
                            {expense.description && (
                              <p className="text-sm text-gray-600 mt-1">{expense.description}</p>
                            )}
                          </div>
                          <span className="px-2 py-1 border border-gray-300 rounded-md text-sm">
                            {formatCurrency(expense.amount)}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'general-expenses' && (
          <div className="space-y-6">
            {/* Common Expenses */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-6">
                <span className="text-orange-500">🏢</span>
                Общие расходы организации ({commonExpenses.length})
              </h2>

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
                      <tr
                        key={expense.id}
                        className="hover:bg-blue-50 cursor-pointer transition-colors"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          console.log('Common expense clicked:', expense);
                          handleExpenseClick(expense, 'common');
                        }}
                      >
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
                          Нет данных об общих расходах организации
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Employee Expenses Without Project */}
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2 mb-6">
                <span className="text-blue-500">👥</span>
                Расходы сотрудников без привязки к проектам ({employeeExpensesWithoutProject.length})
              </h2>
              <div className="mb-4 text-xs text-gray-500">
                Debug: employeeExpensesWithoutProject.length = {employeeExpensesWithoutProject.length}<br/>
                Debug: First item: {JSON.stringify(employeeExpensesWithoutProject[0])}<br/>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full table-auto">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Дата</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Название</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Сотрудник</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-gray-900">Сумма</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-gray-900">Описание</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {employeeExpensesWithoutProject.map((expense) => (
                      <tr
                        key={expense.id}
                        className="hover:bg-blue-50 cursor-pointer transition-colors"
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          console.log('Employee expense clicked:', expense);
                          handleExpenseClick(expense, 'employee');
                        }}
                      >
                        <td className="px-4 py-3">
                          <span className="text-sm">
                            {new Date(expense.date).toLocaleDateString('ru-RU')}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="font-medium text-gray-900">
                            {expense.name}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-sm text-gray-600">
                            {expense.user?.name || 'Неизвестно'}
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
                      </tr>
                    ))}
                    {employeeExpensesWithoutProject.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                          Нет расходов сотрудников без привязки к проектам
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Expense Detail Modal */}
        <ExpenseDetailModal />
      </div>
    </div>
  );
};

export default ExpenseReports;