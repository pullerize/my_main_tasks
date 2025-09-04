import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useSidebar } from '../contexts/SidebarContext'
import { useState, useEffect } from 'react'
import { API_URL } from '../api'
import { clearAllFilters } from '../utils/filterStorage'

function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isCollapsed, toggleSidebar } = useSidebar()
  const [userName, setUserName] = useState('')

  // Load user name
  useEffect(() => {
    const loadUserName = async () => {
      const token = localStorage.getItem('token')
      const userId = localStorage.getItem('userId')
      
      if (token && userId) {
        try {
          const response = await fetch(`${API_URL}/users/me`, {
            headers: { Authorization: `Bearer ${token}` }
          })
          if (response.ok) {
            const userData = await response.json()
            setUserName(userData.name || 'Пользователь')
          }
        } catch (error) {
          console.error('Failed to load user name:', error)
          setUserName('Пользователь')
        }
      }
    }
    
    loadUserName()
  }, [])

  // Auto refresh functionality - DISABLED for debugging
  useEffect(() => {
    // DEBUG Navbar: Auto-refresh disabled for debugging
    // const interval = setInterval(() => {
    //   // Сохраняем текущий путь перед обновлением
    //   localStorage.setItem('lastVisitedPath', location.pathname)
    //   window.location.reload()
    // }, 30000) // Обновление каждые 30 секунд

    // return () => {
    //   clearInterval(interval)
    // }
  }, [location.pathname])

  const clearCache = async () => {
    if (isAdmin) {
      // Глобальная очистка кеша для администратора
      try {
        const token = localStorage.getItem('token')
        const response = await fetch(`${API_URL}/admin/clear-cache`, {
          method: 'POST',
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        })
        
        if (response.ok) {
          alert('✅ Глобальный кеш успешно очищен для всех пользователей!')
        } else {
          // Fallback to local cache clearing if server doesn't support global clearing
          console.warn('Global cache clearing not supported, falling back to local clearing')
          localCacheClear()
        }
      } catch (error) {
        console.error('Failed to clear global cache:', error)
        // Fallback to local cache clearing
        localCacheClear()
      }
    } else {
      // Локальная очистка кеша для обычных пользователей
      localCacheClear()
    }
  }

  const localCacheClear = () => {
    // Очистка localStorage (кроме критически важных данных)
    const token = localStorage.getItem('token')
    const role = localStorage.getItem('role')
    const userId = localStorage.getItem('userId')
    const lastVisitedPath = localStorage.getItem('lastVisitedPath')
    
    localStorage.clear()
    
    // Восстанавливаем важные данные
    if (token) localStorage.setItem('token', token)
    if (role) localStorage.setItem('role', role)  
    if (userId) localStorage.setItem('userId', userId)
    if (lastVisitedPath) localStorage.setItem('lastVisitedPath', lastVisitedPath)
    
    // Очистка sessionStorage
    sessionStorage.clear()
    
    // Перезагрузка страницы для полной очистки
    window.location.reload()
  }

  const logout = () => {
    try {
      // Очищаем все фильтры перед выходом
      clearAllFilters()
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      localStorage.removeItem('userId')
      // Принудительно обновляем страницу для очистки состояния
      window.location.href = '/login'
    } catch (error) {
      console.error('Logout error:', error)
      // В случае ошибки все равно перенаправляем на логин
      window.location.href = '/login'
    }
  }

  const role = localStorage.getItem('role')
  
  // Debug logging - временное для отладки
  // console.log('DEBUG: Current role from localStorage:', role)
  // console.log('DEBUG: localStorage contents:', {
  //   token: localStorage.getItem('token') ? 'exists' : 'missing',
  //   role: localStorage.getItem('role'),
  //   userId: localStorage.getItem('userId')
  // })
  
  // Role-based permissions system
  const isAdmin = role && (
    role.toLowerCase() === 'admin' || 
    role.toLowerCase() === 'administrator' ||
    role === 'ADMIN'
  )
  
  const isDesigner = role === 'designer'
  const isSmmManager = role === 'smm_manager'
  const isDigital = role === 'digital'
  const isHeadSmm = role === 'head_smm'
  
  // console.log('DEBUG: Role checks:', { 
  //   isAdmin, 
  //   isDesigner, 
  //   isSmmManager, 
  //   isDigital, 
  //   isHeadSmm,
  //   originalRole: role 
  // })

  const isActive = (path: string) => {
    return location.pathname.startsWith(path)
  }

  const NavLink = ({ to, children, icon }: { to: string, children: React.ReactNode, icon: string }) => (
    <Link
      to={to}
      className={`
        group flex items-center text-sm font-medium rounded-xl transition-all duration-300 ease-in-out
        ${isCollapsed ? 'px-3 py-3 justify-center' : 'px-4 py-3'}
        ${isActive(to) 
          ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg shadow-blue-500/25 transform scale-105' 
          : 'text-gray-300 hover:text-white hover:bg-gradient-to-r hover:from-gray-700/50 hover:to-gray-600/50'
        }
        relative overflow-hidden
        before:absolute before:inset-0 before:bg-gradient-to-r before:from-blue-500/10 before:to-purple-500/10 
        before:opacity-0 before:transition-opacity before:duration-300 hover:before:opacity-100
      `}
      title={isCollapsed ? children as string : undefined}
    >
      <span className={`text-lg ${isCollapsed ? '' : 'mr-3'}`}>{icon}</span>
      {!isCollapsed && <span className="relative z-10">{children}</span>}
    </Link>
  )

  // Меню для дизайнеров
  const designerMenuItems = [
    { to: "/smm-projects?tab=tasks", label: "СММ проекты", icon: "📱" },
    { to: "/resources", label: "Ресурсы", icon: "🛠️" },
    { to: "/personal-expenses", label: "Мои расходы", icon: "💳" },
  ]

  // Меню для СММ менеджеров
  const smmManagerMenuItems = [
    { to: "/smm-projects", label: "СММ проекты", icon: "📱" },
    { to: "/resources", label: "Ресурсы", icon: "🛠️" },
    { to: "/personal-expenses", label: "Мои расходы", icon: "💳" },
  ]

  // Меню для Digital специалистов
  const digitalMenuItems = [
    { to: "/smm-projects", label: "СММ проекты", icon: "📱" },
    { to: "/digital/tasks", label: "Digital проекты", icon: "💻" },
    { to: "/resources", label: "Ресурсы", icon: "🛠️" },
    { to: "/personal-expenses", label: "Мои расходы", icon: "💳" },
  ]

  // Меню для администраторов
  const adminMenuItems = [
    { to: "/smm-projects", label: "СММ проекты", icon: "📱" },
    { to: "/digital/tasks", label: "Digital проекты", icon: "💻" },
    { to: "/analytics", label: "Аналитика", icon: "📊" },
    { to: "/resources", label: "Ресурсы", icon: "🛠️" },
    { to: "/reports", label: "Отчеты", icon: "📋" },
    { to: "/expense-reports", label: "Отчеты по расходам", icon: "💰" },
    { to: "/personal-expenses", label: "Мои расходы", icon: "💳" },
    { to: "/admin", label: "Админ панель", icon: "⚙️" },
  ]

  // Определяем меню в зависимости от роли
  const getMenuItems = () => {
    if (isAdmin) return adminMenuItems
    if (isDesigner) return designerMenuItems
    if (isSmmManager || isHeadSmm) return smmManagerMenuItems
    if (isDigital) return digitalMenuItems
    // Fallback для неизвестных ролей
    return designerMenuItems
  }

  const menuItems = getMenuItems()
  
  // console.log('DEBUG: Selected menu items:', menuItems.map(item => item.label))
  // console.log('DEBUG: Using admin menu?', isAdmin)

  return (
    <>
      <aside
        key={location.pathname} // Force re-render on route change 
        className={`
          fixed left-0 top-0 z-50 h-screen transition-all duration-300 ease-in-out
          ${isCollapsed ? 'w-20' : 'w-64'}
          bg-gradient-to-b from-slate-900 via-gray-900 to-slate-900 
          border-r border-gray-700/50 shadow-2xl backdrop-blur-lg
        `}
        style={{ 
          zIndex: 9999, 
          display: 'block', 
          visibility: 'visible'
        }}
      >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700/50">
        <div className={`transition-all duration-300 ${isCollapsed ? 'opacity-0 w-0' : 'opacity-100'}`}>
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            8BIT MEDIA
          </h1>
        </div>
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700/50 transition-all duration-300"
        >
          <svg 
            className={`w-5 h-5 transition-transform duration-300 ${isCollapsed ? 'rotate-180' : ''}`} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-2">
        {menuItems.map((item) => (
          <NavLink key={item.to} to={item.to} icon={item.icon}>
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* User Profile Section */}
      <div className="flex-1 p-4 border-t border-gray-700/50">
        {userName && (
          <div className={`
            bg-gradient-to-r from-indigo-600/20 to-purple-600/20 
            border border-indigo-500/30 rounded-xl p-3
            backdrop-blur-sm
            ${isCollapsed ? 'text-center' : ''}
          `}>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-white text-sm font-bold">
                  {userName.charAt(0).toUpperCase()}
                </span>
              </div>
              {!isCollapsed && (
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-white truncate">
                    {userName}
                  </div>
                  <div className="text-xs text-indigo-200">
                    {role === 'admin' ? 'Администратор' : 
                     role === 'designer' ? 'Дизайнер' :
                     role === 'smm_manager' ? 'СММ-менеджер' :
                     role === 'digital' ? 'Digital специалист' :
                     role === 'head_smm' ? 'Главный СММ' : 'Сотрудник'}
                  </div>
                </div>
              )}
            </div>
            {isCollapsed && (
              <div className="text-xs text-indigo-200 mt-1 truncate" title={userName}>
                {userName.length > 8 ? userName.substring(0, 8) + '...' : userName}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action Buttons - Fixed to bottom of screen */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-700/50 bg-gradient-to-b from-slate-900 via-gray-900 to-slate-900 space-y-2">
        {/* Clear Cache Button */}
        <button 
          onClick={clearCache}
          className={`
            w-full flex items-center text-sm font-medium rounded-xl
            ${isCollapsed ? 'px-3 py-3 justify-center' : 'px-4 py-3'}
            bg-orange-600/20 hover:bg-orange-600 text-orange-200 hover:text-white 
            border border-orange-600/50 hover:border-orange-600 
            transition-all duration-300 ease-in-out hover:shadow-lg hover:shadow-orange-500/25 
            transform hover:scale-105
          `}
          title={isCollapsed ? "Очистить кеш" : undefined}
        >
          <span className={`text-lg ${isCollapsed ? '' : 'mr-3'}`}>🗑️</span>
          {!isCollapsed && <span>Очистить кеш</span>}
        </button>

        {/* Logout Button */}
        <button 
          onClick={logout} 
          className={`
            w-full flex items-center text-sm font-medium rounded-xl
            ${isCollapsed ? 'px-3 py-3 justify-center' : 'px-4 py-3'}
            bg-red-600/20 hover:bg-red-600 text-red-200 hover:text-white 
            border border-red-600/50 hover:border-red-600 
            transition-all duration-300 ease-in-out hover:shadow-lg hover:shadow-red-500/25 
            transform hover:scale-105
          `}
          title={isCollapsed ? "Выйти" : undefined}
        >
          <span className={`text-lg ${isCollapsed ? '' : 'mr-3'}`}>🚪</span>
          {!isCollapsed && <span>Выйти</span>}
        </button>
      </div>

      </aside>
    </>
  )
}

export default Navbar
