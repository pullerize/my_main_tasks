import { useState, useEffect } from 'react'
import { API_URL } from '../api'
import {
  Link2,
  FileText,
  BookOpen,
  Plus,
  Edit3,
  Trash2,
  Download,
  ExternalLink,
  Search,
  Filter,
  Star,
  Clock,
  User
} from 'lucide-react'

interface Link {
  id: number
  title: string
  url: string
  description?: string
  category: string
  isFavorite: boolean
  addedBy: string
  createdAt: string
}

interface File {
  id: number
  name: string
  filename: string
  size: number
  category: string
  uploadedBy: string
  uploadedAt: string
  downloadCount: number
  isFavorite: boolean
  fileData?: string // base64 данные файла
  mimeType?: string // MIME тип файла
}

interface Note {
  id: number
  title: string
  content: string
  category: string
  isPinned: boolean
  author: string
  createdAt: string
  updatedAt: string
}

function Resources() {
  const [activeTab, setActiveTab] = useState('links')
  const [links, setLinks] = useState<Link[]>([])
  const [files, setFiles] = useState<File[]>([])
  const [notes, setNotes] = useState<Note[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory] = useState('all')
  const [showAddForm, setShowAddForm] = useState(false)
  const [showEditForm, setShowEditForm] = useState(false)
  const [showEditFileForm, setShowEditFileForm] = useState(false)
  const [showEditNoteForm, setShowEditNoteForm] = useState(false)
  const [showViewNoteModal, setShowViewNoteModal] = useState(false)
  const [editingItem, setEditingItem] = useState<Link | null>(null)
  const [editingFile, setEditingFile] = useState<File | null>(null)
  const [editingNote, setEditingNote] = useState<Note | null>(null)
  const [viewingNote, setViewingNote] = useState<Note | null>(null)
  const [loading, setLoading] = useState(false)

  // Список пользователей команды
  const teamMembers = [
    { id: 1, name: 'Сергей', role: 'Digital' },
    { id: 2, name: 'Сабина', role: 'Head_of_SMM' },
    { id: 3, name: 'Анна', role: 'Designer' },
    { id: 4, name: 'Максим', role: 'Content_Manager' },
    { id: 5, name: 'Елена', role: 'Marketing_Manager' },
    { id: 6, name: 'Денис', role: 'Project_Manager' },
    { id: 7, name: 'Иван', role: 'Developer' },
    { id: 8, name: 'Мария', role: 'Copywriter' }
  ]

  // Функции для работы с localStorage
  const saveLinksToStorage = (linksToSave: Link[]) => {
    try {
      localStorage.setItem('resources_links', JSON.stringify(linksToSave))
      console.log('Ссылки сохранены в localStorage:', linksToSave.length)
    } catch (error) {
      console.error('Ошибка сохранения ссылок в localStorage:', error)
    }
  }

  const loadLinksFromStorage = (): Link[] => {
    try {
      const savedLinks = localStorage.getItem('resources_links')
      if (savedLinks) {
        const parsedLinks = JSON.parse(savedLinks)
        console.log('Загружены ссылки из localStorage:', parsedLinks.length)
        return parsedLinks
      }
      return []
    } catch (error) {
      console.error('Ошибка загрузки ссылок из localStorage:', error)
      return []
    }
  }

  // Функции для файлов и заметок
  const saveFilesToStorage = (filesToSave: File[]) => {
    try {
      localStorage.setItem('resources_files', JSON.stringify(filesToSave))
      console.log('Файлы сохранены в localStorage:', filesToSave.length)
    } catch (error) {
      console.error('Ошибка сохранения файлов в localStorage:', error)
    }
  }

  const loadFilesFromStorage = (): File[] => {
    try {
      const savedFiles = localStorage.getItem('resources_files')
      if (savedFiles) {
        const parsedFiles = JSON.parse(savedFiles)
        console.log('Загружены файлы из localStorage:', parsedFiles.length)
        return parsedFiles
      }
      return []
    } catch (error) {
      console.error('Ошибка загрузки файлов из localStorage:', error)
      return []
    }
  }

  const saveNotesToStorage = (notesToSave: Note[]) => {
    try {
      localStorage.setItem('resources_notes', JSON.stringify(notesToSave))
      console.log('Заметки сохранены в localStorage:', notesToSave.length)
    } catch (error) {
      console.error('Ошибка сохранения заметок в localStorage:', error)
    }
  }

  const loadNotesFromStorage = (): Note[] => {
    try {
      const savedNotes = localStorage.getItem('resources_notes')
      if (savedNotes) {
        const parsedNotes = JSON.parse(savedNotes)
        console.log('Загружены заметки из localStorage:', parsedNotes.length)
        return parsedNotes
      }
      return []
    } catch (error) {
      console.error('Ошибка загрузки заметок из localStorage:', error)
      return []
    }
  }

  // Заглушечные данные для демонстрации
  const mockLinks: Link[] = [
    {
      id: 1,
      title: "Figma - дизайн инструменты",
      url: "https://figma.com",
      description: "Основной инструмент для дизайна и прототипирования",
      category: "design",
      isFavorite: false,
      addedBy: "Анна Designer",
      createdAt: "2024-01-15"
    },
    {
      id: 2,
      title: "Unsplash - бесплатные фото",
      url: "https://unsplash.com",
      description: "Коллекция качественных стоковых фотографий",
      category: "resources",
      isFavorite: false,
      addedBy: "Максим Content_Manager",
      createdAt: "2024-01-20"
    },
    {
      id: 3,
      title: "Google Analytics",
      url: "https://analytics.google.com",
      description: "Аналитика веб-сайтов и приложений",
      category: "analytics",
      isFavorite: false,
      addedBy: "Елена Marketing_Manager",
      createdAt: "2024-02-01"
    }
  ]

  const mockFiles: File[] = [
    {
      id: 1,
      name: "Брендбук компании 2024",
      filename: "brandbook_2024.pdf",
      size: 2048000,
      category: "branding",
      uploadedBy: "Анна Designer",
      uploadedAt: "2024-01-10",
      downloadCount: 15,
      isFavorite: false
    },
    {
      id: 2,
      name: "Шаблон презентации",
      filename: "template_presentation.pptx",
      size: 512000,
      category: "templates",
      uploadedBy: "Максим Content_Manager",
      uploadedAt: "2024-01-25",
      downloadCount: 8,
      isFavorite: false
    }
  ]

  const mockNotes: Note[] = [
    {
      id: 1,
      title: "Чек-лист публикации в соцсетях",
      content: "1. Проверить качество изображений\n2. Добавить хештеги\n3. Настроить время публикации\n4. Проверить ссылки\n5. Добавить призыв к действию",
      category: "social-media",
      isPinned: true,
      author: "Елена Marketing_Manager",
      createdAt: "2024-01-15",
      updatedAt: "2024-02-10"
    },
    {
      id: 2,
      title: "Контакты поставщиков",
      content: "Полиграфия: ООО \"Принт Про\" - +7 (999) 123-45-67\nФотограф: Иван Петров - +7 (999) 987-65-43\nВидеограф: Студия \"Кадр\" - +7 (999) 555-33-22",
      category: "contacts",
      isPinned: false,
      author: "Денис Project_Manager",
      createdAt: "2024-01-20",
      updatedAt: "2024-01-20"
    }
  ]

  useEffect(() => {
    // Загружаем данные из localStorage или используем заглушки
    const savedLinks = loadLinksFromStorage()
    if (savedLinks.length > 0) {
      setLinks(savedLinks)
    } else {
      // Если в localStorage нет данных, загружаем заглушки
      console.log('Инициализация: загружаем заглушечные данные')
      setLinks(mockLinks)
      saveLinksToStorage(mockLinks) // И сразу сохраняем их
    }
    
    // Загружаем файлы из localStorage или используем заглушки
    const savedFiles = loadFilesFromStorage()
    if (savedFiles.length > 0) {
      setFiles(savedFiles)
    } else {
      console.log('Инициализация: загружаем заглушечные файлы')
      setFiles(mockFiles)
      saveFilesToStorage(mockFiles)
    }

    // Загружаем заметки из localStorage или используем заглушки
    const savedNotes = loadNotesFromStorage()
    if (savedNotes.length > 0) {
      setNotes(savedNotes)
    } else {
      console.log('Инициализация: загружаем заглушечные заметки')
      setNotes(mockNotes)
      saveNotesToStorage(mockNotes)
    }
  }, [])

  const categories = {
    links: [
      { value: 'all', label: 'Все' },
      { value: 'design', label: 'Дизайн' },
      { value: 'resources', label: 'Ресурсы' },
      { value: 'analytics', label: 'Аналитика' },
      { value: 'tools', label: 'Инструменты' }
    ],
    files: [
      { value: 'all', label: 'Все' },
      { value: 'branding', label: 'Брендинг' },
      { value: 'templates', label: 'Шаблоны' },
      { value: 'documents', label: 'Документы' },
      { value: 'media', label: 'Медиа' }
    ],
    notes: [
      { value: 'all', label: 'Все' },
      { value: 'social-media', label: 'Соцсети' },
      { value: 'contacts', label: 'Контакты' },
      { value: 'processes', label: 'Процессы' },
      { value: 'ideas', label: 'Идеи' }
    ]
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU')
  }

  const handleEditLink = (link: Link) => {
    setEditingItem(link)
    setShowEditForm(true)
  }

  const handleDeleteLink = (linkId: number) => {
    if (window.confirm('Вы уверены, что хотите удалить эту ссылку?')) {
      const newLinks = links.filter(link => link.id !== linkId)
      setLinks(newLinks)
      saveLinksToStorage(newLinks) // Сохраняем в localStorage
    }
  }

  const handleSaveEdit = (updatedLink: Link) => {
    const updatedLinks = links.map(link => 
      link.id === updatedLink.id ? updatedLink : link
    )
    setLinks(updatedLinks)
    saveLinksToStorage(updatedLinks) // Сохраняем в localStorage
    setShowEditForm(false)
    setEditingItem(null)
  }

  const handleToggleFavorite = (linkId: number) => {
    const updatedLinks = links.map(link => 
      link.id === linkId ? { ...link, isFavorite: !link.isFavorite } : link
    )
    setLinks(updatedLinks)
    saveLinksToStorage(updatedLinks) // Сохраняем в localStorage
  }

  // Функции для управления файлами
  const handleEditFile = (file: File) => {
    setEditingFile(file)
    setShowEditFileForm(true)
  }

  const handleDeleteFile = (fileId: number) => {
    if (window.confirm('Вы уверены, что хотите удалить этот файл?')) {
      const newFiles = files.filter(file => file.id !== fileId)
      setFiles(newFiles)
      saveFilesToStorage(newFiles)
    }
  }

  const handleSaveEditFile = (updatedFile: File) => {
    const updatedFiles = files.map(file => 
      file.id === updatedFile.id ? updatedFile : file
    )
    setFiles(updatedFiles)
    saveFilesToStorage(updatedFiles)
    setShowEditFileForm(false)
    setEditingFile(null)
  }

  const handleToggleFileFavorite = (fileId: number) => {
    const updatedFiles = files.map(file => 
      file.id === fileId ? { ...file, isFavorite: !file.isFavorite } : file
    )
    setFiles(updatedFiles)
    saveFilesToStorage(updatedFiles)
  }

  // Функции для управления заметками
  const handleEditNote = (note: Note) => {
    setEditingNote(note)
    setShowEditNoteForm(true)
  }

  const handleDeleteNote = (noteId: number) => {
    if (window.confirm('Вы уверены, что хотите удалить эту заметку?')) {
      const newNotes = notes.filter(note => note.id !== noteId)
      setNotes(newNotes)
      saveNotesToStorage(newNotes)
    }
  }

  const handleSaveEditNote = (updatedNote: Note) => {
    const updatedNotes = notes.map(note => 
      note.id === updatedNote.id ? updatedNote : note
    )
    setNotes(updatedNotes)
    saveNotesToStorage(updatedNotes)
    setShowEditNoteForm(false)
    setEditingNote(null)
  }

  const handleToggleNotePinned = (noteId: number) => {
    const updatedNotes = notes.map(note => 
      note.id === noteId ? { ...note, isPinned: !note.isPinned } : note
    )
    setNotes(updatedNotes)
    saveNotesToStorage(updatedNotes)
  }

  // Функция для определения MIME-типа по расширению файла
  const getMimeType = (filename: string): string => {
    const extension = filename.split('.').pop()?.toLowerCase()
    
    const mimeTypes: { [key: string]: string } = {
      // Документы
      'pdf': 'application/pdf',
      'doc': 'application/msword',
      'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'xls': 'application/vnd.ms-excel',
      'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'ppt': 'application/vnd.ms-powerpoint',
      'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'txt': 'text/plain',
      'rtf': 'application/rtf',
      
      // Изображения
      'jpg': 'image/jpeg',
      'jpeg': 'image/jpeg',
      'png': 'image/png',
      'gif': 'image/gif',
      'bmp': 'image/bmp',
      'svg': 'image/svg+xml',
      'webp': 'image/webp',
      
      // Аудио
      'mp3': 'audio/mpeg',
      'wav': 'audio/wav',
      'ogg': 'audio/ogg',
      'aac': 'audio/aac',
      
      // Видео
      'mp4': 'video/mp4',
      'avi': 'video/x-msvideo',
      'mov': 'video/quicktime',
      'wmv': 'video/x-ms-wmv',
      
      // Архивы
      'zip': 'application/zip',
      'rar': 'application/vnd.rar',
      '7z': 'application/x-7z-compressed',
      
      // Другие
      'json': 'application/json',
      'xml': 'application/xml',
      'csv': 'text/csv'
    }

    return mimeTypes[extension || ''] || 'application/octet-stream'
  }

  // Функция для скачивания файла
  const handleDownloadFile = (file: File) => {
    // Увеличиваем счетчик скачиваний
    const updatedFiles = files.map(f => 
      f.id === file.id ? { ...f, downloadCount: f.downloadCount + 1 } : f
    )
    setFiles(updatedFiles)
    saveFilesToStorage(updatedFiles)

    let dataUrl: string

    if (file.fileData && file.mimeType) {
      // Если у нас есть сохраненные данные файла, используем их
      dataUrl = `data:${file.mimeType};base64,${file.fileData}`
    } else {
      // Fallback для старых файлов без данных - создаем демонстрационный контент
      const mimeType = getMimeType(file.filename)
      
      if (mimeType.startsWith('text/') || mimeType === 'text/csv') {
        const fileContent = `Файл: ${file.name}\nРазмер: ${formatFileSize(file.size)}\nЗагружен: ${file.uploadedBy}\nКатегория: ${file.category}\n\nЭто демонстрационный файл из системы управления ресурсами.\n\nСодержимое файла:\nЗдесь могли бы быть ваши данные...`
        dataUrl = `data:${mimeType};charset=utf-8,${encodeURIComponent(fileContent)}`
      } else if (mimeType === 'application/json') {
        const jsonContent = {
          name: file.name,
          filename: file.filename,
          size: file.size,
          category: file.category,
          uploadedBy: file.uploadedBy,
          uploadedAt: file.uploadedAt,
          downloadCount: file.downloadCount,
          isFavorite: file.isFavorite,
          note: "Это демонстрационный файл из системы управления ресурсами"
        }
        const fileContent = JSON.stringify(jsonContent, null, 2)
        dataUrl = `data:${mimeType};charset=utf-8,${encodeURIComponent(fileContent)}`
      } else {
        // Для бинарных файлов без данных создаем информационный файл
        const fileContent = `ДЕМОНСТРАЦИОННЫЙ ФАЙЛ\n\nОригинальное название: ${file.filename}\nОтображаемое название: ${file.name}\nРазмер: ${formatFileSize(file.size)}\nЗагружен: ${file.uploadedBy}\nКатегория: ${file.category}\n\nЭтот файл был создан как демонстрационный.\nДля получения реального файла загрузите его через форму добавления файла.`
        dataUrl = `data:text/plain;charset=utf-8,${encodeURIComponent(fileContent)}`
      }
    }

    // Создаем и запускаем скачивание
    const link = document.createElement('a')
    link.href = dataUrl
    link.download = file.filename
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    console.log(`Скачивание файла: ${file.filename}`)
  }

  // Функция для просмотра заметки
  const handleViewNote = (note: Note) => {
    setViewingNote(note)
    setShowViewNoteModal(true)
  }

  const filteredData = () => {
    let data = activeTab === 'links' ? links : activeTab === 'files' ? files : notes
    
    if (selectedCategory !== 'all') {
      data = data.filter(item => item.category === selectedCategory)
    }
    
    if (searchQuery) {
      data = data.filter(item => 
        item.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item as any).description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item as any).content?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }
    
    // Сортируем: избранные наверху для ссылок и файлов, закрепленные наверху для заметок
    if (activeTab === 'links' || activeTab === 'files') {
      data = data.sort((a: any, b: any) => {
        if (a.isFavorite && !b.isFavorite) return -1
        if (!a.isFavorite && b.isFavorite) return 1
        return 0
      })
    } else if (activeTab === 'notes') {
      data = data.sort((a: any, b: any) => {
        if (a.isPinned && !b.isPinned) return -1
        if (!a.isPinned && b.isPinned) return 1
        return 0
      })
    }
    
    return data
  }

  const AddResourceForm = () => {
    const [title, setTitle] = useState('')
    const [url, setUrl] = useState('')
    const [description, setDescription] = useState('')
    const category = 'general'
    const [selectedFile, setSelectedFile] = useState<globalThis.File | null>(null)

    const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault()
      
      if (activeTab === 'links' && title && url) {
        const newLink: Link = {
          id: Math.max(...links.map(l => l.id), 0) + 1,
          title,
          url,
          description,
          category,
          isFavorite: false,
          addedBy: 'Команда',
          createdAt: new Date().toISOString().split('T')[0]
        }
        const updatedLinks = [...links, newLink]
        setLinks(updatedLinks)
        saveLinksToStorage(updatedLinks) // Сохраняем в localStorage
        setShowAddForm(false)
        // Очищаем форму
        setTitle('')
        setUrl('')
        setDescription('')
      } else if (activeTab === 'files' && (title || selectedFile)) {
        if (selectedFile) {
          // Загружаем реальный файл
          const reader = new FileReader()
          reader.onload = (e) => {
            const result = e.target?.result as string
            const base64Data = result.split(',')[1] // Убираем префикс data:...;base64,
            
            const displayName = title || selectedFile.name.split('.')[0]
            
            const newFile: File = {
              id: Math.max(...files.map(f => f.id), 0) + 1,
              name: displayName,
              filename: selectedFile.name,
              size: selectedFile.size,
              category,
              uploadedBy: 'Команда',
              uploadedAt: new Date().toISOString().split('T')[0],
              downloadCount: 0,
              isFavorite: false,
              fileData: base64Data,
              mimeType: selectedFile.type || getMimeType(selectedFile.name)
            }
            
            const updatedFiles = [...files, newFile]
            setFiles(updatedFiles)
            saveFilesToStorage(updatedFiles)
            setShowAddForm(false)
            // Очищаем форму
            setTitle('')
            setDescription('')
            setSelectedFile(null)
          }
          reader.readAsDataURL(selectedFile)
        } else {
          // Создаем демонстрационный файл без реального содержимого
          const fileName = title.toLowerCase().replace(/\s+/g, '_') + '.txt'
          const fileSize = Math.floor(Math.random() * 5000000) + 100000
          
          const newFile: File = {
            id: Math.max(...files.map(f => f.id), 0) + 1,
            name: title,
            filename: fileName,
            size: fileSize,
            category,
            uploadedBy: 'Команда',
            uploadedAt: new Date().toISOString().split('T')[0],
            downloadCount: 0,
            isFavorite: false
          }
          const updatedFiles = [...files, newFile]
          setFiles(updatedFiles)
          saveFilesToStorage(updatedFiles)
          setShowAddForm(false)
          // Очищаем форму
          setTitle('')
          setDescription('')
          setSelectedFile(null)
        }
      } else if (activeTab === 'notes' && title && description) {
        const newNote: Note = {
          id: Math.max(...notes.map(n => n.id), 0) + 1,
          title,
          content: description,
          category,
          isPinned: false,
          author: 'Команда',
          createdAt: new Date().toISOString().split('T')[0],
          updatedAt: new Date().toISOString().split('T')[0]
        }
        const updatedNotes = [...notes, newNote]
        setNotes(updatedNotes)
        saveNotesToStorage(updatedNotes)
        setShowAddForm(false)
        // Очищаем форму
        setTitle('')
        setDescription('')
      }
    }

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowAddForm(false)}>
        <div className="bg-white rounded-lg p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
          <h3 className="text-lg font-semibold mb-4">
            Добавить {activeTab === 'links' ? 'ссылку' : activeTab === 'files' ? 'файл' : 'заметку'}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="text"
              placeholder="Название"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg"
              required
            />
            {activeTab === 'links' && (
              <>
                <input
                  type="url"
                  placeholder="URL"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="w-full p-2 border border-gray-300 rounded-lg"
                  required
                />
                <textarea
                  placeholder="Описание (необязательно)"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  className="w-full p-2 border border-gray-300 rounded-lg"
                />
              </>
            )}
            {activeTab === 'files' && (
              <input
                type="file"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  setSelectedFile(file || null)
                  if (file && !title) {
                    setTitle(file.name.split('.')[0])
                  }
                }}
                className="w-full p-2 border border-gray-300 rounded-lg"
              />
            )}
            {activeTab === 'notes' && (
              <textarea
                placeholder="Содержание"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                className="w-full p-2 border border-gray-300 rounded-lg"
                required
              />
            )}
            <div className="flex gap-2">
              <button
                type="submit"
                className="flex-1 bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600"
              >
                Сохранить
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="flex-1 bg-gray-300 text-gray-700 py-2 rounded-lg hover:bg-gray-400"
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      </div>
    )
  }

  const EditLinkForm = () => {
    const [title, setTitle] = useState(editingItem?.title || '')
    const [url, setUrl] = useState(editingItem?.url || '')
    const [description, setDescription] = useState(editingItem?.description || '')
    const category = editingItem?.category || 'general'

    const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault()
      if (editingItem) {
        handleSaveEdit({
          ...editingItem,
          title,
          url,
          description,
          category
        })
      }
    }

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => { setShowEditForm(false); setEditingItem(null); }}>
        <div className="bg-white rounded-lg p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
          <h3 className="text-lg font-semibold mb-4">Редактировать ссылку</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="text"
              placeholder="Название"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg"
              required
            />
            <input
              type="url"
              placeholder="URL"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg"
              required
            />
            <textarea
              placeholder="Описание (необязательно)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full p-2 border border-gray-300 rounded-lg"
            />
            <div className="flex gap-2">
              <button
                type="submit"
                className="flex-1 bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600"
              >
                Сохранить
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowEditForm(false)
                  setEditingItem(null)
                }}
                className="flex-1 bg-gray-300 text-gray-700 py-2 rounded-lg hover:bg-gray-400"
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      </div>
    )
  }

  const EditFileForm = () => {
    const [name, setName] = useState(editingFile?.name || '')
    const category = editingFile?.category || 'general'

    const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault()
      if (editingFile) {
        // Сохраняем оригинальное расширение файла
        const originalExtension = editingFile.filename.split('.').pop()
        const newFilename = originalExtension 
          ? `${name.toLowerCase().replace(/\s+/g, '_')}.${originalExtension}`
          : editingFile.filename
          
        handleSaveEditFile({
          ...editingFile,
          name,
          category,
          filename: newFilename
        })
      }
    }

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => { setShowEditFileForm(false); setEditingFile(null); }}>
        <div className="bg-white rounded-lg p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
          <h3 className="text-lg font-semibold mb-4">Редактировать файл</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="text"
              placeholder="Название"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg"
              required
            />
            <div className="flex gap-2">
              <button
                type="submit"
                className="flex-1 bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600"
              >
                Сохранить
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowEditFileForm(false)
                  setEditingFile(null)
                }}
                className="flex-1 bg-gray-300 text-gray-700 py-2 rounded-lg hover:bg-gray-400"
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      </div>
    )
  }

  const EditNoteForm = () => {
    const [title, setTitle] = useState(editingNote?.title || '')
    const [content, setContent] = useState(editingNote?.content || '')
    const category = editingNote?.category || 'general'

    const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault()
      if (editingNote) {
        handleSaveEditNote({
          ...editingNote,
          title,
          content,
          category,
          updatedAt: new Date().toISOString().split('T')[0]
        })
      }
    }

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => { setShowEditNoteForm(false); setEditingNote(null); }}>
        <div className="bg-white rounded-lg p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
          <h3 className="text-lg font-semibold mb-4">Редактировать заметку</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="text"
              placeholder="Название"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-lg"
              required
            />
            <textarea
              placeholder="Содержание"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={4}
              className="w-full p-2 border border-gray-300 rounded-lg"
              required
            />
            <div className="flex gap-2">
              <button
                type="submit"
                className="flex-1 bg-blue-500 text-white py-2 rounded-lg hover:bg-blue-600"
              >
                Сохранить
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowEditNoteForm(false)
                  setEditingNote(null)
                }}
                className="flex-1 bg-gray-300 text-gray-700 py-2 rounded-lg hover:bg-gray-400"
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      </div>
    )
  }

  const ViewNoteModal = () => {
    if (!viewingNote) return null

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => { setShowViewNoteModal(false); setViewingNote(null); }}>
        <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] m-4" onClick={(e) => e.stopPropagation()}>
          {/* Заголовок модального окна */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <BookOpen className="w-6 h-6 text-purple-500" />
              <h2 className="text-xl font-bold text-gray-900">{viewingNote.title}</h2>
              {viewingNote.isPinned && (
                <Star className="w-5 h-5 text-yellow-500 fill-current" />
              )}
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => {
                  setShowViewNoteModal(false)
                  setViewingNote(null)
                  handleEditNote(viewingNote)
                }}
                className="p-2 rounded-lg hover:bg-blue-100 text-blue-500 hover:text-blue-600 transition-colors"
                title="Редактировать"
              >
                <Edit3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => { setShowViewNoteModal(false); setViewingNote(null); }}
                className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                title="Закрыть"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Содержимое заметки */}
          <div className="p-6 overflow-y-auto max-h-96">
            <div className="prose max-w-none">
              <div className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                {viewingNote.content}
              </div>
            </div>
          </div>

          {/* Метаинформация */}
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
            <div className="flex items-center justify-end text-sm text-gray-500">
              <div className="flex items-center space-x-4">
                <div className="text-xs">
                  Создано: {formatDate(viewingNote.createdAt)}
                </div>
                <div className="text-xs">
                  Изменено: {formatDate(viewingNote.updatedAt)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-7xl mx-auto bg-gray-50 min-h-screen">
      {/* Заголовок */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Ресурсы команды</h1>
        <p className="text-gray-600 mt-1">Полезные ссылки, файлы и заметки для работы</p>
      </div>

      {/* Вкладки */}
      <div className="flex space-x-1 mb-6 bg-gray-100 p-1 rounded-lg">
        {[
          { key: 'links', label: 'Ссылки', icon: Link2 },
          { key: 'files', label: 'Файлы', icon: FileText },
          { key: 'notes', label: 'Заметки', icon: BookOpen }
        ].map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-md transition-colors ${
                activeTab === tab.key
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* Панель управления */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Поиск..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center space-x-2 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600"
        >
          <Plus className="w-4 h-4" />
          <span>Добавить</span>
        </button>
      </div>

      {/* Контент */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredData().map((item: any) => (
          <div key={item.id} className="bg-white rounded-lg shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow flex flex-col h-full">
            {/* Ссылки */}
            {activeTab === 'links' && (
              <>
                <div className="flex items-start justify-between mb-3 relative">
                  <div className="flex items-center space-x-2">
                    <Link2 className="w-5 h-5 text-blue-500" />
                    <h3 className="font-semibold text-gray-900">{item.title}</h3>
                    <button
                      onClick={() => handleToggleFavorite(item.id)}
                      className="p-1 rounded hover:bg-yellow-100 transition-colors"
                      title={item.isFavorite ? "Убрать из избранного" : "Добавить в избранное"}
                    >
                      <Star 
                        className={`w-4 h-4 transition-colors ${
                          item.isFavorite 
                            ? 'text-yellow-500 fill-current' 
                            : 'text-gray-300 hover:text-yellow-400'
                        }`} 
                      />
                    </button>
                  </div>
                  <div className="flex items-center space-x-1">
                    <button
                      onClick={() => handleEditLink(item)}
                      className="p-1 rounded hover:bg-blue-100 text-blue-500 hover:text-blue-600 transition-colors"
                      title="Редактировать"
                    >
                      <Edit3 className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => handleDeleteLink(item.id)}
                      className="p-1 rounded hover:bg-red-100 text-red-500 hover:text-red-600 transition-colors"
                      title="Удалить"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
                <div className="flex-grow">
                  {item.description && (
                    <p className="text-gray-600 text-sm mb-3">{item.description}</p>
                  )}
                </div>
                <div className="flex items-center justify-end text-xs text-gray-500 mb-3">
                  <div className="flex items-center space-x-1">
                    <Clock className="w-3 h-3" />
                    <span>{formatDate(item.createdAt)}</span>
                  </div>
                </div>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full text-center bg-blue-50 text-blue-600 py-2 rounded-md hover:bg-blue-100 transition-colors mt-auto"
                >
                  Перейти
                </a>
              </>
            )}

            {/* Файлы */}
            {activeTab === 'files' && (
              <>
                <div className="flex items-start justify-between mb-3 relative">
                  <div className="flex items-center space-x-2">
                    <FileText className="w-5 h-5 text-green-500" />
                    <h3 className="font-semibold text-gray-900">{item.name}</h3>
                    <button
                      onClick={() => handleToggleFileFavorite(item.id)}
                      className="p-1 rounded hover:bg-yellow-100 transition-colors"
                      title={item.isFavorite ? "Убрать из избранного" : "Добавить в избранное"}
                    >
                      <Star 
                        className={`w-4 h-4 transition-colors ${
                          item.isFavorite 
                            ? 'text-yellow-500 fill-current' 
                            : 'text-gray-300 hover:text-yellow-400'
                        }`} 
                      />
                    </button>
                  </div>
                  <div className="flex items-center space-x-1">
                    <button
                      onClick={() => handleEditFile(item)}
                      className="p-1 rounded hover:bg-blue-100 text-blue-500 hover:text-blue-600 transition-colors"
                      title="Редактировать"
                    >
                      <Edit3 className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => handleDeleteFile(item.id)}
                      className="p-1 rounded hover:bg-red-100 text-red-500 hover:text-red-600 transition-colors"
                      title="Удалить"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
                <div className="flex-grow">
                  <div className="space-y-2 text-sm text-gray-600 mb-3">
                    <div>Размер: {formatFileSize(item.size)}</div>
                    <div>Скачиваний: {item.downloadCount}</div>
                  </div>
                  <div className="text-xs text-gray-500 mb-3">
                    {formatDate(item.uploadedAt)}
                  </div>
                </div>
                <button 
                  onClick={() => handleDownloadFile(item)}
                  className="w-full bg-green-50 text-green-600 py-2 rounded-md hover:bg-green-100 transition-colors mt-auto"
                >
                  Скачать
                </button>
              </>
            )}

            {/* Заметки */}
            {activeTab === 'notes' && (
              <>
                {/* Фиксированная высота для области заголовка */}
                <div className="h-12 flex items-start justify-between mb-3 relative">
                  <div className="flex items-start space-x-2 flex-1 min-w-0">
                    <BookOpen className="w-5 h-5 text-purple-500 flex-shrink-0 mt-0.5" />
                    <h3 className="font-semibold text-gray-900 line-clamp-2 leading-tight">{item.title}</h3>
                    <button
                      onClick={() => handleToggleNotePinned(item.id)}
                      className="p-1 rounded hover:bg-yellow-100 transition-colors flex-shrink-0"
                      title={item.isPinned ? "Открепить заметку" : "Закрепить заметку"}
                    >
                      <Star 
                        className={`w-4 h-4 transition-colors ${
                          item.isPinned 
                            ? 'text-yellow-500 fill-current' 
                            : 'text-gray-300 hover:text-yellow-400'
                        }`} 
                      />
                    </button>
                  </div>
                  <div className="flex items-center space-x-1 flex-shrink-0 ml-2">
                    <button
                      onClick={() => handleEditNote(item)}
                      className="p-1 rounded hover:bg-blue-100 text-blue-500 hover:text-blue-600 transition-colors"
                      title="Редактировать"
                    >
                      <Edit3 className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => handleDeleteNote(item.id)}
                      className="p-1 rounded hover:bg-red-100 text-red-500 hover:text-red-600 transition-colors"
                      title="Удалить"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
                <div className="flex-grow flex flex-col">
                  <div 
                    className="flex-grow cursor-pointer hover:bg-gray-50 -m-2 p-2 rounded transition-colors"
                    onClick={() => handleViewNote(item)}
                    title="Нажмите для просмотра заметки"
                  >
                    <div className="text-sm text-gray-600 mb-3 line-clamp-3">
                      {item.content}
                    </div>
                  </div>
                </div>
                <div className="flex items-center justify-end text-xs text-gray-500 mt-auto">
                  <div className="flex items-center space-x-1">
                    <Clock className="w-3 h-3" />
                    <span>{formatDate(item.updatedAt)}</span>
                  </div>
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      {/* Модальное окно добавления */}
      {showAddForm && <AddResourceForm />}
      
      {/* Модальное окно редактирования */}
      {showEditForm && <EditLinkForm />}
      
      {/* Модальное окно редактирования файла */}
      {showEditFileForm && <EditFileForm />}
      
      {/* Модальное окно редактирования заметки */}
      {showEditNoteForm && <EditNoteForm />}
      
      {/* Модальное окно просмотра заметки */}
      {showViewNoteModal && <ViewNoteModal />}
    </div>
  )
}

export default Resources