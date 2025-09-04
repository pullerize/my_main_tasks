import React, { useEffect, useState } from 'react';
import { API_URL } from '../api';
import { formatDateTimeUTC5, formatDeadlineUTC5 } from '../utils/dateUtils';

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
  status: 'in_progress' | 'completed' | 'overdue';
}

interface DigitalTask {
  id: number;
  title: string;
  description: string;
  created_at: string;
  deadline?: string;
  high_priority?: boolean;
  status: 'completed' | 'in_progress';
}

const PROJECT_STATUSES = [
  { value: '', label: 'Все статусы' },
  { value: 'in_progress', label: 'В работе' },
  { value: 'completed', label: 'Завершено' },
  { value: 'overdue', label: 'Просрочено' }
];

const TASK_STATUSES = [
  { value: '', label: 'Все статусы' },
  { value: 'in_progress', label: 'В работе' },
  { value: 'completed', label: 'Завершено' }
];

export default function DigitalReports() {
  const token = localStorage.getItem('token');
  const [projects, setProjects] = useState<DigitalProject[]>([]);
  const [tasks, setTasks] = useState<Record<number, DigitalTask[]>>({});
  const [loading, setLoading] = useState(true);
  const [expandedProject, setExpandedProject] = useState<number | null>(null);
  
  // Фильтры
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [projectStatus, setProjectStatus] = useState('');
  const [taskStatus, setTaskStatus] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_URL}/digital/projects`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        const projectsWithStatus = data.map((project: any) => ({
          ...project,
          status: getProjectStatus(project)
        }));
        setProjects(projectsWithStatus);
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
    setLoading(false);
  };

  const loadTasks = async (projectId: number) => {
    if (!token || tasks[projectId]) return;

    try {
      const response = await fetch(`${API_URL}/digital/projects/${projectId}/tasks`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setTasks(prev => ({
          ...prev,
          [projectId]: data
        }));
      }
    } catch (error) {
      console.error('Failed to load tasks:', error);
    }
  };

  const getProjectStatus = (project: DigitalProject): 'in_progress' | 'completed' | 'overdue' => {
    if (project.status === 'completed') return 'completed';
    if (project.monthly) return 'in_progress';
    if (!project.deadline) return 'in_progress';
    
    const now = new Date();
    const deadline = new Date(project.deadline);
    
    if (deadline < now) return 'overdue';
    return 'in_progress';
  };

  const formatDate = (dateStr: string) => {
    return formatDateTimeUTC5(dateStr);
  };

  const formatDeadline = (dateStr: string) => {
    return formatDeadlineUTC5(dateStr);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'in_progress': return 'bg-blue-100 text-blue-800';
      case 'overdue': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed': return 'Завершено';
      case 'in_progress': return 'В работе';
      case 'overdue': return 'Просрочено';
      default: return status;
    }
  };

  const filteredProjects = projects.filter(project => {
    // Фильтр по дате
    if (dateFrom) {
      const projectDate = new Date(project.created_at);
      const filterFrom = new Date(dateFrom);
      if (projectDate < filterFrom) return false;
    }
    
    if (dateTo) {
      const projectDate = new Date(project.created_at);
      const filterTo = new Date(dateTo);
      filterTo.setHours(23, 59, 59);
      if (projectDate > filterTo) return false;
    }

    // Фильтр по статусу проекта
    if (projectStatus && project.status !== projectStatus) return false;

    return true;
  });

  const filteredTasks = (projectId: number) => {
    const projectTasks = tasks[projectId] || [];
    
    return projectTasks.filter(task => {
      // Фильтр по дате
      if (dateFrom) {
        const taskDate = new Date(task.created_at);
        const filterFrom = new Date(dateFrom);
        if (taskDate < filterFrom) return false;
      }
      
      if (dateTo) {
        const taskDate = new Date(task.created_at);
        const filterTo = new Date(dateTo);
        filterTo.setHours(23, 59, 59);
        if (taskDate > filterTo) return false;
      }

      // Фильтр по статусу задачи
      if (taskStatus && task.status !== taskStatus) return false;

      return true;
    });
  };

  const toggleProject = async (projectId: number) => {
    if (expandedProject === projectId) {
      setExpandedProject(null);
    } else {
      setExpandedProject(projectId);
      await loadTasks(projectId);
    }
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
            <h1 className="text-3xl font-bold text-gray-900">Digital Отчеты</h1>
            <p className="text-gray-600 mt-1">Аналитика и отчетность digital проектов</p>
          </div>
        </div>
      </div>
      
      <div className="p-6">
        {/* Фильтры */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Фильтры</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                📅 От даты
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                📅 До даты
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                📋 Статус проектов
              </label>
              <select
                value={projectStatus}
                onChange={(e) => setProjectStatus(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {PROJECT_STATUSES.map(status => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                ✅ Статус задач
              </label>
              <select
                value={taskStatus}
                onChange={(e) => setTaskStatus(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {TASK_STATUSES.map(status => (
                  <option key={status.value} value={status.value}>
                    {status.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {(dateFrom || dateTo || projectStatus || taskStatus) && (
            <div className="mt-4">
              <button
                onClick={() => {
                  setDateFrom('');
                  setDateTo('');
                  setProjectStatus('');
                  setTaskStatus('');
                }}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-colors flex items-center space-x-2"
              >
                <span>✕</span>
                <span>Сбросить фильтры</span>
              </button>
            </div>
          )}
        </div>

        {/* Таблица проектов */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Проект
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Тип услуги
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Исполнитель
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Время создания
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Время завершения / Дедлайн
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Статус
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider w-12">
                    
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredProjects.map(project => (
                  <React.Fragment key={project.id}>
                    <tr 
                      className="hover:bg-gray-50 transition-colors duration-150 cursor-pointer"
                      onClick={() => toggleProject(project.id)}
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center space-x-3">
                          {project.logo ? (
                            <img 
                              src={`${API_URL}/${project.logo}`} 
                              alt={project.project} 
                              className="w-8 h-8 rounded-full object-cover"
                            />
                          ) : (
                            <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                              <span className="text-gray-500 text-xs">📁</span>
                            </div>
                          )}
                          <div className="text-sm font-medium text-gray-900">
                            {project.project}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900">{project.service}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900">{project.executor}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900">{formatDate(project.created_at)}</div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-900">
                          {project.status === 'completed' && project.deadline ? 
                            formatDeadline(project.deadline) : 
                            project.deadline ? formatDeadline(project.deadline) : 'Не указан'
                          }
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(project.status)}`}>
                          {getStatusLabel(project.status)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <button className="text-gray-400 hover:text-gray-600 transition-colors">
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

                    {/* Раскрывающаяся таблица задач */}
                    {expandedProject === project.id && (
                      <tr>
                        <td colSpan={7} className="px-0 py-0">
                          <div className="bg-gray-50 border-t border-gray-200">
                            <div className="p-6">
                              <h4 className="text-md font-semibold text-gray-900 mb-4">
                                Задачи проекта "{project.project}"
                              </h4>
                              
                              {filteredTasks(project.id).length > 0 ? (
                                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                                  <table className="w-full">
                                    <thead>
                                      <tr className="bg-gray-100 border-b border-gray-200">
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                          Название задачи
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                          Краткое описание
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                          Время создания
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                          Время завершения / Дедлайн
                                        </th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                          Статус
                                        </th>
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-200">
                                      {filteredTasks(project.id).map(task => (
                                        <tr key={task.id} className="hover:bg-gray-50">
                                          <td className="px-4 py-3">
                                            <div className="flex items-center space-x-2">
                                              {task.high_priority && (
                                                <span className="text-red-500 text-sm">🔥</span>
                                              )}
                                              <div className="text-sm font-medium text-gray-900">
                                                {task.title}
                                              </div>
                                            </div>
                                          </td>
                                          <td className="px-4 py-3">
                                            <div className="text-sm text-gray-600 max-w-xs truncate">
                                              {task.description || 'Нет описания'}
                                            </div>
                                          </td>
                                          <td className="px-4 py-3">
                                            <div className="text-sm text-gray-900">
                                              {formatDate(task.created_at)}
                                            </div>
                                          </td>
                                          <td className="px-4 py-3">
                                            <div className="text-sm text-gray-900">
                                              {task.deadline ? formatDeadline(task.deadline) : 'Не указан'}
                                            </div>
                                          </td>
                                          <td className="px-4 py-3">
                                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(task.status)}`}>
                                              {getStatusLabel(task.status)}
                                            </span>
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              ) : (
                                <div className="text-center py-8 text-gray-500">
                                  Нет задач, соответствующих выбранным фильтрам
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
          
          {filteredProjects.length === 0 && (
            <div className="text-center py-12">
              <div className="text-gray-400 text-4xl mb-4">📊</div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Нет проектов</h3>
              <p className="text-gray-500">
                {(dateFrom || dateTo || projectStatus) ? 
                  'Нет проектов, соответствующих выбранным фильтрам' : 
                  'Сначала создайте проекты в разделе "Задачи"'
                }
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
