import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_URL } from '../api'

interface Project {
  id: number
  name: string
  logo?: string
  start_date?: string
  end_date?: string
}

interface PostSummary {
  in_progress: number
  approved: number
  cancelled: number
  overdue: number
}

const MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']

// Вспомогательные функции для работы с проектными месяцами
const parseUTC = (s: string) => new Date(s.endsWith('Z') ? s : s + 'Z')

const getProjectMonth = (startDate: string, monthIndex: number) => {
  if (!startDate) return null

  try {
    const currentYear = new Date().getFullYear()

    // Очищаем дату от возможных лишних символов
    const cleanDate = startDate.includes('T') ? startDate.split('T')[0] : startDate
    const dayOfMonth = parseUTC(cleanDate + 'T00:00:00').getUTCDate()

    // Начало месяца
    const monthStart = new Date(Date.UTC(currentYear, monthIndex - 1, dayOfMonth))

    // Конец месяца - следующий месяц, тот же день, минус 1 день
    const nextMonth = new Date(Date.UTC(currentYear, monthIndex, dayOfMonth))
    const monthEnd = new Date(nextMonth.getTime() - 24 * 60 * 60 * 1000)

    return {
      startDate: monthStart.toISOString().slice(0, 10),
      endDate: monthEnd.toISOString().slice(0, 10)
    }
  } catch (error) {
    return null
  }
}

function TaskStatsWidget({stats}:{stats:PostSummary}) {
  const total = stats.in_progress + stats.approved + stats.cancelled + stats.overdue
  
  const getPercentage = (value: number) => total > 0 ? Math.round((value / total) * 100) : 0
  
  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-100 p-4 rounded-xl">
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-white rounded-lg p-3 text-center shadow-sm">
          <div className="text-2xl font-bold text-red-600">{stats.overdue}</div>
          <div className="text-xs text-gray-600">Просрочено</div>
        </div>
        <div className="bg-white rounded-lg p-3 text-center shadow-sm">
          <div className="text-2xl font-bold text-gray-600">{stats.cancelled}</div>
          <div className="text-xs text-gray-600">Отменено</div>
        </div>
        <div className="bg-white rounded-lg p-3 text-center shadow-sm">
          <div className="text-2xl font-bold text-yellow-600">{stats.in_progress}</div>
          <div className="text-xs text-gray-600">В работе</div>
        </div>
        <div className="bg-white rounded-lg p-3 text-center shadow-sm">
          <div className="text-2xl font-bold text-green-600">{stats.approved}</div>
          <div className="text-xs text-gray-600">Завершено</div>
        </div>
      </div>
      
      {/* Прогресс бар */}
      <div className="bg-white rounded-lg p-2">
        <div className="relative flex h-6 bg-gray-200 rounded-full overflow-hidden">
          {total > 0 && (
            <>
              <div 
                className="bg-red-500 relative flex items-center justify-center" 
                style={{width: `${getPercentage(stats.overdue)}%`}}
              >
                {getPercentage(stats.overdue) > 0 && (
                  <span className="text-xs font-medium text-white">
                    {getPercentage(stats.overdue)}%
                  </span>
                )}
              </div>
              <div 
                className="bg-gray-500 relative flex items-center justify-center" 
                style={{width: `${getPercentage(stats.cancelled)}%`}}
              >
                {getPercentage(stats.cancelled) > 0 && (
                  <span className="text-xs font-medium text-white">
                    {getPercentage(stats.cancelled)}%
                  </span>
                )}
              </div>
              <div 
                className="bg-yellow-500 relative flex items-center justify-center" 
                style={{width: `${getPercentage(stats.in_progress)}%`}}
              >
                {getPercentage(stats.in_progress) > 0 && (
                  <span className="text-xs font-medium text-white">
                    {getPercentage(stats.in_progress)}%
                  </span>
                )}
              </div>
              <div 
                className="bg-green-500 relative flex items-center justify-center" 
                style={{width: `${getPercentage(stats.approved)}%`}}
              >
                {getPercentage(stats.approved) > 0 && (
                  <span className="text-xs font-medium text-white">
                    {getPercentage(stats.approved)}%
                  </span>
                )}
              </div>
            </>
          )}
        </div>
        <div className="text-center mt-2">
          <span className="text-sm font-semibold text-gray-700">
            Всего постов: {total}
          </span>
        </div>
      </div>
    </div>
  )
}

function Projects() {
  const [projects,setProjects]=useState<Project[]>([])
  const [stats,setStats]=useState<Record<number,PostSummary>>({})
  const [month,setMonth]=useState(new Date().getMonth()+1)
  const [lastDatabaseVersion, setLastDatabaseVersion] = useState<string | null>(null)
  const token = localStorage.getItem('token')
  const navigate=useNavigate()

  // Check database version and force refresh if changed
  const checkDatabaseVersion = async () => {
    try {
      const response = await fetch(`${API_URL}/database/version`)
      if (response.ok) {
        const data = await response.json()
        const currentVersion = data.version

        if (lastDatabaseVersion && lastDatabaseVersion !== currentVersion) {
          console.log('🔄 Database version changed, forcing cache refresh...', {
            old: lastDatabaseVersion,
            new: currentVersion
          })
          // Clear localStorage cache (except auth data)
          const token = localStorage.getItem('token')
          const role = localStorage.getItem('role')
          const userId = localStorage.getItem('userId')

          // Clear all other localStorage data
          Object.keys(localStorage).forEach(key => {
            if (!['token', 'role', 'userId'].includes(key)) {
              localStorage.removeItem(key)
            }
          })

          // Clear sessionStorage
          sessionStorage.clear()

          // Force page reload to ensure clean state
          window.location.reload()
          return
        }

        setLastDatabaseVersion(currentVersion)
      }
    } catch (error) {
      console.error('Failed to check database version:', error)
    }
  }

  const load = async (m:number=month) => {
    if (!token) {
      setProjects([])
      setStats({})
      return
    }

    try {
      const res = await fetch(`${API_URL}/projects/`,{headers:{Authorization:`Bearer ${token}`}})
      if(res.ok){
        const data = await res.json()
        const projects: Project[] = Array.isArray(data) ? data : []

        // Загружаем детальную информацию для каждого проекта
        const projectsWithDetails = []
        for(const p of projects) {
          const detailRes = await fetch(`${API_URL}/projects/${p.id}`, {headers:{Authorization:`Bearer ${token}`}})
          if(detailRes.ok) {
            const detailData = await detailRes.json()
            projectsWithDetails.push({
              ...p,
              start_date: detailData.start_date,
              end_date: detailData.end_date
            })
          } else {
            projectsWithDetails.push(p)
          }
        }

        setProjects(projectsWithDetails)
        const obj:Record<number,PostSummary>={}

        for(const p of projectsWithDetails){
          // Получаем все посты проекта
          const r = await fetch(`${API_URL}/projects/${p.id}/posts`,{headers:{Authorization:`Bearer ${token}`}})
          if(r.ok){
            const allPosts = await r.json()
            const sum:PostSummary={in_progress:0,approved:0,cancelled:0,overdue:0}

            if(Array.isArray(allPosts)){
              if(p.start_date) {
                // Получаем диапазон текущего проектного месяца
                const projectMonth = getProjectMonth(p.start_date, m)

                if(projectMonth){
                  // Фильтруем посты по диапазону проектного месяца
                  const filteredPosts = allPosts.filter(post => {
                    if(!post.date) return false
                    const postDate = post.date.slice(0, 10)
                    return postDate >= projectMonth.startDate && postDate <= projectMonth.endDate
                  })

                  // Считаем статистику для отфильтрованных постов
                  for(const pt of filteredPosts){
                    sum[pt.status as keyof PostSummary]++
                  }
                }
              } else {
                // Если нет дат проекта, считаем все посты
                for(const pt of allPosts){
                  sum[pt.status as keyof PostSummary]++
                }
              }
            }
            obj[p.id]=sum
          } else {
            obj[p.id]={in_progress:0,approved:0,cancelled:0,overdue:0}
          }
        }
        setStats(obj)
      } else {
        setProjects([])
        setStats({})
      }
    } catch (error) {
      setProjects([])
      setStats({})
    }
  }

  useEffect(()=>{
    // Initial load with database version check
    const initialLoad = async () => {
      await checkDatabaseVersion()
      load(month)
    }
    initialLoad()
  },[month])

  // Добавляем автоматическое обновление
  useEffect(() => {
    const handleFocus = async () => {
      console.log('🔄 Page focused, checking database version and reloading projects...')
      await checkDatabaseVersion()
      load(month)
    }

    const handleVisibilityChange = async () => {
      if (!document.hidden) {
        console.log('🔄 Page became visible, checking database version and reloading projects...')
        await checkDatabaseVersion()
        load(month)
      }
    }

    // Автообновление каждые 10 секунд с проверкой версии БД
    const interval = setInterval(async () => {
      console.log('⏰ Auto-refreshing: checking database version and projects data...')
      await checkDatabaseVersion()
      load(month)
    }, 10000)

    window.addEventListener('focus', handleFocus)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      clearInterval(interval)
      window.removeEventListener('focus', handleFocus)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [month])

  return (
    <div>
      {/* Header with Month Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">📊 Успеваемость по проектам</h1>
          <p className="text-gray-600">Отслеживайте прогресс и статистику ваших проектов</p>
        </div>
        
        {/* Minimalistic Month Filter */}
        <div className="mt-4 sm:mt-0 flex items-center space-x-3">
          <select
            className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
            value={month}
            onChange={e=>setMonth(Number(e.target.value))}
          >
            {MONTHS.map((m,i)=>(<option key={i+1} value={i+1}>{m}</option>))}
          </select>

          {/* Кнопка обновления */}
          <button
            onClick={async () => {
              console.log('🔄 Manual reload requested - checking database version')
              await checkDatabaseVersion()
              load(month)
            }}
            className="flex items-center space-x-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
            title="Обновить данные"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Обновить</span>
          </button>
        </div>
      </div>
      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {Array.isArray(projects) && projects.length > 0 ? projects.map(p => (
          <div 
            key={p.id} 
            className="group bg-white rounded-2xl shadow-sm hover:shadow-xl transition-all duration-500 overflow-hidden cursor-pointer border border-gray-200 hover:border-blue-300 transform hover:-translate-y-1"
            onClick={()=>navigate(`/projects/${p.id}`)}
          >
            {/* Шапка карточки с логотипом */}
            <div className="bg-gradient-to-br from-blue-600 via-purple-600 to-indigo-700 p-6 text-white relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-white bg-opacity-10 rounded-full transform translate-x-16 -translate-y-16"></div>
              <div className="relative z-10">
                <div className="flex items-center space-x-4 mb-3">
                  {p.logo ? (
                    <img 
                      src={`${API_URL}/${p.logo}`} 
                      alt={p.name}
                      className="w-14 h-14 rounded-full object-cover bg-white p-1 shadow-lg"
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-full bg-white bg-opacity-20 flex items-center justify-center shadow-lg backdrop-blur-sm">
                      <span className="text-2xl font-bold">{p.name.charAt(0)}</span>
                    </div>
                  )}
                  <div>
                    <h3 className="font-bold text-xl text-white group-hover:text-blue-100 transition-colors">{p.name}</h3>
                    <p className="text-blue-100 text-sm flex items-center">
                      <span className="mr-1">🚀</span> Проект
                    </p>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Содержимое карточки */}
            <div className="p-6">
              <TaskStatsWidget stats={stats[p.id]||{in_progress:0,approved:0,cancelled:0,overdue:0}} />
            </div>
          </div>
        )) : (
          <div className="col-span-full flex flex-col items-center justify-center py-16 text-center">
            <div className="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <span className="text-4xl">📁</span>
            </div>
            <h3 className="text-xl font-semibold text-gray-600 mb-2">Нет проектов</h3>
            <p className="text-gray-500">Создайте свой первый проект, чтобы начать отслеживание</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default Projects
