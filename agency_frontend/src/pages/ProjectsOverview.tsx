import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_URL } from '../api'

interface Project {
  id: number
  name: string
  logo?: string
}

interface PostSummary {
  in_progress: number
  approved: number
  cancelled: number
  overdue: number
}

const MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']

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
            Всего задач: {total}
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
  const token = localStorage.getItem('token')
  const navigate=useNavigate()

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
        setProjects(projects)
        const obj:Record<number,PostSummary>={}
        for(const p of projects){
          const r = await fetch(`${API_URL}/projects/${p.id}/posts?month=${m}`,{headers:{Authorization:`Bearer ${token}`}})
          if(r.ok){
            const posts = await r.json()
            const sum:PostSummary={in_progress:0,approved:0,cancelled:0,overdue:0}
            if(Array.isArray(posts)){
              for(const pt of posts){
                sum[pt.status as keyof PostSummary]++
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

  useEffect(()=>{load(month)},[month])

  return (
    <div>
      {/* Header with Month Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">📊 Успеваемость по проектам</h1>
          <p className="text-gray-600">Отслеживайте прогресс и статистику ваших проектов</p>
        </div>
        
        {/* Minimalistic Month Filter */}
        <div className="mt-4 sm:mt-0">
          <select 
            className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all" 
            value={month} 
            onChange={e=>setMonth(Number(e.target.value))}
          >
            {MONTHS.map((m,i)=>(<option key={i+1} value={i+1}>{m}</option>))}
          </select>
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
