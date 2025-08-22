import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useSidebar } from '../contexts/SidebarContext'

function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isCollapsed, toggleSidebar } = useSidebar()

  const logout = () => {
    try {
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

  const menuItems = role === 'admin' ? [
    { to: "/smm-projects", label: "СММ проекты", icon: "📱" },
    { to: "/digital/tasks", label: "Digital проекты", icon: "💻" },
    { to: "/analytics", label: "Аналитика", icon: "📊" },
    { to: "/resources", label: "Ресурсы", icon: "🛠️" },
    { to: "/reports", label: "Отчеты", icon: "📋" },
    { to: "/admin", label: "Админ панель", icon: "⚙️" },
  ] : [
    { to: "/tasks", label: "Задачи", icon: "✅" },
    { to: "/calendar", label: "Календарь съемок", icon: "📅" },
    { to: "/projects", label: "Проекты", icon: "📁" },
    { to: "/digital/tasks", label: "Digital отдел", icon: "💻" },
    { to: "/analytics", label: "Аналитика", icon: "📊" },
    { to: "/resources", label: "Ресурсы", icon: "🛠️" },
    { to: "/reports", label: "Отчеты", icon: "📋" },
  ]

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

      {/* Footer */}
      <div className="p-4 border-t border-gray-700/50">
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
