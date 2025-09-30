import { useState, useEffect } from 'react'
import { API_URL } from '../api'
import { ConfirmationModal } from '../components/ConfirmationModal'
import { useToast } from '../components/ToastNotification'

interface Lead {
  id: number
  title: string
  source: string
  status: string
  manager_id?: number
  client_name?: string
  client_contact?: string
  description?: string
  company_name?: string
  proposal_amount?: number
  proposal_date?: string
  deal_amount?: number
  rejection_reason?: string
  created_at: string
  updated_at: string
  last_activity_at: string
  reminder_date?: string
  waiting_started_at?: string
  manager?: {
    id: number
    name: string
  }
  notes: Array<{
    id: number
    content: string
    lead_status?: string
    created_at: string
    user: {
      name: string
    }
  }>
  attachments: Array<{
    id: number
    filename: string
    uploaded_at: string
  }>
  history: Array<{
    id: number
    action: string
    old_value?: string
    new_value?: string
    description: string
    created_at: string
    user: {
      name: string
    }
  }>
}

interface LeadStats {
  total_leads: number
  active_leads: number
  success_leads: number
  rejected_leads: number
  conversion_rate: number
  average_processing_time: number
}

const LEAD_SOURCES = [
  { value: 'instagram', label: 'Instagram' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'telegram', label: 'Telegram' },
  { value: 'search', label: 'Поисковая выдача' },
  { value: 'referral', label: 'Знакомые' },
  { value: 'other', label: 'Другое' }
]

const LEAD_STATUSES = {
  new: { label: 'Новая заявка', color: 'bg-blue-500' },
  in_progress: { label: 'Взят в обработку', color: 'bg-yellow-500' },
  negotiation: { label: 'Созвон / переговоры', color: 'bg-orange-500' },
  proposal: { label: 'К.П.', color: 'bg-purple-500' },
  waiting: { label: 'Ожидание ответа', color: 'bg-indigo-500' },
  success: { label: 'Успешно', color: 'bg-green-500' },
  rejected: { label: 'Отказ', color: 'bg-red-500' }
}

const getActivityColor = (lastActivity: string) => {
  const now = new Date()
  const activityDate = new Date(lastActivity)
  const daysDiff = Math.floor((now.getTime() - activityDate.getTime()) / (1000 * 60 * 60 * 24))
  
  if (daysDiff >= 7) return 'border-red-400 bg-red-50'
  if (daysDiff >= 3) return 'border-yellow-400 bg-yellow-50'
  return 'border-gray-200 bg-white'
}

function LeadCard({ lead, onUpdate, onDragStart, onCardClick, isCompact = false }: { 
  lead: Lead, 
  onUpdate: () => void,
  onDragStart: (e: React.DragEvent, lead: Lead) => void,
  onCardClick: (lead: Lead) => void,
  isCompact?: boolean
}) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editData, setEditData] = useState({
    title: lead.title,
    client_name: lead.client_name || '',
    proposal_amount: lead.proposal_amount || 0,
    deal_amount: lead.deal_amount || 0,
    rejection_reason: lead.rejection_reason || ''
  })

  const updateLead = async (updates: any) => {
    const token = localStorage.getItem('token')
    try {
      const response = await fetch(`${API_URL}/leads/${lead.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(updates)
      })
      
      if (response.ok) {
        onUpdate()
        setIsEditing(false)
      }
    } catch (error) {
      console.error('Error updating lead:', error)
    }
  }

  const handleStatusChange = async (newStatus: string) => {
    const updates: any = { status: newStatus }
    
    if (newStatus === 'success' && !lead.deal_amount) {
      const amount = prompt('Введите сумму сделки:')
      if (amount) {
        updates.deal_amount = parseFloat(amount)
      }
    }
    
    if (newStatus === 'rejected' && !lead.rejection_reason) {
      const reason = prompt('Введите причину отказа:')
      if (reason) {
        updates.rejection_reason = reason
      }
    }
    
    await updateLead(updates)
  }

  if (isCompact) {
    return (
      <div 
        className={`p-2 lg:p-3 rounded-lg shadow-sm border-l-4 cursor-pointer transition-all ${getActivityColor(lead.last_activity_at)} mb-2`}
        draggable
        onDragStart={(e) => onDragStart(e, lead)}
        onClick={() => onCardClick(lead)}
      >
        <div className="flex justify-between items-center">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm lg:text-xs font-medium text-gray-900 truncate mb-1">{lead.company_name || lead.title}</h3>
            <div className="text-sm lg:text-xs text-gray-600 space-y-1">
              {lead.manager && (
                <div className="truncate">📋 {lead.manager.name}</div>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div 
      className={`p-2 lg:p-3 rounded-lg shadow-sm border-l-4 cursor-pointer transition-all ${getActivityColor(lead.last_activity_at)}`}
      draggable
      onDragStart={(e) => onDragStart(e, lead)}
    >
      <div onClick={() => onCardClick(lead)}>
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-sm lg:text-xs font-medium text-gray-900 truncate">{lead.company_name || lead.title}</h3>
        </div>
        
        <div className="text-xs lg:text-xs text-gray-600 mb-2 space-y-1">
          {lead.client_name && <div>{lead.client_name}</div>}
          {lead.client_contact && <div>📞 {lead.client_contact}</div>}
          {lead.manager && <div>📋 {lead.manager.name}</div>}
        </div>
        
        {lead.proposal_amount && (
          <div className="text-xs text-green-600 mb-2">
            💰 КП: {Math.round(lead.proposal_amount / 1000)}k ₽
          </div>
        )}
        
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">
            {new Date(lead.created_at).toLocaleDateString('ru', { day: '2-digit', month: '2-digit' })}
          </span>
          <div className="flex space-x-1">
            {lead.notes.length > 0 && (
              <span className="text-xs bg-blue-100 text-blue-800 px-1 py-1 rounded">
                📝{lead.notes.length}
              </span>
            )}
            {lead.attachments.length > 0 && (
              <span className="text-xs bg-green-100 text-green-800 px-1 py-1 rounded">
                📎{lead.attachments.length}
              </span>
            )}
          </div>
        </div>
      </div>
      
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="space-y-2 mb-4">
            <select
              value={lead.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              {Object.entries(LEAD_STATUSES).map(([status, config]) => (
                <option key={status} value={status}>{config.label}</option>
              ))}
            </select>
            
            {lead.status === 'proposal' && (
              <input
                type="number"
                placeholder="Сумма предложения"
                value={lead.proposal_amount || ''}
                onChange={(e) => updateLead({ proposal_amount: parseFloat(e.target.value) })}
                className="w-full px-3 py-2 border rounded-lg"
              />
            )}
            
            {lead.status === 'success' && (
              <input
                type="number"
                placeholder="Сумма сделки"
                value={lead.deal_amount || ''}
                onChange={(e) => updateLead({ deal_amount: parseFloat(e.target.value) })}
                className="w-full px-3 py-2 border rounded-lg"
              />
            )}
            
            {lead.status === 'rejected' && (
              <textarea
                placeholder="Причина отказа"
                value={lead.rejection_reason || ''}
                onChange={(e) => updateLead({ rejection_reason: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg resize-none"
                rows={2}
              />
            )}
          </div>
          
          <div className="text-xs text-gray-500">
            Последняя активность: {new Date(lead.last_activity_at).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  )
}

// Функция для форматирования времени в секундах в читаемый формат
function formatDuration(seconds: number): string {
  if (seconds === 0) return '0 минут'

  const days = Math.floor(seconds / (24 * 60 * 60))
  const hours = Math.floor((seconds % (24 * 60 * 60)) / (60 * 60))
  const minutes = Math.floor((seconds % (60 * 60)) / 60)

  const parts = []
  if (days > 0) parts.push(`${days} ${days === 1 ? 'день' : days < 5 ? 'дня' : 'дней'}`)
  if (hours > 0) parts.push(`${hours} ${hours === 1 ? 'час' : hours < 5 ? 'часа' : 'часов'}`)
  if (minutes > 0) parts.push(`${minutes} ${minutes === 1 ? 'минута' : minutes < 5 ? 'минуты' : 'минут'}`)

  return parts.join(', ')
}

function LeadBoard() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [stats, setStats] = useState<LeadStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [filterManager, setFilterManager] = useState('')
  const [filterSource, setFilterSource] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [filterDateFrom, setFilterDateFrom] = useState('')
  const [filterDateTo, setFilterDateTo] = useState('')
  const [customSource, setCustomSource] = useState('')
  const [selectedSource, setSelectedSource] = useState('')
  const [draggedLead, setDraggedLead] = useState<Lead | null>(null)
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
  const [newComment, setNewComment] = useState('')
  const [isEditingLead, setIsEditingLead] = useState(false)
  const [editLeadData, setEditLeadData] = useState<any>({})
  const [phoneNumber, setPhoneNumber] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isUploadingFile, setIsUploadingFile] = useState(false)
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
    type?: 'warning' | 'danger' | 'info';
  }>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {}
  })
  const { showToast } = useToast()

  const loadLeads = async () => {
    const token = localStorage.getItem('token')
    try {
      const params = new URLSearchParams()
      if (filterManager) params.append('manager_id', filterManager)
      if (filterSource) params.append('source', filterSource)
      if (filterDateFrom) params.append('created_from', filterDateFrom)
      if (filterDateTo) params.append('created_to', filterDateTo)

      const response = await fetch(`${API_URL}/leads/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (response.ok) {
        const data = await response.json()
        setLeads(data)
      }
    } catch (error) {
      console.error('Error loading leads:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    const token = localStorage.getItem('token')
    try {
      const response = await fetch(`${API_URL}/leads/analytics/`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      if (response.ok) {
        const data = await response.json()
        setStats(data.stats)
      }
    } catch (error) {
      console.error('Error loading stats:', error)
    }
  }

  useEffect(() => {
    loadLeads()
    loadStats()
  }, [filterManager, filterSource, filterDateFrom, filterDateTo])

  const handleDragStart = (e: React.DragEvent, lead: Lead) => {
    setDraggedLead(lead)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDrop = async (e: React.DragEvent, newStatus: string) => {
    e.preventDefault()
    if (draggedLead && draggedLead.status !== newStatus) {
      const token = localStorage.getItem('token')
      try {
        await fetch(`${API_URL}/leads/${draggedLead.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ status: newStatus })
        })
        loadLeads()
        loadStats()
      } catch (error) {
        console.error('Error updating lead status:', error)
      }
    }
    setDraggedLead(null)
  }

  const deleteLead = async (leadId: number) => {
    setConfirmModal({
      isOpen: true,
      title: 'Удаление заявки',
      message: 'Вы уверены, что хотите удалить эту заявку? Это действие необратимо.',
      type: 'danger',
      onConfirm: () => performDeleteLead(leadId)
    })
  }

  const performDeleteLead = async (leadId: number) => {
    
    const token = localStorage.getItem('token')
    try {
      const response = await fetch(`${API_URL}/leads/${leadId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        setSelectedLead(null)
        loadLeads()
        loadStats()
      }
    } catch (error) {
      console.error('Error deleting lead:', error)
    }
  }

  const addComment = async (leadId: number) => {
    if (!newComment.trim()) return
    
    const token = localStorage.getItem('token')
    try {
      const response = await fetch(`${API_URL}/leads/${leadId}/notes/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ content: newComment })
      })
      
      if (response.ok) {
        setNewComment('')
        loadLeads()
        // Обновить выбранную заявку
        const updatedLead = leads.find(l => l.id === leadId)
        if (updatedLead) {
          const refreshResponse = await fetch(`${API_URL}/leads/${leadId}`, {
            headers: { Authorization: `Bearer ${token}` }
          })
          if (refreshResponse.ok) {
            const refreshedLead = await refreshResponse.json()
            setSelectedLead(refreshedLead)
          }
        }
      }
    } catch (error) {
      console.error('Error adding comment:', error)
    }
  }

  const uploadFile = async (leadId: number, file: File) => {
    console.log('uploadFile called with:', leadId, file)
    if (!file) {
      console.log('No file provided')
      return
    }

    const token = localStorage.getItem('token')
    console.log('Token:', token ? 'exists' : 'missing')
    const formData = new FormData()
    formData.append('file', file)

    try {
      setIsUploadingFile(true)
      console.log(`Making request to: ${API_URL}/leads/${leadId}/attachments/`)
      const response = await fetch(`${API_URL}/leads/${leadId}/attachments/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`
        },
        body: formData
      })

      console.log('Upload response status:', response.status)
      if (response.ok) {
        console.log('File uploaded successfully')
        setSelectedFile(null)
        // Обновить заявку чтобы показать новый файл
        const refreshResponse = await fetch(`${API_URL}/leads/${leadId}`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (refreshResponse.ok) {
          const refreshedLead = await refreshResponse.json()
          setSelectedLead(refreshedLead)
          console.log('Lead refreshed with attachments:', refreshedLead.attachments)
        }
        loadLeads()
        showToast('Файл успешно загружен!', 'success')
      } else {
        const errorText = await response.text()
        console.error('Upload failed:', response.status, errorText)
        showToast('Ошибка при загрузке файла: ' + errorText, 'error')
      }
    } catch (error) {
      console.error('Error uploading file:', error)
      showToast('Ошибка при загрузке файла', 'error')
    } finally {
      setIsUploadingFile(false)
    }
  }

  const handleDownloadAttachment = async (attachmentId: number, filename: string) => {
    const token = localStorage.getItem('token')
    if (!token) return

    try {
      const response = await fetch(`${API_URL}/leads/attachments/${attachmentId}/download`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      } else {
        showToast('Ошибка при скачивании файла', 'error')
      }
    } catch (error) {
      console.error('Error downloading file:', error)
      showToast('Ошибка при скачивании файла', 'error')
    }
  }

  const handleDeleteAttachment = async (attachmentId: number) => {
    const token = localStorage.getItem('token')
    if (!token || !selectedLead) return

    setConfirmModal({
      isOpen: true,
      title: 'Удаление файла',
      message: 'Вы уверены, что хотите удалить этот файл?',
      type: 'warning',
      onConfirm: () => performDeleteAttachment(attachmentId, token)
    })
  }

  const performDeleteAttachment = async (attachmentId: number, token: string) => {

    try {
      const response = await fetch(`${API_URL}/leads/attachments/${attachmentId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      if (response.ok) {
        // Обновить заявку чтобы убрать удаленный файл
        const refreshResponse = await fetch(`${API_URL}/leads/${selectedLead.id}`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (refreshResponse.ok) {
          const refreshedLead = await refreshResponse.json()
          setSelectedLead(refreshedLead)
        }
        loadLeads()
        showToast('Файл успешно удален!', 'success')
      } else {
        const errorText = await response.text()
        console.error('Delete failed:', response.status, errorText)
        if (response.status === 404) {
          showToast('Файл не найден или у вас нет прав на его удаление', 'error')
        } else {
          showToast('Ошибка при удалении файла: ' + errorText, 'error')
        }
      }
    } catch (error) {
      console.error('Error deleting file:', error)
      showToast('Ошибка при удалении файла', 'error')
    }
  }

  const createLead = async (formData: FormData) => {
    const token = localStorage.getItem('token')
    try {
      const leadData = {
        title: formData.get('company_name') || 'Новая заявка',
        source: formData.get('source'),
        client_name: formData.get('client_name'),
        client_contact: formData.get('client_contact'),
        company_name: formData.get('company_name'),
        description: formData.get('description')
      }

      const response = await fetch(`${API_URL}/leads/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(leadData)
      })
      
      if (response.ok) {
        setShowCreateForm(false)
        setSelectedSource('')
        setCustomSource('')
        setPhoneNumber('')
        loadLeads()
        loadStats()
      }
    } catch (error) {
      console.error('Error creating lead:', error)
    }
  }

  const groupedLeads = Object.keys(LEAD_STATUSES).reduce((acc, status) => {
    acc[status] = leads.filter(lead => 
      lead.status === status && 
      (searchQuery === '' || lead.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
       lead.client_name?.toLowerCase().includes(searchQuery.toLowerCase()))
    )
    return acc
  }, {} as Record<string, Lead[]>)

  if (loading) {
    return <div className="flex items-center justify-center h-64">Загрузка...</div>
  }

  return (
    <div className="p-2 lg:p-4 max-w-none mx-auto overflow-x-hidden">
      {/* Дашборд */}
      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 lg:gap-4 mb-4 lg:mb-6">
          <div className="bg-white p-3 lg:p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-blue-600">{stats.total_leads}</div>
            <div className="text-sm lg:text-xs text-gray-600">Всего заявок</div>
          </div>
          <div className="bg-white p-3 lg:p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-yellow-600">{stats.active_leads}</div>
            <div className="text-sm lg:text-xs text-gray-600">Активные</div>
          </div>
          <div className="bg-white p-3 lg:p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-green-600">{stats.conversion_rate}%</div>
            <div className="text-sm lg:text-xs text-gray-600">Конверсия</div>
          </div>
          <div className="bg-white p-3 lg:p-4 rounded-lg shadow">
            <div className="text-2xl font-bold text-purple-600">{formatDuration(stats.average_processing_time)}</div>
            <div className="text-sm lg:text-xs text-gray-600">Средняя длительность сделки</div>
          </div>
        </div>
      )}

      {/* Фильтры и поиск */}
      <div className="bg-white p-3 lg:p-4 rounded-lg shadow mb-4 lg:mb-6">
        <div className="flex flex-wrap gap-2 lg:gap-4 items-center mb-3 lg:mb-4">
          <input
            type="text"
            placeholder="Поиск по названию или клиенту..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 min-w-0 px-3 py-2 border rounded-lg"
          />

          <input
            type="text"
            placeholder="Фильтр по источнику"
            value={filterSource}
            onChange={(e) => setFilterSource(e.target.value)}
            className="px-3 py-2 border rounded-lg"
          />

          <button
            onClick={() => setShowCreateForm(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            + Новая заявка
          </button>
        </div>

        {/* Фильтры по дате */}
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2">
            <label className="text-sm lg:text-xs font-medium text-gray-700">Период создания:</label>
            <input
              type="date"
              value={filterDateFrom}
              onChange={(e) => setFilterDateFrom(e.target.value)}
              className="px-3 py-2 border rounded-lg text-sm lg:text-xs"
              placeholder="От"
            />
            <span className="text-gray-500">—</span>
            <input
              type="date"
              value={filterDateTo}
              onChange={(e) => setFilterDateTo(e.target.value)}
              className="px-3 py-2 border rounded-lg text-sm lg:text-xs"
              placeholder="До"
            />
            {(filterDateFrom || filterDateTo) && (
              <button
                onClick={() => {
                  setFilterDateFrom('')
                  setFilterDateTo('')
                }}
                className="text-red-600 hover:text-red-800 px-2 py-1 text-sm"
                title="Очистить фильтр по дате"
              >
                ✕
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Канбан-доска */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 2xl:grid-cols-7 gap-1 lg:gap-2 overflow-x-auto">
        {Object.entries(LEAD_STATUSES).map(([status, config]) => (
          <div
            key={status}
            className="bg-gray-50 rounded-lg p-1 lg:p-2"
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, status)}
          >
            <div className={`flex items-center justify-between mb-2 pb-1 border-b-2 ${config.color.replace('bg-', 'border-')}`}>
              <h2 className="text-xs font-semibold text-gray-800 truncate">{config.label}</h2>
              <span className="text-xs text-gray-500 bg-white px-1 py-0.5 rounded">
                {groupedLeads[status]?.length || 0}
              </span>
            </div>
            
            <div className="space-y-1 min-h-16">
              {groupedLeads[status]?.map(lead => {
                const isCompact = (groupedLeads[status]?.length || 0) > 4
                return (
                  <LeadCard 
                    key={lead.id} 
                    lead={lead} 
                    onUpdate={loadLeads}
                    onDragStart={handleDragStart}
                    onCardClick={setSelectedLead}
                    isCompact={isCompact}
                  />
                )
              })}
              {!groupedLeads[status]?.length && (
                <div className="text-xs text-gray-400 text-center py-4">
                  Перетащите заявку сюда
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Модальное окно создания заявки */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center" style={{ zIndex: 9999 }}>
          <div className="bg-white p-6 rounded-lg w-full max-w-lg">
            <h2 className="text-lg lg:text-base font-bold mb-4">Новая заявка</h2>
            <form onSubmit={(e) => {
              e.preventDefault()
              const formData = new FormData(e.target as HTMLFormElement)
              // Добавляем отформатированный номер телефона
              formData.set('client_contact', `+998 ${phoneNumber}`)
              // Добавляем источник в зависимости от выбора
              const sourceValue = selectedSource === 'other' ? customSource : selectedSource
              formData.set('source', sourceValue)
              createLead(formData)
            }}>
              <div className="space-y-4">
                <input
                  name="company_name"
                  placeholder="Название компании клиента"
                  className="w-full px-3 py-2 border rounded-lg"
                  required
                />
                <input
                  name="client_name"
                  placeholder="Имя клиента"
                  className="w-full px-3 py-2 border rounded-lg"
                  required
                />
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none bg-gray-100 border-r">
                    <span className="text-gray-500">+998</span>
                  </div>
                  <input
                    type="tel"
                    value={phoneNumber}
                    onChange={(e) => {
                      const value = e.target.value.replace(/\D/g, '').slice(0, 9)
                      const formatted = value.replace(/(\d{2})(\d{3})(\d{2})(\d{2})/, '$1 $2 $3 $4')
                      setPhoneNumber(formatted)
                    }}
                    placeholder="99 999 99 99"
                    className="w-full pl-16 pr-3 py-2 border rounded-lg"
                    required
                  />
                  <input
                    type="hidden"
                    name="client_contact"
                    value={`+998 ${phoneNumber}`}
                  />
                </div>
                
                <div>
                  <label className="block text-sm lg:text-xs font-medium text-gray-700 mb-2">
                    Источник заявки
                  </label>
                  <select
                    value={selectedSource}
                    onChange={(e) => setSelectedSource(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg"
                    required
                  >
                    <option value="">Выберите источник</option>
                    {LEAD_SOURCES.map(source => (
                      <option key={source.value} value={source.value}>
                        {source.label}
                      </option>
                    ))}
                  </select>
                  
                  {selectedSource === 'other' && (
                    <input
                      value={customSource}
                      onChange={(e) => setCustomSource(e.target.value)}
                      placeholder="Укажите источник"
                      className="w-full px-3 py-2 border rounded-lg mt-2"
                      required
                    />
                  )}
                </div>

                <textarea
                  name="description"
                  placeholder="Описание заявки (что клиент хочет)"
                  rows={3}
                  className="w-full px-3 py-2 border rounded-lg resize-none"
                  required
                />
              </div>
              
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateForm(false)
                    setPhoneNumber('')
                    setSelectedSource('')
                    setCustomSource('')
                  }}
                  className="px-4 py-2 text-gray-600 border rounded-lg hover:bg-gray-50"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Создать
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Детальное модальное окно заявки */}
      {selectedLead && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4" style={{ zIndex: 9999 }}>
          <div className="bg-white rounded-lg w-full max-w-[95vw] xl:max-w-6xl max-h-[95vh] overflow-hidden">
            <div className="p-6 border-b bg-gray-50">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h2 className="text-2xl font-bold text-gray-900">{selectedLead.title}</h2>
                  <p className="text-sm text-gray-600 mt-1">
                    Создана: {new Date(selectedLead.created_at).toLocaleString('ru')}
                  </p>
                </div>
                <div className="flex items-center space-x-2">
                  {!isEditingLead ? (
                    <>
                      <button
                        onClick={() => {
                          setIsEditingLead(true)
                          setEditLeadData({
                            company_name: selectedLead.company_name,
                            client_name: selectedLead.client_name,
                            client_contact: selectedLead.client_contact,
                            source: selectedLead.source,
                            description: selectedLead.description
                          })
                        }}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm lg:text-xs"
                      >
                        ✏️ Редактировать
                      </button>
                      <button
                        onClick={() => deleteLead(selectedLead.id)}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm lg:text-xs"
                      >
                        🗑️ Удалить заявку
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={async () => {
                          const token = localStorage.getItem('token')
                          try {
                            const response = await fetch(`${API_URL}/leads/${selectedLead.id}`, {
                              method: 'PUT',
                              headers: {
                                'Content-Type': 'application/json',
                                Authorization: `Bearer ${token}`
                              },
                              body: JSON.stringify(editLeadData)
                            })
                            
                            if (response.ok) {
                              const updatedLead = await response.json()
                              setSelectedLead(updatedLead)
                              setIsEditingLead(false)
                              loadLeads()
                            }
                          } catch (error) {
                            console.error('Error updating lead:', error)
                          }
                        }}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm lg:text-xs"
                      >
                        💾 Сохранить
                      </button>
                      <button
                        onClick={() => {
                          setIsEditingLead(false)
                          setEditLeadData({})
                        }}
                        className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors text-sm lg:text-xs"
                      >
                        ❌ Отмена
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => {
                      setSelectedLead(null)
                      setIsEditingLead(false)
                      setEditLeadData({})
                    }}
                    className="text-gray-400 hover:text-gray-600 text-2xl ml-4"
                  >
                    ×
                  </button>
                </div>
              </div>
            </div>
            
            <div className="flex flex-col lg:flex-row h-full max-h-[calc(95vh-140px)]">
              {/* Основная информация */}
              <div className="w-full lg:w-1/2 p-3 lg:p-6 lg:border-r overflow-y-auto">
                <h3 className="text-base lg:text-sm font-semibold mb-4">Информация о заявке</h3>
                
                <div className="space-y-4">
                  {!isEditingLead ? (
                    <>
                      <div>
                        <label className="text-sm lg:text-xs font-medium text-gray-700">Компания</label>
                        <p className="text-gray-900">{selectedLead.company_name || 'Не указана'}</p>
                      </div>
                      
                      <div>
                        <label className="text-sm lg:text-xs font-medium text-gray-700">Клиент</label>
                        <p className="text-gray-900">{selectedLead.client_name || 'Не указан'}</p>
                      </div>
                      
                      <div>
                        <label className="text-sm lg:text-xs font-medium text-gray-700">Контакты</label>
                        <p className="text-gray-900">{selectedLead.client_contact || 'Не указаны'}</p>
                      </div>
                      
                      <div>
                        <label className="text-sm lg:text-xs font-medium text-gray-700">Источник</label>
                        <p className="text-gray-900">{selectedLead.source}</p>
                      </div>
                    </>
                  ) : (
                    <>
                      <div>
                        <label className="text-sm lg:text-xs font-medium text-gray-700">Компания</label>
                        <input
                          type="text"
                          value={editLeadData.company_name || ''}
                          onChange={(e) => setEditLeadData({...editLeadData, company_name: e.target.value})}
                          className="w-full px-3 py-2 border rounded-lg"
                        />
                      </div>
                      
                      <div>
                        <label className="text-sm lg:text-xs font-medium text-gray-700">Клиент</label>
                        <input
                          type="text"
                          value={editLeadData.client_name || ''}
                          onChange={(e) => setEditLeadData({...editLeadData, client_name: e.target.value})}
                          className="w-full px-3 py-2 border rounded-lg"
                        />
                      </div>
                      
                      <div>
                        <label className="text-sm lg:text-xs font-medium text-gray-700">Контакты</label>
                        <input
                          type="text"
                          value={editLeadData.client_contact || ''}
                          onChange={(e) => setEditLeadData({...editLeadData, client_contact: e.target.value})}
                          className="w-full px-3 py-2 border rounded-lg"
                        />
                      </div>
                      
                      <div>
                        <label className="text-sm lg:text-xs font-medium text-gray-700">Источник</label>
                        <select
                          value={editLeadData.source || ''}
                          onChange={(e) => setEditLeadData({...editLeadData, source: e.target.value})}
                          className="w-full px-3 py-2 border rounded-lg"
                        >
                          {LEAD_SOURCES.map(source => (
                            <option key={source.value} value={source.value}>
                              {source.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </>
                  )}
                  
                  <div>
                    <label className="text-sm lg:text-xs font-medium text-gray-700">Статус</label>
                    <select
                      value={selectedLead.status}
                      onChange={(e) => {
                        const token = localStorage.getItem('token')
                        fetch(`${API_URL}/leads/${selectedLead.id}`, {
                          method: 'PUT',
                          headers: {
                            'Content-Type': 'application/json',
                            Authorization: `Bearer ${token}`
                          },
                          body: JSON.stringify({ status: e.target.value })
                        }).then(() => {
                          loadLeads()
                          setSelectedLead({...selectedLead, status: e.target.value})
                        })
                      }}
                      className="mt-1 px-3 py-2 border rounded-lg"
                    >
                      {Object.entries(LEAD_STATUSES).map(([status, config]) => (
                        <option key={status} value={status}>{config.label}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="text-sm lg:text-xs font-medium text-gray-700">Описание</label>
                    {!isEditingLead ? (
                      <p className="text-gray-900 whitespace-pre-wrap">{selectedLead.description || 'Нет описания'}</p>
                    ) : (
                      <textarea
                        value={editLeadData.description || ''}
                        onChange={(e) => setEditLeadData({...editLeadData, description: e.target.value})}
                        rows={3}
                        className="w-full px-3 py-2 border rounded-lg resize-none"
                      />
                    )}
                  </div>
                  
                  {selectedLead.manager && (
                    <div>
                      <label className="text-sm lg:text-xs font-medium text-gray-700">Оформил заявку</label>
                      <p className="text-gray-900">{selectedLead.manager.name}</p>
                    </div>
                  )}
                  
                  
                  {selectedLead.proposal_amount && (
                    <div>
                      <label className="text-sm lg:text-xs font-medium text-gray-700">Сумма КП</label>
                      <p className="text-gray-900">{selectedLead.proposal_amount.toLocaleString()} ₽</p>
                    </div>
                  )}
                  
                  {selectedLead.deal_amount && (
                    <div>
                      <label className="text-sm lg:text-xs font-medium text-gray-700">Сумма сделки</label>
                      <p className="text-gray-900 text-green-600 font-semibold">{selectedLead.deal_amount.toLocaleString()} ₽</p>
                    </div>
                  )}
                </div>
              </div>
              
              {/* История */}
              <div className="w-full lg:w-1/2 p-3 lg:p-6 flex flex-col">
                <h3 className="text-base lg:text-sm font-semibold mb-4">История заявки</h3>
                
                <div className="flex-1 overflow-y-auto space-y-3">
                  {/* Создание заявки */}
                  <div className="bg-blue-50 p-3 rounded-lg border-l-4 border-blue-400">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-medium text-sm lg:text-xs text-blue-700">🆕 Заявка создана</span>
                      <span className="text-xs lg:text-xs text-gray-500">
                        {new Date(selectedLead.created_at).toLocaleString('ru')}
                      </span>
                    </div>
                    <p className="text-gray-700 text-sm lg:text-xs">
                      Заявка "{selectedLead.company_name || selectedLead.title}" создана
                    </p>
                  </div>

                  {/* Структурированная история по этапам */}
                  {(() => {
                    // Вспомогательные функции
                    const getStatusLabel = (status: string) => {
                      const cleanStatus = status.replace('LeadStatusEnum.', '')
                      switch (cleanStatus) {
                        case 'new': return 'Новая заявка'
                        case 'in_progress': return 'Взят в обработку'
                        case 'negotiation': return 'Созвон / переговоры'
                        case 'proposal': return 'К.П.'
                        case 'waiting': return 'Ожидание ответа'
                        case 'success': return 'Успешно'
                        case 'rejected': return 'Отказ'
                        default: return status
                      }
                    }

                    const getStatusColor = (status: string) => {
                      const cleanStatus = status.replace('LeadStatusEnum.', '')
                      switch (cleanStatus) {
                        case 'new': return 'border-blue-500 bg-blue-50 text-blue-800'
                        case 'in_progress': return 'border-yellow-500 bg-yellow-50 text-yellow-800'
                        case 'negotiation': return 'border-orange-500 bg-orange-50 text-orange-800'
                        case 'proposal': return 'border-purple-500 bg-purple-50 text-purple-800'
                        case 'waiting': return 'border-indigo-500 bg-indigo-50 text-indigo-800'
                        case 'success': return 'border-green-500 bg-green-50 text-green-800'
                        case 'rejected': return 'border-red-500 bg-red-50 text-red-800'
                        default: return 'border-gray-500 bg-gray-50 text-gray-800'
                      }
                    }

                    const getStatusIcon = (status: string) => {
                      const cleanStatus = status.replace('LeadStatusEnum.', '')
                      switch (cleanStatus) {
                        case 'new': return '🆕'
                        case 'in_progress': return '⚡'
                        case 'negotiation': return '📞'
                        case 'proposal': return '💰'
                        case 'waiting': return '⏳'
                        case 'success': return '✅'
                        case 'rejected': return '❌'
                        default: return '📋'
                      }
                    }

                    // Собираем все изменения статусов
                    const statusChanges = selectedLead.history
                      .filter(item => item.action === 'status_changed')
                      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())

                    // Определяем все этапы через которые прошла заявка
                    const stages = ['new'] // Начинаем с "new"
                    statusChanges.forEach(change => {
                      if (change.new_value && !stages.includes(change.new_value)) {
                        stages.push(change.new_value)
                      }
                    })

                    // Группируем комментарии по этапам
                    const commentsByStage: Record<string, typeof selectedLead.notes> = {}
                    selectedLead.notes.forEach(note => {
                      const stage = note.lead_status || 'new'
                      if (!commentsByStage[stage]) commentsByStage[stage] = []
                      commentsByStage[stage].push(note)
                    })


                    return (
                      <>
                        {/* Этапы как заголовки секций */}
                        {stages.map((stage, index) => {
                          const stageComments = (commentsByStage[stage] || [])
                            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                          
                          const stageChange = statusChanges.find(change => change.new_value === stage)
                          const stageStartDate = stage === 'new' 
                            ? selectedLead.created_at 
                            : stageChange?.created_at

                          // Показываем этап только если есть комментарии или это не первый этап
                          if (stageComments.length === 0 && stage === 'new') return null

                          return (
                            <div key={stage} className="mb-4">
                              {/* Заголовок этапа */}
                              <div className={`p-3 rounded-lg border-l-4 ${getStatusColor(stage)} mb-3`}>
                                <div className="flex justify-between items-center">
                                  <h4 className="font-semibold text-sm lg:text-xs">
                                    {getStatusIcon(stage)} {getStatusLabel(stage)}
                                  </h4>
                                  {stageStartDate && (
                                    <span className="text-xs opacity-70">
                                      {new Date(stageStartDate).toLocaleString('ru')}
                                    </span>
                                  )}
                                </div>
                                {stageChange && (
                                  <p className="text-xs lg:text-xs mt-1 opacity-80">
                                    Переход выполнен: {stageChange.user?.name}
                                  </p>
                                )}
                              </div>

                              {/* Комментарии внутри этапа */}
                              {stageComments.map(comment => (
                                <div key={comment.id} className="ml-6 mb-2 p-2 bg-gray-50 rounded border-l-2 border-gray-300">
                                  <div className="flex justify-between items-start mb-1">
                                    <span className="font-medium text-xs lg:text-xs text-gray-700">
                                      💬 {comment.user?.name || 'Неизвестный пользователь'}
                                    </span>
                                    <span className="text-xs lg:text-xs text-gray-500">
                                      {new Date(comment.created_at).toLocaleString('ru')}
                                    </span>
                                  </div>
                                  <p className="text-sm text-gray-800">{comment.content}</p>
                                </div>
                              ))}

                              {/* Сообщение если нет комментариев в этапе */}
                              {stageComments.length === 0 && stage !== 'new' && (
                                <div className="ml-6 text-xs text-gray-500 italic mb-2">
                                  Комментариев на этом этапе нет
                                </div>
                              )}
                            </div>
                          )
                        })}


                        {/* Сообщение если история пуста */}
                        {stages.length <= 1 && selectedLead.notes.length === 0 && (
                          <div className="text-center text-gray-500 py-8">
                            История пуста
                          </div>
                        )}
                      </>
                    )
                  })()}
                </div>

                {/* Прикрепленные файлы */}
                {selectedLead.attachments && selectedLead.attachments.length > 0 && (
                  <div className="border-t pt-4 mt-4">
                    <h4 className="text-sm font-semibold text-gray-700 mb-3">Прикрепленные файлы</h4>
                    <div className="space-y-2">
                      {selectedLead.attachments.map((attachment, index) => (
                        <div key={attachment.id || index} className="flex items-center justify-between p-2 bg-gray-50 rounded border">
                          <div className="flex items-center gap-2">
                            <span className="text-green-600">📎</span>
                            <span className="text-sm font-medium">{attachment.filename}</span>
                            <span className="text-xs lg:text-xs text-gray-500">
                              {new Date(attachment.uploaded_at).toLocaleString('ru')}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleDownloadAttachment(attachment.id, attachment.filename)}
                              className="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 transition-colors"
                            >
                              📥 Скачать
                            </button>
                            <button
                              onClick={() => handleDeleteAttachment(attachment.id)}
                              className="px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700 transition-colors"
                              title="Удалить файл"
                            >
                              🗑️ Удалить
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Форма добавления комментария */}
                <div className="border-t pt-4 mt-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">Добавить комментарий</h4>
                  <textarea
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Оставьте комментарий к заявке..."
                    rows={3}
                    className="w-full px-3 py-2 border rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />

                  {/* Загрузка файлов */}
                  <div className="mt-3 border-t pt-3">
                    <div className="flex items-center gap-2 mb-2">
                      <label className="text-sm font-medium text-gray-700">Прикрепить файл:</label>
                      <input
                        type="file"
                        onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                        className="text-sm text-gray-500 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-sm file:bg-gray-100 file:text-gray-700 hover:file:bg-gray-200"
                      />
                      {selectedFile && (
                        <button
                          onClick={() => uploadFile(selectedLead.id, selectedFile)}
                          className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition-colors"
                        >
                          📎 Загрузить
                        </button>
                      )}
                    </div>
                    {selectedFile && (
                      <p className="text-xs text-gray-600">
                        Выбран файл: {selectedFile.name} ({Math.round(selectedFile.size / 1024)} КБ)
                      </p>
                    )}
                  </div>

                  <div className="flex justify-between items-center mt-2">
                    <span className="text-xs lg:text-xs text-gray-500">
                      Комментарий будет добавлен к текущему этапу: "{LEAD_STATUSES[selectedLead.status]?.label || selectedLead.status}"
                    </span>
                    <button
                      onClick={() => addComment(selectedLead.id)}
                      disabled={!newComment.trim()}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm lg:text-xs"
                    >
                      💬 Добавить комментарий
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        onClose={() => setConfirmModal(prev => ({ ...prev, isOpen: false }))}
        onConfirm={confirmModal.onConfirm}
        title={confirmModal.title}
        message={confirmModal.message}
        type={confirmModal.type}
      />
    </div>
  )
}

export default LeadBoard