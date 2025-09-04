import { useState, useEffect } from 'react'
import { API_URL } from '../api'

interface Tax {
  id: number
  name: string
  rate: number
}

interface TaxForm {
  name: string
  rate: number
}

function Taxes() {
  const [taxes, setTaxes] = useState<Tax[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingTax, setEditingTax] = useState<Tax | null>(null)
  const [formData, setFormData] = useState<TaxForm>({ name: '', rate: 0 })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchTaxes()
  }, [])

  const fetchTaxes = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/taxes/`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setTaxes(data)
      }
    } catch (error) {
      console.error('Error fetching taxes:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    
    try {
      const token = localStorage.getItem('token')
      const url = editingTax 
        ? `${API_URL}/taxes/${editingTax.id}`
        : `${API_URL}/taxes/`
      const method = editingTax ? 'PUT' : 'POST'
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      })

      if (response.ok) {
        await fetchTaxes()
        resetForm()
      } else {
        alert('Ошибка при сохранении налога')
      }
    } catch (error) {
      console.error('Error saving tax:', error)
      alert('Ошибка при сохранении налога')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (taxId: number) => {
    if (!confirm('Вы уверены, что хотите удалить этот налог?')) {
      return
    }

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/taxes/${taxId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      })

      if (response.ok) {
        await fetchTaxes()
      } else {
        alert('Ошибка при удалении налога')
      }
    } catch (error) {
      console.error('Error deleting tax:', error)
      alert('Ошибка при удалении налога')
    }
  }

  const startEdit = (tax: Tax) => {
    setEditingTax(tax)
    setFormData({ name: tax.name, rate: tax.rate })
    setShowForm(true)
  }

  const resetForm = () => {
    setFormData({ name: '', rate: 0 })
    setEditingTax(null)
    setShowForm(false)
  }

  if (loading) {
    return <div className="p-6">Загрузка налогов...</div>
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Управление налогами</h2>
        <button
          onClick={() => setShowForm(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
        >
          Добавить налог
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">
            {editingTax ? 'Редактировать налог' : 'Добавить новый налог'}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Название налога
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Например: НДС"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Ставка налога (в десятичном виде)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={formData.rate}
                onChange={(e) => setFormData({ ...formData, rate: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Например: 0.20 для 20%"
                required
              />
              <p className="text-sm text-gray-500 mt-1">
                Введите как десятичное число: 0.20 = 20%, 0.13 = 13%
              </p>
            </div>
            <div className="flex space-x-2">
              <button
                type="submit"
                disabled={saving}
                className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {saving ? 'Сохранение...' : 'Сохранить'}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600"
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      )}
      
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Название
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Ставка
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Действия
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {taxes.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-6 py-4 text-center text-gray-500">
                  Налоги не найдены. Добавьте первый налог.
                </td>
              </tr>
            ) : (
              taxes.map((tax) => (
                <tr key={tax.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {tax.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {(tax.rate * 100).toFixed(1)}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                    <button
                      onClick={() => startEdit(tax)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      Редактировать
                    </button>
                    <button
                      onClick={() => handleDelete(tax.id)}
                      className="text-red-600 hover:text-red-900"
                    >
                      Удалить
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Taxes