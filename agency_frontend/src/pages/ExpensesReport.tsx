import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { API_URL } from '../api'

const MONTH_NAMES = [
  'Январь','Февраль','Март','Апрель','Май','Июнь',
  'Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'
]

interface Project { id:number; name:string }
interface Row { name:string; quantity:number; unit_avg:number }

function fmt(d:Date){ return d.toISOString().slice(0,10) }

function ExpensesReport(){
  const token = localStorage.getItem('token')
  const [projects,setProjects] = useState<Project[]>([])
  const [projectId,setProjectId] = useState<number|''>('')
  const [month,setMonth] = useState(new Date().getMonth()+1)
  const year = new Date().getFullYear()

  const monthRange = (y:number,m:number) => {
    const first = new Date(Date.UTC(y, m-1, 1))
    const last = new Date(Date.UTC(y, m, 0))
    return [fmt(first), fmt(last)] as const
  }

  const [start,setStart] = useState(() => monthRange(year, month)[0])
  const [end,setEnd] = useState(() => monthRange(year, month)[1])
  const [rows,setRows] = useState<Row[]>([])

  const loadProjects = async () => {
    const res = await fetch(`${API_URL}/projects/`, { headers:{Authorization:`Bearer ${token}`}})
    if(res.ok) setProjects(await res.json())
  }

  const loadReport = async () => {
    const params = new URLSearchParams()
    params.append('start', start)
    const endDate = new Date(end)
    endDate.setDate(endDate.getDate() + 1)
    params.append('end', fmt(endDate))
    if(projectId) params.append('project_id', String(projectId))
    const res = await fetch(`${API_URL}/expenses/report?${params}`, { headers:{Authorization:`Bearer ${token}`}})
    if(res.ok) setRows(await res.json())
  }

  useEffect(()=>{ loadProjects() },[])
  useEffect(()=>{
    const [s,e] = monthRange(year, month)
    setStart(s)
    setEnd(e)
  },[month])
  useEffect(()=>{ loadReport() },[start,end,projectId])

  return (
    <div className="p-4 space-y-4">
      <div className="space-x-2 mb-4">
        <Link to="/reports" className="px-2 py-1 border rounded">Отчеты по проектам</Link>
        <button className="px-2 py-1 border rounded bg-blue-500 text-white">Отчет по расходам</button>
      </div>
      <h1 className="text-2xl mb-4">Отчет по расходам</h1>
      <div className="flex space-x-2">
        <select className="border p-2" value={month} onChange={e=>setMonth(Number(e.target.value))}>
          {MONTH_NAMES.map((m,i)=>(<option key={i+1} value={i+1}>{m}</option>))}
        </select>
        <input type="date" className="border p-2" value={start} onChange={e=>setStart(e.target.value)} />
        <input type="date" className="border p-2" value={end} onChange={e=>setEnd(e.target.value)} />
        <select className="border p-2" value={projectId} onChange={e=>setProjectId(e.target.value ? Number(e.target.value):'')}>
          <option value="">Все проекты</option>
          {projects.map(p=>(<option key={p.id} value={p.id}>{p.name}</option>))}
        </select>
      </div>
      <table className="min-w-full bg-white border mt-4">
        <thead>
          <tr className="bg-gray-100">
            <th className="px-4 py-2 border">Наименование</th>
            <th className="px-4 py-2 border">Количество</th>
            <th className="px-4 py-2 border">Себестоимость</th>
            <th className="px-4 py-2 border">Итого</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r=> (
            <tr key={r.name} className="text-center border-t">
              <td className="px-4 py-2 border">{r.name}</td>
              <td className="px-4 py-2 border">{r.quantity}</td>
              <td className="px-4 py-2 border">{r.unit_avg.toLocaleString('ru-RU')}</td>
              <td className="px-4 py-2 border">{(r.quantity*r.unit_avg).toLocaleString('ru-RU')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default ExpensesReport
