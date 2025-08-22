import { useEffect, useState } from 'react'
import { API_URL } from '../api'

interface User {
  id: number
  login: string
  name: string
  role: string
}

function Users() {
  const [users, setUsers] = useState<User[]>([])
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)
  const [login, setLogin] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('designer')

  const token = localStorage.getItem('token')

  const load = async () => {
    const res = await fetch(`${API_URL}/users/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) setUsers(await res.json())
  }

  useEffect(() => { load() }, [])

  const openAdd = () => {
    setEditing(null)
    setLogin('')
    setName('')
    setPassword('')
    setRole('designer')
    setShowModal(true)
  }

  const openEdit = (u: User) => {
    setEditing(u)
    setLogin(u.login)
    setName(u.name)
    setPassword('')
    setRole(u.role)
    setShowModal(true)
  }

  const save = async () => {
    const payload: any = { login, name, role }
    if (password) payload.password = password
    if (editing) {
      await fetch(`${API_URL}/users/${editing.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      })
    } else {
      payload.password = password
      await fetch(`${API_URL}/users/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      })
    }
    setShowModal(false)
    load()
  }

  const remove = async (id: number) => {
    await fetch(`${API_URL}/users/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    load()
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl">Пользователи</h1>
        <button className="bg-blue-500 text-white px-3 py-1 rounded" onClick={openAdd}>Добавить</button>
      </div>
      <table className="min-w-full bg-white border">
        <thead>
          <tr className="bg-gray-100">
            <th className="px-4 py-2 border">Логин</th>
            <th className="px-4 py-2 border">Имя</th>
            <th className="px-4 py-2 border">Роль</th>
            <th className="px-4 py-2 border"></th>
          </tr>
        </thead>
        <tbody>
          {users.map(u => (
            <tr key={u.id} className="text-center border-t">
              <td className="px-4 py-2 border">{u.login}</td>
              <td className="px-4 py-2 border">{u.name}</td>
              <td className="px-4 py-2 border">{u.role}</td>
              <td className="px-4 py-2 border space-x-2">
                <button className="text-blue-500" onClick={() => openEdit(u)}>Редактировать</button>
                <button className="text-red-500" onClick={() => remove(u.id)}>Удалить</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-4 rounded w-96">
            <h2 className="text-xl mb-2">{editing ? 'Редактировать пользователя' : 'Новый пользователь'}</h2>
            <input className="border p-2 w-full mb-2" placeholder="Логин" value={login} onChange={e => setLogin(e.target.value)} />
            <input className="border p-2 w-full mb-2" placeholder="Имя" value={name} onChange={e => setName(e.target.value)} />
            <input type="password" className="border p-2 w-full mb-2" placeholder="Пароль" value={password} onChange={e => setPassword(e.target.value)} />
            <select className="border p-2 w-full mb-4" value={role} onChange={e => setRole(e.target.value)}>
              <option value="designer">Дизайнер</option>
              <option value="smm_manager">СММ-менеджер</option>
              <option value="head_smm">Head of SMM</option>
              <option value="digital">Digital</option>
              <option value="admin">Админ</option>
            </select>
            <div className="flex justify-end">
              <button className="mr-2 px-4 py-1 border rounded" onClick={() => setShowModal(false)}>Отмена</button>
              <button className="bg-blue-500 text-white px-4 py-1 rounded" onClick={save}>Сохранить</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Users
