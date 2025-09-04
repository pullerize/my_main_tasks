import { useEffect, useState } from 'react'
import { API_URL } from '../api'

function formatInput(value: string) {
  const digits = value.replace(/\D/g, '')
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

function parseNumber(value: string) {
  return parseFloat(value.replace(/[^0-9.,]/g, '').replace(/\s+/g, '').replace(',', '.')) || 0
}

interface Operator {
  id: number
  name: string
  role: string
  color: string
  price_per_video: number
  is_salaried: boolean
  monthly_salary?: number
}

function Operators() {
  const [items, setItems] = useState<Operator[]>([])
  const [show, setShow] = useState(false)
  const [editing, setEditing] = useState<Operator | null>(null)
  const [name, setName] = useState('')
  const [role, setRole] = useState('mobile')
  const [color, setColor] = useState('#ff0000')
  const [price, setPrice] = useState('')
  const [isSalaried, setIsSalaried] = useState(false)
  const [salary, setSalary] = useState('')

  const token = localStorage.getItem('token')

  const load = async () => {
    if (!token) {
      setItems([])
      return
    }

    try {
      const res = await fetch(`${API_URL}/operators/`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setItems(Array.isArray(data) ? data : [])
      } else {
        setItems([])
      }
    } catch (error) {
      setItems([])
    }
  }

  useEffect(() => { load() }, [])

  const openAdd = () => {
    setEditing(null)
    setName('')
    setRole('mobile')
    setColor('#ff0000')
    setPrice('')
    setIsSalaried(false)
    setSalary('')
    setShow(true)
  }

  const openEdit = (o: Operator) => {
    setEditing(o)
    setName(o.name)
    setRole(o.role)
    setColor(o.color)
    setPrice(formatInput(String(o.price_per_video || 0)))
    setIsSalaried(o.is_salaried || false)
    setSalary(formatInput(String(o.monthly_salary || 0)))
    setShow(true)
  }

  const save = async () => {
    const payload = { 
      name, 
      role, 
      color, 
      is_salaried: isSalaried,
      price_per_video: isSalaried ? 0 : parseNumber(price),
      monthly_salary: isSalaried ? parseNumber(salary) : null
    }
    if (editing) {
      await fetch(`${API_URL}/operators/${editing.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      })
    } else {
      await fetch(`${API_URL}/operators/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      })
    }
    setShow(false)
    load()
  }

  const remove = async (id: number) => {
    await fetch(`${API_URL}/operators/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    load()
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl">Операторы</h1>
        <button className="bg-blue-500 text-white px-3 py-1 rounded" onClick={openAdd}>Добавить</button>
      </div>
      <table className="min-w-full bg-white border">
        <thead>
          <tr className="bg-gray-100">
            <th className="px-4 py-2 border">Имя</th>
            <th className="px-4 py-2 border">Роль</th>
            <th className="px-4 py-2 border">Цвет</th>
            <th className="px-4 py-2 border">Оплата</th>
            <th className="px-4 py-2 border"></th>
          </tr>
        </thead>
        <tbody>
          {Array.isArray(items) && items.map(o => (
            <tr key={o.id} className="text-center border-t">
              <td className="px-4 py-2 border">{o.name}</td>
              <td className="px-4 py-2 border">{o.role === 'mobile' ? 'Мобилограф' : o.role === 'video' ? 'Видеограф' : o.role}</td>
              <td className="px-4 py-2 border">
                <span className="inline-block w-4 h-4 rounded" style={{background:o.color}} />
              </td>
              <td className="px-4 py-2 border">
                {o.is_salaried 
                  ? `${(o.monthly_salary || 0).toLocaleString('ru-RU')} сум/мес` 
                  : `${(o.price_per_video || 0).toLocaleString('ru-RU')} сум/видео`}
              </td>
              <td className="px-4 py-2 border space-x-2">
                <button className="text-blue-500" onClick={() => openEdit(o)}>Редактировать</button>
                <button className="text-red-500" onClick={() => remove(o.id)}>Удалить</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-4 rounded w-96">
            <h2 className="text-xl mb-2">{editing ? 'Редактировать оператора' : 'Новый оператор'}</h2>
            <input className="border p-2 w-full mb-2" placeholder="Имя" value={name} onChange={e => setName(e.target.value)} />
            <select className="border p-2 w-full mb-4" value={role} onChange={e => setRole(e.target.value)}>
              <option value="mobile">Мобилограф</option>
              <option value="video">Видеограф</option>
            </select>
            <label className="block mb-4">Цвет
              <input type="color" className="border p-2 w-full" value={color} onChange={e => setColor(e.target.value)} />
            </label>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Тип оплаты</label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="paymentType"
                    checked={!isSalaried}
                    onChange={() => setIsSalaried(false)}
                    className="mr-2"
                  />
                  За видео
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    name="paymentType"
                    checked={isSalaried}
                    onChange={() => setIsSalaried(true)}
                    className="mr-2"
                  />
                  Фиксированная зарплата
                </label>
              </div>
            </div>
            
            {!isSalaried ? (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Цена за видео</label>
                <div className="relative">
                  <input 
                    className="border p-2 w-full pr-12" 
                    placeholder="300 000" 
                    value={price} 
                    onChange={e => setPrice(formatInput(e.target.value))} 
                  />
                  <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500">сум</span>
                </div>
              </div>
            ) : (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Месячная зарплата</label>
                <div className="relative">
                  <input 
                    className="border p-2 w-full pr-12" 
                    placeholder="5 000 000" 
                    value={salary} 
                    onChange={e => setSalary(formatInput(e.target.value))} 
                  />
                  <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500">сум</span>
                </div>
              </div>
            )}
            <div className="flex justify-end">
              <button className="mr-2 px-4 py-1 border rounded" onClick={() => setShow(false)}>Отмена</button>
              <button className="bg-blue-500 text-white px-4 py-1 rounded" onClick={save}>Сохранить</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Operators
