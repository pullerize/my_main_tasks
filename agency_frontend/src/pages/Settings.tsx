import { useState, useEffect, useRef } from 'react'
import { API_URL, authFetch } from '../api'

function Settings() {
  const [timezone, setTimezone] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState(null)
  const [clearing, setClearing] = useState(false)
  const [clearResult, setClearResult] = useState(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      const token = localStorage.getItem('token')
      
      // Загрузка настройки часового пояса
      const timezoneResponse = await fetch(`${API_URL}/settings/timezone`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (timezoneResponse.ok) {
        const data = await timezoneResponse.json()
        setTimezone(data.value || 'Asia/Tashkent')
      } else {
        setTimezone('Asia/Tashkent')
      }

    } catch (error) {
      console.error('Error fetching settings:', error)
      setTimezone('Asia/Tashkent')
    } finally {
      setLoading(false)
    }
  }

  const saveTimezone = async () => {
    setSaving(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/settings/timezone`, {
        method: 'PUT',
        headers: { 
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}` 
        },
        body: JSON.stringify({ value: timezone })
      })
      if (response.ok) {
        alert('Настройки сохранены')
      }
    } catch (error) {
      console.error('Error saving settings:', error)
      alert('Ошибка сохранения настроек')
    } finally {
      setSaving(false)
    }
  }



  const handleDatabaseDownload = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/admin/export-database`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        
        // Получаем имя файла из заголовка Content-Disposition или создаем свое
        const contentDisposition = response.headers.get('Content-Disposition')
        const filename = contentDisposition
          ? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
          : `database_export_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.zip`
        
        a.download = filename
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      } else {
        const data = await response.json()
        alert(`Ошибка экспорта: ${data.detail}`)
      }
    } catch (error) {
      console.error('Error downloading database:', error)
      alert('Ошибка при скачивании базы данных')
    }
  }

  const handleDatabaseImport = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    if (!file.name.endsWith('.db') && !file.name.endsWith('.zip')) {
      alert('Пожалуйста, выберите файл с расширением .db или .zip')
      return
    }

    setImporting(true)
    setImportResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/admin/import-database`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      })

      const data = await response.json()
      
      if (response.ok) {
        setImportResult(data)
        const availableTables = data.available_tables ? `\n\nОбнаруженные таблицы: ${data.available_tables.join(', ')}` : ''
        alert(`База данных успешно импортирована!\n
Импортировано:
- Пользователей: ${data.imported.users}
- Проектов: ${data.imported.projects}
- Задач: ${data.imported.tasks}
- Цифровых проектов: ${data.imported.digital_projects}
- Операторов: ${data.imported.operators}
- Статей расходов: ${data.imported.expense_items}
- Налогов: ${data.imported.taxes}
- CRM заявок: ${data.imported.leads || 0}
- Заметок к заявкам: ${data.imported.lead_notes || 0}
- Вложений к заявкам: ${data.imported.lead_attachments || 0}
- Истории заявок: ${data.imported.lead_history || 0}
- Категорий расходов: ${data.imported.expense_categories || 0}
- Расходов по проектам: ${data.imported.project_expenses || 0}
- Общих расходов: ${data.imported.common_expenses || 0}
- Расходов по цифр. проектам: ${data.imported.digital_project_expenses || 0}
- Расходов сотрудников: ${data.imported.employee_expenses || 0}
- Отчетов по проектам: ${data.imported.project_reports || 0}${availableTables}`)
      } else {
        alert(`Ошибка импорта: ${data.detail}`)
      }
    } catch (error) {
      console.error('Error importing database:', error)
      alert('Ошибка при импорте базы данных')
    } finally {
      setImporting(false)
      // Очищаем input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDatabaseClear = async () => {
    if (!confirm('ВНИМАНИЕ! Вы действительно хотите полностью очистить базу данных?\n\nЭто действие удалит ВСЕ данные (кроме вашего аккаунта администратора) и не может быть отменено!')) {
      return
    }

    if (!confirm('Вы уверены? ВСЕ проекты, задачи, пользователи и другие данные будут УДАЛЕНЫ БЕЗВОЗВРАТНО!')) {
      return
    }

    setClearing(true)
    setClearResult(null)

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/admin/clear-database`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      const data = await response.json()
      
      if (response.ok) {
        setClearResult(data)
        alert(`База данных успешно очищена!\n
Удалено:
- Пользователей: ${data.deleted.users}
- Проектов: ${data.deleted.projects}
- Задач: ${data.deleted.tasks}
- Повторяющихся задач: ${data.deleted.recurring_tasks || 0}
- Цифровых проектов: ${data.deleted.digital_projects}
- Операторов: ${data.deleted.operators}
- Статей расходов: ${data.deleted.expense_items}
- Налогов: ${data.deleted.taxes}
- Расходов: ${data.deleted.expenses}
- Расходов по проектам: ${data.deleted.project_expenses || 0}
- Общих расходов: ${data.deleted.common_expenses || 0}
- Расходов клиентов: ${data.deleted.project_client_expenses || 0}
- Расходов по цифр. проектам: ${data.deleted.digital_project_expenses || 0}
- Расходов сотрудников: ${data.deleted.employee_expenses || 0}
- Поступлений: ${data.deleted.receipts}
- Съемок: ${data.deleted.shootings}
- Постов: ${data.deleted.posts}
- Файлов: ${data.deleted.files}
- CRM заявок: ${data.deleted.leads || 0}
- Заметок к заявкам: ${data.deleted.lead_notes || 0}
- Вложений к заявкам: ${data.deleted.lead_attachments || 0}
- Истории заявок: ${data.deleted.lead_history || 0}
- Отчетов по проектам: ${data.deleted.project_reports || 0}`)
        
        // Перезагружаем страницу для обновления данных
        setTimeout(() => {
          window.location.reload()
        }, 2000)
      } else {
        alert(`Ошибка очистки: ${data.detail}`)
      }
    } catch (error) {
      console.error('Error clearing database:', error)
      alert('Ошибка при очистке базы данных')
    } finally {
      setClearing(false)
    }
  }

  if (loading) {
    return <div className="p-6">Загрузка настроек...</div>
  }

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-4">Настройки</h2>
      
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4">Основные настройки</h3>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Часовой пояс
          </label>
          <select 
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md"
          >
            <option value="Asia/Tashkent">Asia/Tashkent (UTC+5)</option>
            <option value="Europe/Moscow">Europe/Moscow (UTC+3)</option>
            <option value="UTC">UTC (UTC+0)</option>
          </select>
        </div>
        
        <button
          onClick={saveTimezone}
          disabled={saving}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Сохранение...' : 'Сохранить'}
        </button>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Импорт базы данных</h3>
        <p className="text-sm text-gray-600 mb-4">
          Загрузите файл базы данных (.db) или архив с базой и файлами (.zip) для импорта данных о пользователях, проектах, задачах и других сущностях.
          ZIP архивы также восстанавливают все загруженные файлы (логотипы, CRM вложения, контракты). Существующие записи с уникальными идентификаторами не будут дублироваться.
        </p>
        
        <div className="mb-4">
          <div className="flex gap-4 items-center">
            <input
              ref={fileInputRef}
              type="file"
              accept=".db,.zip"
              onChange={handleDatabaseImport}
              disabled={importing}
              className="block flex-1 text-sm text-gray-500
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-semibold
                file:bg-blue-50 file:text-blue-700
                hover:file:bg-blue-100
                disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              onClick={handleDatabaseDownload}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm font-semibold whitespace-nowrap"
            >
              📦 Скачать архив БД
            </button>
          </div>
        </div>

        {importing && (
          <div className="text-blue-600">
            <svg className="animate-spin inline-block h-5 w-5 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Импортирование базы данных...
          </div>
        )}

        {importResult && (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-md">
            <h4 className="text-sm font-semibold text-green-800 mb-2">Импорт успешно завершен!</h4>
            <ul className="text-sm text-green-700">
              <li>Пользователей: {importResult.imported.users}</li>
              <li>Проектов: {importResult.imported.projects}</li>
              <li>Задач: {importResult.imported.tasks}</li>
              <li>Цифровых проектов: {importResult.imported.digital_projects}</li>
              <li>Операторов: {importResult.imported.operators}</li>
              <li>Статей расходов: {importResult.imported.expense_items}</li>
              <li>Налогов: {importResult.imported.taxes}</li>
            </ul>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow p-6 mt-6 border-2 border-red-200">
        <h3 className="text-lg font-semibold mb-4 text-red-600">Опасная зона</h3>
        <p className="text-sm text-gray-600 mb-4">
          <strong className="text-red-600">ВНИМАНИЕ!</strong> Очистка базы данных удалит ВСЕ данные безвозвратно.
          Это действие нельзя отменить. Будут удалены все проекты, задачи, пользователи (кроме вашего аккаунта),
          расходы, поступления и другие данные.
        </p>
        
        <button
          onClick={handleDatabaseClear}
          disabled={clearing}
          className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 font-semibold"
        >
          {clearing ? (
            <>
              <svg className="animate-spin inline-block h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Очистка базы данных...
            </>
          ) : (
            '🗑️ Очистить базу данных'
          )}
        </button>

        {clearResult && (
          <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
            <h4 className="text-sm font-semibold text-yellow-800 mb-2">База данных очищена!</h4>
            <ul className="text-sm text-yellow-700">
              <li>Удалено пользователей: {clearResult.deleted.users}</li>
              <li>Удалено проектов: {clearResult.deleted.projects}</li>
              <li>Удалено задач: {clearResult.deleted.tasks}</li>
              <li>Удалено цифровых проектов: {clearResult.deleted.digital_projects}</li>
              <li>Удалено операторов: {clearResult.deleted.operators}</li>
              <li>Удалено расходов: {clearResult.deleted.expenses}</li>
              <li>Удалено поступлений: {clearResult.deleted.receipts}</li>
              <li>Удалено файлов: {clearResult.deleted.files}</li>
            </ul>
            <p className="text-sm text-yellow-700 mt-2 font-semibold">Страница будет перезагружена...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default Settings