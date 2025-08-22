import { useEffect, useState } from 'react'
import { API_URL } from '../api'

interface Project {
  id: number
  name: string
  logo?: string
  high_priority?: boolean
}

function Projects() {
  const [items, setItems] = useState<Project[]>([])
  const [show, setShow] = useState(false)
  const [showLogoModal, setShowLogoModal] = useState(false)
  const [editing, setEditing] = useState<Project | null>(null)
  const [editingLogo, setEditingLogo] = useState<Project | null>(null)
  const [name, setName] = useState('')
  const [logo, setLogo] = useState<File | null>(null)

  const token = localStorage.getItem('token')

  const load = async () => {
    const res = await fetch(`${API_URL}/projects/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) {
      const data: Project[] = await res.json()
      setItems(data)
    }
  }

  useEffect(() => { load() }, [])

  const openAdd = () => {
    setEditing(null)
    setName('')
    setLogo(null)
    setShow(true)
  }

  const openEdit = (p: Project) => {
    setEditing(p)
    setName(p.name)
    setLogo(null)
    setShow(true)
  }

  const openLogoEdit = (p: Project) => {
    setEditingLogo(p)
    setShowLogoModal(true)
  }

  const downloadLogo = async (project: Project) => {
    if (!project.logo) return
    try {
      const response = await fetch(`${API_URL}/${project.logo}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${project.name}_logo.${project.logo.split('.').pop()}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Ошибка при скачивании логотипа:', error)
    }
  }

  const save = async () => {
    const payload = { name, high_priority: editing ? editing.high_priority ?? false : false }
    let proj: Project | null = null
    if (editing) {
      const res = await fetch(`${API_URL}/projects/${editing.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      })
      if (res.ok) proj = await res.json()
    } else {
      const res = await fetch(`${API_URL}/projects/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(payload),
      })
      if (res.ok) proj = await res.json()
    }
    if (proj && logo) {
      const form = new FormData()
      form.append('file', logo)
      const lr = await fetch(`${API_URL}/projects/${proj.id}/logo`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      if (lr.ok) {
        const data = await lr.json()
        proj.logo = data.logo
      }
    }
    setShow(false)
    setLogo(null)
    load()
  }

  const changeLogo = async (file: File) => {
    if (!editingLogo) return
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_URL}/projects/${editingLogo.id}/logo`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    })
    if (res.ok) {
      const data = await res.json()
      setItems(items.map(it => it.id === editingLogo.id ? { ...it, logo: data.logo } : it))
      setShowLogoModal(false)
      setEditingLogo(null)
    }
  }

  const removeLogo = async (id: number) => {
    const res = await fetch(`${API_URL}/projects/${id}/logo`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.ok) setItems(items.map(it => it.id === id ? { ...it, logo: undefined } : it))
  }

  const remove = async (id: number) => {
    await fetch(`${API_URL}/projects/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    load()
  }

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl">Проекты</h1>
        <button className="bg-blue-500 text-white px-3 py-1 rounded" onClick={openAdd}>Добавить</button>
      </div>
      <table className="min-w-full bg-white border">
        <thead>
          <tr className="bg-gray-100">
            <th className="px-4 py-2 border">Логотип</th>
            <th className="px-4 py-2 border">Название</th>
            <th className="px-4 py-2 border"></th>
          </tr>
        </thead>
        <tbody>
          {items.map(p => (
            <tr key={p.id} className="text-center border-t">
              <td className="px-4 py-2 border">
                {p.logo ? (
                  <img src={`${API_URL}/${p.logo}`} className="w-12 h-12 object-cover mx-auto" />
                ) : (
                  <span className="text-sm text-gray-500">Нет логотипа</span>
                )}
              </td>
              <td className="px-4 py-2 border">{p.name}</td>
              <td className="px-4 py-2 border space-x-2">
                <button className="text-blue-500" onClick={() => openEdit(p)}>Редактировать</button>
                <button className="text-green-500" onClick={() => openLogoEdit(p)}>Логотип</button>
                <button className="text-red-500" onClick={() => remove(p.id)}>Удалить</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {show && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-4 rounded w-96">
            <h2 className="text-xl mb-2">{editing ? 'Редактировать проект' : 'Новый проект'}</h2>
            <input className="border p-2 w-full mb-2" placeholder="Название" value={name} onChange={e => setName(e.target.value)} />
            {!editing && (
              <input type="file" className="border p-2 w-full mb-4" onChange={e => setLogo(e.target.files ? e.target.files[0] : null)} />
            )}
            <div className="flex justify-end">
              <button className="mr-2 px-4 py-1 border rounded" onClick={() => setShow(false)}>Отмена</button>
              <button className="bg-blue-500 text-white px-4 py-1 rounded" onClick={save}>Сохранить</button>
            </div>
          </div>
        </div>
      )}

      {showLogoModal && editingLogo && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded w-96">
            <h2 className="text-xl mb-4">Логотип проекта "{editingLogo.name}"</h2>
            
            {editingLogo.logo && (
              <div className="mb-4 text-center">
                <img src={`${API_URL}/${editingLogo.logo}`} className="w-24 h-24 object-cover mx-auto mb-2" />
                <p className="text-sm text-gray-600">Текущий логотип</p>
              </div>
            )}

            <div className="space-y-3">
              <label className="block">
                <input 
                  type="file" 
                  className="hidden" 
                  accept="image/*"
                  onChange={e => e.target.files && changeLogo(e.target.files[0])}
                />
                <span className="w-full bg-blue-500 text-white px-4 py-2 rounded cursor-pointer inline-block text-center">
                  Выберите файл
                </span>
              </label>
              
              {editingLogo.logo && (
                <button 
                  className="w-full bg-green-500 text-white px-4 py-2 rounded"
                  onClick={() => downloadLogo(editingLogo)}
                >
                  Скачать файл
                </button>
              )}
            </div>

            <div className="flex justify-end mt-4">
              <button 
                className="px-4 py-1 border rounded" 
                onClick={() => {setShowLogoModal(false); setEditingLogo(null)}}
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Projects

