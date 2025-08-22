import { NavLink, Routes, Route, Navigate } from 'react-router-dom';
import DigitalTasks from './DigitalTasks';
import DigitalFinance from './DigitalFinance';
import DigitalReports from './DigitalReports';
import DigitalSettings from './DigitalSettings';

function Digital() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Digital проекты</h1>
      
      {/* Навигация по табам */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <NavLink
            to="tasks"
            className={({ isActive }) =>
              `py-2 px-1 border-b-2 font-medium text-sm ${
                isActive
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`
            }
          >
            Задачи
          </NavLink>
          <NavLink
            to="finance"
            className={({ isActive }) =>
              `py-2 px-1 border-b-2 font-medium text-sm ${
                isActive
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`
            }
          >
            Финансы
          </NavLink>
          <NavLink
            to="reports"
            className={({ isActive }) =>
              `py-2 px-1 border-b-2 font-medium text-sm ${
                isActive
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`
            }
          >
            Отчеты
          </NavLink>
          <NavLink
            to="settings"
            className={({ isActive }) =>
              `py-2 px-1 border-b-2 font-medium text-sm ${
                isActive
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`
            }
          >
            Настройки
          </NavLink>
        </nav>
      </div>

      {/* Содержимое активной вкладки */}
      <div>
        <Routes>
          <Route path="tasks/*" element={<DigitalTasks />} />
          <Route path="finance" element={<DigitalFinance />} />
          <Route path="reports" element={<DigitalReports />} />
          <Route path="settings" element={<DigitalSettings />} />
          <Route path="*" element={<Navigate to="tasks" replace />} />
        </Routes>
      </div>
    </div>
  );
}

export default Digital;
