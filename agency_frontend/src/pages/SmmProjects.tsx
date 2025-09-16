import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import Tasks from './Tasks'
import Calendar from './Calendar'
import ProjectsOverview from './ProjectsOverview'
import { usePersistedState } from '../utils/filterStorage'

function SmmProjects() {
  const location = useLocation()
  const role = localStorage.getItem('role')
  
  // Определяем доступные вкладки в зависимости от роли
  const tabs = (() => {
    const allTabs = [
      { id: 'tasks', label: 'Задачи', component: Tasks },
      { id: 'calendar', label: 'Календарь съемок', component: Calendar },
      { id: 'projects', label: 'Успеваемость по проектам', component: ProjectsOverview }
    ]

    // Дизайнеры видят только Задачи
    if (role === 'designer') {
      return allTabs.filter(tab => tab.id === 'tasks')
    }
    
    // СММ менеджеры, Digital и администраторы видят все вкладки
    return allTabs
  })()
  
  // Инициализируем activeTab после определения tabs
  const defaultTab = tabs.length > 0 ? tabs[0].id : 'tasks'
  const [activeTab, setActiveTab] = usePersistedState('active_tab_smm_projects', defaultTab)

  const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component || Tasks

  // Проверяем доступность текущей вкладки
  useEffect(() => {
    const availableTabIds = tabs.map(tab => tab.id)
    
    // Проверяем, есть ли доступ к текущей вкладке
    if (!availableTabIds.includes(activeTab)) {
      setActiveTab('tasks') // Переключаем на доступную вкладку
    }
  }, [tabs.length]) // Зависимость только от количества вкладок, не от location

  return (
    <div className="w-full h-full overflow-hidden">
      <h1 className="text-2xl font-bold mb-6">СММ проекты</h1>
      
      {/* Навигация по табам */}
      <div className="border-b border-gray-200 mb-6 overflow-x-auto">
        <nav className="-mb-px flex space-x-4 min-w-max">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={(e) => {
                e.preventDefault()
                if (activeTab !== tab.id) {
                  setActiveTab(tab.id)
                }
              }}
              className={`py-2 px-3 border-b-2 font-medium text-sm whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Содержимое активной вкладки */}
      <div className="flex-1 w-full overflow-hidden">
        <ActiveComponent />
      </div>
    </div>
  )
}

export default SmmProjects