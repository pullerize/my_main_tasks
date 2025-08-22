import { useEffect, useState } from 'react'
import { API_URL } from '../api'

function formatInput(value: string) {
  const digits = value.replace(/\D/g, '')
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
}

function parseNumber(value: string) {
  return parseFloat(value.replace(/[^0-9.,]/g, '').replace(/\s+/g, '').replace(',', '.')) || 0
}

interface Item {
  id: number
  name: string
  is_common: boolean
  unit_cost: number
}

function ExpensesAdmin() {
  const [items, setItems] = useState<Item[]>([])
  const [show, setShow] = useState(false)
  const [editing, setEditing] = useState<Item | null>(null)
  const [name, setName] = useState('')
  const [isCommon, setIsCommon] = useState(false)
  const [unitCost, setUnitCost] = useState('')

  const token = localStorage.getItem('token')

  const load = async () => {
    const res = await fetch(`${API_URL}/expense_items/`, { headers: { Authorization: `Bearer ${token}` } })
    if (res.ok) setItems(await res.json())
  }
  useEffect(() => { load() }, [])

  const openAdd = () => { setEditing(null); setName(''); setIsCommon(false); setUnitCost(''); setShow(true) }
  const openEdit = (it: Item) => { setEditing(it); setName(it.name); setIsCommon(it.is_common); setUnitCost(formatInput(String(it.unit_cost))); setShow(true) }

  const save = async () => {
    const payload = { name, is_common: isCommon, unit_cost: parseNumber(unitCost) }
    if (editing) {
      await fetch(`${API_URL}/expense_items/${editing.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload)
      })
    } else {
      await fetch(`${API_URL}/expense_items/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload)
      })
    }
    setShow(false)
    load()
  }

  const remove = async (id: number) => {
    await fetch(`${API_URL}/expense_items/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
    load()
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl">Расходы</h1>
        <button className="bg-blue-500 text-white px-3 py-1 rounded" onClick={openAdd}>Добавить</button>
      </div>
      <h2 className="text-xl mb-2">Общие расходы</h2>
      <table className="min-w-full bg-white border mb-6">
        <thead>
          <tr className="bg-gray-100">
            <th className="px-4 py-2 border">Название</th>
            <th className="px-4 py-2 border">Себестоимость</th>
            <th className="px-4 py-2 border"></th>
          </tr>
        </thead>
        <tbody>
          {items.filter(i => i.is_common).map(i => (
            <tr key={i.id} className="text-center border-t">
              <td className="px-4 py-2 border">{i.name}</td>
              <td className="px-4 py-2 border">{i.unit_cost.toLocaleString('ru-RU')}</td>
              <td className="px-4 py-2 border space-x-2">
                <button className="text-blue-500" onClick={() => openEdit(i)}>Редактировать</button>
                <button className="text-red-500" onClick={() => remove(i.id)}>Удалить</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="text-xl mb-2">Расходы по проектам</h2>
      <table className="min-w-full bg-white border">
        <thead>
          <tr className="bg-gray-100">
            <th className="px-4 py-2 border">Название</th>
            <th className="px-4 py-2 border"></th>
          </tr>
        </thead>
        <tbody>
          {items.filter(i => !i.is_common).map(i => (
            <tr key={i.id} className="text-center border-t">
              <td className="px-4 py-2 border">{i.name}</td>
              <td className="px-4 py-2 border space-x-2">
                <button className="text-blue-500" onClick={() => openEdit(i)}>Редактировать</button>
                <button className="text-red-500" onClick={() => remove(i.id)}>Удалить</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-4 rounded w-96">
            <h2 className="text-xl mb-2">{editing ? 'Редактировать расход' : 'Новый расход'}</h2>
            <input className="border p-2 w-full mb-2" placeholder="Название" value={name} onChange={e => setName(e.target.value)} />
            <label className="block mb-2">
              <span className="text-sm text-gray-500">Тип расхода</span>
              <select className="border p-2 w-full" value={isCommon ? 'common':'project'} onChange={e => setIsCommon(e.target.value==='common')}>
                <option value="project">Расход по проектам</option>
                <option value="common">Общий расход</option>
              </select>
            </label>
            {isCommon && (
              <label className="block mb-4">
                <span className="text-sm text-gray-500">Себестоимость</span>
                <input className="border p-2 w-full" value={unitCost} onChange={e => setUnitCost(formatInput(e.target.value))} />
              </label>
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

export default ExpensesAdmin
