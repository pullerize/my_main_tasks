import { useState } from 'react'
import Users from './Users'
import Operators from './Operators'
import Projects from './ProjectsAdmin'
import ExpensesAdmin from './ExpensesAdmin'
import Taxes from './Taxes'
import Settings from './Settings'

function AdminPanel() {
  const [tab, setTab] = useState<'users'|'operators'|'projects'|'expenses'|'taxes'|'settings'>('users')

  const tabs = [
    { id: 'users', label: 'Пользователи' },
    { id: 'operators', label: 'Операторы' },
    { id: 'projects', label: 'Проекты' },
    { id: 'expenses', label: 'Расходы' },
    { id: 'taxes', label: 'Налоги' },
    { id: 'settings', label: 'Настройки' }
  ]

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Админ панель</h1>
      
      {/* Навигация по табам */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tabItem) => (
            <button
              key={tabItem.id}
              onClick={() => setTab(tabItem.id as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                tab === tabItem.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tabItem.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Содержимое активной вкладки */}
      <div>
        {tab === 'users' && <Users />}
        {tab === 'operators' && <Operators />}
        {tab === 'projects' && <Projects />}
        {tab === 'expenses' && <ExpensesAdmin />}
        {tab === 'taxes' && <Taxes />}
        {tab === 'settings' && <Settings />}
      </div>
    </div>
  )
}

export default AdminPanel
