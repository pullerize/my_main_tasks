import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import Login from './pages/Login'
import Tasks from './pages/Tasks'
import Calendar from './pages/Calendar'
import Reports from './pages/Reports'
import ExpensesReport from './pages/ExpensesReport'
import EmployeeReport from './pages/EmployeeReport'
import Users from './pages/Users'
import Operators from './pages/Operators'
import ProjectsAdmin from './pages/ProjectsAdmin'
import ProjectsOverview from './pages/ProjectsOverview'
import ProjectDetail from './pages/ProjectDetail'
import AdminPanel from './pages/AdminPanel'
import Digital from './pages/Digital'
import SmmProjects from './pages/SmmProjects'
import Analytics from './pages/Analytics'
import Resources from './pages/Resources'
import ExpenseReports from './pages/ExpenseReports'
import PersonalExpenses from './pages/PersonalExpenses'
import { SidebarProvider, useSidebar } from './contexts/SidebarContext'

function AppContent() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [role, setRole] = useState(localStorage.getItem('role'))
  const location = useLocation()
  
  // Определяем путь по умолчанию с учетом последней посещенной страницы
  const getDefaultPath = () => {
    const lastVisitedPath = localStorage.getItem('lastVisitedPath')
    const defaultPath = '/smm-projects' // Все пользователи начинают с СММ проектов
    
    // Если есть сохраненный путь, используем его, иначе путь по умолчанию
    return lastVisitedPath || defaultPath
  }
  
  const defaultPath = getDefaultPath()
  const { isCollapsed } = useSidebar()

  // Сохраняем текущий путь при изменении маршрута
  useEffect(() => {
    if (token && location.pathname !== '/login') {
      localStorage.setItem('lastVisitedPath', location.pathname)
    }
  }, [location.pathname, token])

  useEffect(() => {
    const handleStorageChange = () => {
      setToken(localStorage.getItem('token'))
      setRole(localStorage.getItem('role'))
    }

    window.addEventListener('storage', handleStorageChange)
    
    const checkAuth = () => {
      const currentToken = localStorage.getItem('token')
      const currentRole = localStorage.getItem('role')
      if (currentToken !== token) setToken(currentToken)
      if (currentRole !== role) setRole(currentRole)
    }
    
    const interval = setInterval(checkAuth, 100)
    
    return () => {
      window.removeEventListener('storage', handleStorageChange)
      clearInterval(interval)
    }
  }, [token, role])

  // Автообновление страницы каждую минуту - ОТКЛЮЧЕНО
  // useEffect(() => {
  //   if (token) {
  //     const autoRefreshInterval = setInterval(() => {
  //       window.location.reload()
  //     }, 60000) // 60 секунд = 1 минута
  //     
  //     return () => clearInterval(autoRefreshInterval)
  //   }
  // }, [token])
  
  if (!token) {
    // Check if we have role/userId without token (shouldn't happen after login fix)
    const currentRole = localStorage.getItem('role')
    const currentUserId = localStorage.getItem('userId')
    
    // console.log('DEBUG App: No token found', { 
    //   currentRole, 
    //   currentUserId,
    //   shouldClear: !currentRole || !currentUserId 
    // })
    
    // Only clear if both role and userId are missing (avoid clearing fresh login data)
    if (!currentRole || !currentUserId) {
      // console.log('DEBUG App: Clearing stale role and userId')
      localStorage.removeItem('role')
      localStorage.removeItem('userId')
    }
    
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    )
  }

  // console.log('DEBUG App: Token exists, role and userId should be preserved:', {
  //   token: token ? 'exists' : 'missing',
  //   role: role,
  //   userId: localStorage.getItem('userId')
  // })

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <Navbar key="navbar-always-visible" />
      <main 
        className={`
          flex-1 px-4 sm:px-8 lg:px-[100px] py-8 max-w-full min-h-screen transition-all duration-300 ease-in-out
          ${isCollapsed ? 'ml-20' : 'ml-64'}
        `}
      >
        <div className="max-w-full w-full">
          <Routes>
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/calendar" element={<Calendar />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/expenses-report" element={<ExpensesReport />} />
            <Route path="/employee-report" element={<EmployeeReport />} />
            <Route path="/admin" element={<AdminPanel />} />
            <Route path="/users" element={<Users />} />
            <Route path="/operators" element={<Operators />} />
            <Route path="/projects" element={<ProjectsOverview />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/projects-admin" element={<ProjectsAdmin />} />
            <Route path="/digital/*" element={<Digital />} />
            <Route path="/smm-projects" element={<SmmProjects />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/resources" element={<Resources />} />
            <Route path="/expense-reports" element={<ExpenseReports />} />
            <Route path="/personal-expenses" element={<PersonalExpenses />} />
            <Route path="*" element={<Navigate to={defaultPath} />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

function App() {
  return (
    <SidebarProvider>
      <AppContent />
    </SidebarProvider>
  )
}

export default App
