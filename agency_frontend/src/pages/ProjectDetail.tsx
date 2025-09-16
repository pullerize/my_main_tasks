import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { API_URL } from '../api'

interface Post {
  id: number
  date: string
  posts_per_day: number
  post_type: string
  status: string
}

interface Project {
  id: number
  name: string
  posts_count: number
  start_date: string
  end_date: string
}

// Row border colors based on post status
const statusColors: Record<string, string> = {
  in_progress: '#fbbf24', // yellow
  cancelled: '#808080',   // grey
  approved: '#008000',    // green
  overdue: '#ff0000',     // red
}

const MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']

function ProjectDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const token = localStorage.getItem('token')

  const [project, setProject] = useState<Project | null>(null)
  const [name, setName] = useState('')
  const [postsCount, setPostsCount] = useState(0)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [month,setMonth] = useState(new Date().getMonth()+1)

  const [posts, setPosts] = useState<Post[]>([])
  const [drafts, setDrafts] = useState<Post[]>([])
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)


  const parseUTC = (s: string) => new Date(s.endsWith('Z') ? s : s + 'Z')

  const load = async (m:number=month) => {
    const res = await fetch(`${API_URL}/projects/${id}`, { headers: { Authorization: `Bearer ${token}` } })
    if (res.ok) {
      const data = await res.json()
      setProject(data)
      setName(data.name)
      setPostsCount(data.posts_count)
      setStartDate(data.start_date?.slice(0, 10) || '')
      setEndDate(data.end_date?.slice(0, 10) || '')
    }
    let year = startDate ? parseUTC(startDate + 'T00:00:00').getUTCFullYear() : new Date().getFullYear()
    const nextMonth = m === 12 ? 1 : m + 1
    const nextYear = nextMonth === 1 ? year + 1 : year
    const first = await fetch(`${API_URL}/projects/${id}/posts?month=${m}&year=${year}`, { headers: { Authorization: `Bearer ${token}` } })
    const second = await fetch(`${API_URL}/projects/${id}/posts?month=${nextMonth}&year=${nextYear}`, { headers: { Authorization: `Bearer ${token}` } })
    const list1 = first.ok ? await first.json() : []
    const list2 = second.ok ? await second.json() : []
    setPosts([...list1, ...list2])
    setLoaded(true)
  }

  useEffect(() => { load(month) }, [id, month])

  const calcEndDate = (start: string) => {
    const d = new Date(start + 'T00:00:00Z')
    const end = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate()))
    end.setUTCDate(end.getUTCDate() - 1)
    return end.toISOString().slice(0, 10)
  }

  const handleStartChange = (value: string) => {
    setStartDate(value)
    if (value) {
      const e = calcEndDate(value)
      setEndDate(e)
    }
  }

  useEffect(() => {
    if (!loaded || !startDate) return
    const d = new Date(startDate + 'T00:00:00Z')
    const year = d.getUTCFullYear()
    const day = d.getUTCDate()
    const newStart = new Date(Date.UTC(year, month - 1, day))
    const newEnd = new Date(Date.UTC(year, month - 1, day))
    newEnd.setUTCMonth(newEnd.getUTCMonth() + 1)
    newEnd.setUTCDate(newEnd.getUTCDate() - 1)
    const s = newStart.toISOString().slice(0, 10)
    const e = newEnd.toISOString().slice(0, 10)
    setStartDate(s)
    setEndDate(e)
    updateInfo({ start_date: s, end_date: e })
  }, [month])

  // month/year selectors no longer reset start and end dates automatically

  const showError = (message: string) => {
    setSaveError(message)
    setTimeout(() => setSaveError(null), 5000)
  }

  const updateInfo = async (data: Partial<{name:string;posts_count:number;start_date:string;end_date:string}>) => {
    setSaving(true)
    setSaveError(null)
    
    try {
      if ('name' in data) {
        const res = await fetch(`${API_URL}/projects/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ name: data.name })
        })
        if (!res.ok) {
          const errorText = await res.text()
          throw new Error(`Не удалось обновить название проекта: ${errorText}`)
        }
      }
      const payload: any = {}
      if ('posts_count' in data) payload.posts_count = data.posts_count
      if ('start_date' in data) payload.start_date = data.start_date
      if ('end_date' in data) payload.end_date = data.end_date
      if (Object.keys(payload).length) {
        const res = await fetch(`${API_URL}/projects/${id}/info`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify(payload)
        })
        if (!res.ok) {
          const errorText = await res.text()
          throw new Error(`Не удалось обновить информацию о проекте: ${errorText}`)
        }
      }
      await load()
    } catch (error) {
      console.error('Error updating project:', error)
      showError(error instanceof Error ? error.message : 'Произошла ошибка при сохранении')
    } finally {
      setSaving(false)
    }
  }

  const updatePost = async (idx: number, post: Post, field: string, value: any) => {
    setSaving(true)
    setSaveError(null)
    
    try {
      const updated = { ...post, [field]: value }
      if (field === 'date' && value) {
        const d = parseUTC(value + 'T00:00:00')
        const sd = startDate ? parseUTC(startDate + 'T00:00:00') : null
        const ed = endDate ? parseUTC(endDate + 'T00:00:00') : null
        
        // Добавляем один день к endDate для правильного сравнения
        // так как endDate - это последний день месяца и посты на этот день должны быть включены
        const edNextDay = ed ? new Date(ed.getTime() + 24 * 60 * 60 * 1000) : null
        
        if (sd && d < sd) {
          setMonth(m => (m === 1 ? 12 : m - 1))
        } else if (edNextDay && d >= edNextDay) {
          // Переключаем на следующий месяц только если дата поста ПОСЛЕ последнего дня месяца
          setMonth(m => (m === 12 ? 1 : m + 1))
        }
        // Removed automatic status update - status should only change when user explicitly changes it
      }
      
      if (post.id === 0) {
        // Handle draft posts
        const draftsCopy = [...drafts]
        draftsCopy[idx - filteredPosts.length] = updated
        setDrafts(draftsCopy)
        
        if (field === 'date' && value) {
          const res = await fetch(`${API_URL}/projects/${id}/posts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({
              date: value + 'T00:00:00Z',
              posts_per_day: updated.posts_per_day,
              post_type: updated.post_type,
              status: updated.status,
            })
          })
          if (res.ok) {
            const created = await res.json()
            setPosts([...posts, created])
            draftsCopy.splice(idx - filteredPosts.length, 1)
            setDrafts(draftsCopy)
            await load()
          } else {
            const errorText = await res.text()
            throw new Error(`Не удалось создать пост: ${errorText}`)
          }
        }
      } else {
        // Handle existing posts with optimistic updates
        const originalPosts = [...posts]
        setPosts(posts.map((p) => (p.id === post.id ? updated : p)))
        
        const res = await fetch(`${API_URL}/project_posts/${post.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            date: (updated.date.includes('T') ? updated.date : updated.date + 'T00:00:00Z'),
            posts_per_day: updated.posts_per_day,
            post_type: updated.post_type,
            status: updated.status,
          }),
        })
        
        if (res.ok) {
          const saved = await res.json()
          setPosts(posts.map((p) => (p.id === post.id ? saved : p)))
        } else {
          // Revert optimistic update on error
          setPosts(originalPosts)
          const errorText = await res.text()
          throw new Error(`Не удалось обновить пост: ${errorText}`)
        }
      }
    } catch (error) {
      console.error('Error updating post:', error)
      showError(error instanceof Error ? error.message : 'Произошла ошибка при сохранении поста')
    } finally {
      setSaving(false)
    }
  }

  const addRow = () => {
    setDrafts([...drafts, { id: 0, date: '', posts_per_day: 1, post_type: 'video', status: 'in_progress' }])
  }

  const removeRow = async (idx: number, post: Post) => {
    setSaving(true)
    setSaveError(null)
    
    try {
      if (post.id === 0) {
        const copy = drafts.filter((_, i) => i !== idx - filteredPosts.length)
        setDrafts(copy)
      } else {
        const res = await fetch(`${API_URL}/project_posts/${post.id}`, { 
          method: 'DELETE', 
          headers: { Authorization: `Bearer ${token}` } 
        })
        if (res.ok) {
            setPosts(posts.filter(p => p.id !== post.id))
        } else {
          const errorText = await res.text()
          throw new Error(`Не удалось удалить пост: ${errorText}`)
        }
      }
    } catch (error) {
      console.error('Error removing post:', error)
      showError(error instanceof Error ? error.message : 'Произошла ошибка при удалении поста')
    } finally {
      setSaving(false)
    }
  }

  const filteredPosts = posts.filter(p => {
    const d = parseUTC(p.date)
    const sd = startDate ? parseUTC(startDate + 'T00:00:00') : null
    const ed = endDate ? parseUTC(endDate + 'T00:00:00') : null
    
    // Добавляем один день к endDate для правильного сравнения
    const edNextDay = ed ? new Date(ed.getTime() + 24 * 60 * 60 * 1000) : null
    
    if (sd && d < sd) return false
    if (edNextDay && d >= edNextDay) return false
    return true
  })

  const recalcPostsCount = async (list?: Post[], dr?: Post[]) => {
    const sd = startDate ? parseUTC(startDate + 'T00:00:00') : null
    const ed = endDate ? parseUTC(endDate + 'T00:00:00') : null
    
    // Добавляем один день к endDate для правильного сравнения
    const edNextDay = ed ? new Date(ed.getTime() + 24 * 60 * 60 * 1000) : null
    
    const relevant = (list || posts).filter(p => {
      const d = parseUTC(p.date)
      if (sd && d < sd) return false
      if (edNextDay && d >= edNextDay) return false
      return true
    })
    const totalExisting = relevant.reduce((sum, p) => sum + p.posts_per_day, 0)
    const draftSum = (dr || drafts).reduce((sum, d) => sum + d.posts_per_day, 0)
    const total = totalExisting + draftSum
    setPostsCount(total)
    await fetch(`${API_URL}/projects/${id}/info`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ posts_count: total })
    })
  }

  useEffect(() => {
    if (loaded) recalcPostsCount()
  }, [posts, drafts, startDate, endDate, month, loaded])

  // Разделяем посты на те, у которых есть дата, и те, у которых нет
  const postsWithDate = [...filteredPosts, ...drafts].filter(p => p.date)
  const postsWithoutDate = [...filteredPosts, ...drafts].filter(p => !p.date)
  
  // Сортируем только посты с датой
  const sortedPostsWithDate = postsWithDate.sort((a, b) => {
    const dateA = new Date(a.date).getTime()
    const dateB = new Date(b.date).getTime()
    return dateA - dateB
  })
  
  // Объединяем: сначала отсортированные посты с датой, потом посты без даты
  const rows = [...sortedPostsWithDate, ...postsWithoutDate]

  return (
    <div>
      {/* Header with back navigation */}
      <div className="bg-white shadow-sm border border-gray-200 rounded-xl px-6 py-4 mb-6">
        <div className="flex items-center space-x-4">
          <button
            onClick={() => navigate('/smm-projects', { state: { fromProjectDetail: true } })}
            className="flex items-center px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-all duration-200 group"
          >
            <svg className="w-5 h-5 mr-2 group-hover:-translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Назад к проектам
          </button>
          <div className="h-6 w-px bg-gray-300"></div>
          <h1 className="text-2xl font-bold text-gray-800">
            {project?.name || 'Загрузка...'}
          </h1>
        </div>
      </div>

      <div className="space-y-6">
        {/* Error Messages */}
        {saveError && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 flex items-center space-x-2">
            <svg className="h-5 w-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <span className="text-red-800">{saveError}</span>
          </div>
        )}

        {/* Project Information Card */}
        {project && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Информация о проекте</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-600">Название проекта</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    onBlur={() => updateInfo({name})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    placeholder="Введите название"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-600">Количество постов</label>
                  <input
                    type="number"
                    value={postsCount}
                    onChange={(e) => setPostsCount(Number(e.target.value))}
                    onBlur={() => updateInfo({posts_count: postsCount})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                    placeholder="0"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-600">Дата начала</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => handleStartChange(e.target.value)}
                    onBlur={() => updateInfo({start_date: startDate, end_date: endDate})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-600">Дата завершения</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    onBlur={() => updateInfo({end_date: endDate})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>
            </div>
            
            {/* Month selector */}
            <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
              <div className="flex items-center space-x-4">
                <label className="text-sm font-medium text-gray-600">Просмотр по месяцам:</label>
                <select 
                  value={month} 
                  onChange={e => setMonth(Number(e.target.value))}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                >
                  {MONTHS.map((m, i) => (
                    <option key={i + 1} value={i + 1}>{m}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Posts Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 bg-gradient-to-r from-green-50 to-emerald-50 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800">Планирование постов</h2>
              <button
                onClick={addRow}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200 flex items-center space-x-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                <span>Добавить пост</span>
              </button>
            </div>
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Дата</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Постов/день</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Тип поста</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Статус</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-20">Действие</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {rows.map((p, idx) => {
                  const statusColor = statusColors[p.status] || '#6B7280'
                  return (
                    <tr key={p.id ? `post-${p.id}` : `new-${idx}`} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <input
                          type="date"
                          value={p.date ? p.date.slice(0, 10) : ''}
                          onChange={e => updatePost(idx, p, 'date', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                          style={{ borderLeftColor: statusColor, borderLeftWidth: '4px' }}
                        />
                      </td>
                      <td className="px-6 py-4">
                        <input
                          type="number"
                          min="1"
                          value={p.posts_per_day}
                          onChange={e => updatePost(idx, p, 'posts_per_day', Number(e.target.value))}
                          className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-center"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <select
                          value={p.post_type}
                          onChange={e => updatePost(idx, p, 'post_type', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                        >
                          <option value="video">📹 Видео</option>
                          <option value="static">🖼️ Статика</option>
                          <option value="carousel">🎠 Карусель</option>
                        </select>
                      </td>
                      <td className="px-6 py-4" style={{ minWidth: '220px' }}>
                        <select
                          value={p.status}
                          onChange={e => updatePost(idx, p, 'status', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all bg-white"
                          style={{ color: statusColor, minWidth: '200px' }}
                        >
                          {(() => {
                            const today = new Date().toISOString().slice(0, 10)
                            const postDate = p.date ? p.date.slice(0, 10) : ''
                            const isPastDate = postDate && postDate < today
                            
                            if (isPastDate) {
                              // For past dates: only overdue, approved, or cancelled
                              return (
                                <>
                                  <option value="overdue">⏰ Просрочено (автоматически)</option>
                                  <option value="approved">✅ Завершена</option>
                                  <option value="cancelled">❌ Отменена</option>
                                </>
                              )
                            } else {
                              // For today or future dates: all statuses except overdue
                              return (
                                <>
                                  <option value="in_progress">🔄 В работе</option>
                                  <option value="approved">✅ Завершена</option>
                                  <option value="cancelled">❌ Отменена</option>
                                </>
                              )
                            }
                          })()}
                        </select>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <button
                          onClick={() => removeRow(idx, p)}
                          className="p-2 text-red-600 hover:text-red-900 hover:bg-red-50 rounded-lg transition-all duration-200"
                          title="Удалить пост"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  )
                })}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center">
                      <div className="text-gray-500">
                        <svg className="mx-auto h-12 w-12 text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                        </svg>
                        <p className="text-lg font-medium mb-2">Нет запланированных постов</p>
                        <p className="text-sm">Добавьте первый пост для начала планирования</p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ProjectDetail
