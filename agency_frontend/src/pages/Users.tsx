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
    if (res.ok) {
      const data = await res.json()
      setUsers(data)
    }
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
    // Don't allow editing inactive users
    if (u.role === 'inactive') return
    
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

  const toggleStatus = async (user: User) => {
    await fetch(`${API_URL}/users/${user.id}/toggle-status`, {
      method: 'PUT',
      headers: { Authorization: `Bearer ${token}` },
    })
    load()
  }

  const deleteUser = async (user: User) => {
    if (confirm(`Вы уверены, что хотите удалить пользователя "${user.name}"?`)) {
      await fetch(`${API_URL}/users/${user.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      load()
    }
  }

  const getRoleDisplay = (role: string) => {
    const roleMap: { [key: string]: string } = {
      'designer': 'Дизайнер',
      'smm_manager': 'СММ-менеджер',
      'digital': 'Digital отдел',
      'admin': 'Администратор',
      'inactive': 'Неактивный'
    }
    return roleMap[role] || role
  }

  const groupUsersByRole = (users: User[]) => {
    const activeUsers = users.filter(u => u.role !== 'inactive')
    const inactiveUsers = users.filter(u => u.role === 'inactive')
    
    const grouped: { [key: string]: User[] } = {}
    activeUsers.forEach(user => {
      if (!grouped[user.role]) {
        grouped[user.role] = []
      }
      grouped[user.role].push(user)
    })
    
    return { grouped, inactiveUsers }
  }

  const getRoleOrder = () => {
    return ['admin', 'digital', 'smm_manager', 'designer']
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl">Пользователи</h1>
        <button className="bg-blue-500 text-white px-3 py-1 rounded" onClick={openAdd}>
          Добавить пользователя
        </button>
      </div>
      
      <div className="space-y-6">
        {(() => {
          const { grouped, inactiveUsers } = groupUsersByRole(users)
          const roleOrder = getRoleOrder()
          
          return (
            <>
              {roleOrder.map(roleKey => {
                if (!grouped[roleKey] || grouped[roleKey].length === 0) return null
                
                return (
                  <div key={roleKey} className="bg-white rounded-lg shadow">
                    <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 rounded-t-lg">
                      <h3 className="font-medium text-base text-gray-800">
                        {getRoleDisplay(roleKey)} ({grouped[roleKey].length})
                      </h3>
                    </div>
                    <div className="divide-y">
                      {grouped[roleKey].map(u => (
                        <div key={u.id} className="p-4 flex items-center justify-between hover:bg-gray-50">
                          <div className="flex-1">
                            <div className="flex items-center gap-3">
                              <span className="font-medium text-lg">{u.name}</span>
                            </div>
                            <div className="text-sm text-gray-500 mt-1">
                              Логин: {u.login}
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-2">
                            <button 
                              className="px-3 py-1 text-sm border border-blue-500 text-blue-500 rounded hover:bg-blue-50"
                              onClick={() => openEdit(u)}
                            >
                              Редактировать
                            </button>
                            <button 
                              className="px-3 py-1 text-sm bg-yellow-500 text-white rounded hover:bg-yellow-600"
                              onClick={() => toggleStatus(u)}
                            >
                              Сделать неактивным
                            </button>
                            <button 
                              className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600"
                              onClick={() => deleteUser(u)}
                            >
                              Удалить
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
              
              {inactiveUsers.length > 0 && (
                <div className="bg-white rounded-lg shadow">
                  <div className="px-4 py-2 bg-red-50 border-b border-red-200 rounded-t-lg">
                    <h3 className="font-medium text-base text-red-800">
                      Неактивные пользователи ({inactiveUsers.length})
                    </h3>
                  </div>
                  <div className="divide-y">
                    {inactiveUsers.map(u => (
                      <div key={u.id} className="p-4 flex items-center justify-between hover:bg-gray-50">
                        <div className="flex-1">
                          <div className="flex items-center gap-3">
                            <span className="font-medium text-lg text-gray-500">{u.name}</span>
                            <span className="text-sm text-red-600 bg-red-100 px-2 py-1 rounded">
                              Неактивный
                            </span>
                          </div>
                          <div className="text-sm text-gray-400 mt-1">
                            Логин: {u.login}
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <button 
                            className="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600"
                            onClick={() => toggleStatus(u)}
                          >
                            Активировать
                          </button>
                          <button 
                            className="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600"
                            onClick={() => deleteUser(u)}
                          >
                            Удалить
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )
        })()}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg w-96">
            <h2 className="text-xl font-semibold mb-4">
              {editing ? 'Редактировать пользователя' : 'Новый пользователь'}
            </h2>
            
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Логин</label>
                <input 
                  className="border p-2 w-full rounded" 
                  value={login} 
                  onChange={e => setLogin(e.target.value)} 
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Имя</label>
                <input 
                  className="border p-2 w-full rounded" 
                  value={name} 
                  onChange={e => setName(e.target.value)} 
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Пароль {editing && '(оставьте пустым, чтобы не менять)'}
                </label>
                <input 
                  type="password" 
                  className="border p-2 w-full rounded" 
                  value={password} 
                  onChange={e => setPassword(e.target.value)} 
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Роль</label>
                <select 
                  className="border p-2 w-full rounded" 
                  value={role} 
                  onChange={e => setRole(e.target.value)}
                >
                  <option value="designer">Дизайнер</option>
                  <option value="smm_manager">СММ-менеджер</option>
                  <option value="digital">Digital отдел</option>
                  <option value="admin">Администратор</option>
                </select>
              </div>
            </div>
            
            <div className="flex justify-end mt-6 gap-2">
              <button 
                className="px-4 py-2 border rounded hover:bg-gray-50" 
                onClick={() => setShowModal(false)}
              >
                Отмена
              </button>
              <button 
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600" 
                onClick={save}
              >
                Сохранить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Users