import { useState, useRef, useEffect, useMemo } from 'react'

interface CustomDatePickerProps {
  value: string
  onChange: (date: string) => void
  minDate?: string
  maxDate?: string
  className?: string
  style?: React.CSSProperties
}

const MONTHS = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
]

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

function CustomDatePicker({ value, onChange, minDate, maxDate, className = '', style }: CustomDatePickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [position, setPosition] = useState({ top: 0, left: 0 })
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Parse dates with memoization
  const selectedDate = useMemo(() => value ? new Date(value + 'T00:00:00') : null, [value])
  const minDateObj = useMemo(() => minDate ? new Date(minDate + 'T00:00:00') : null, [minDate])
  const maxDateObj = useMemo(() => maxDate ? new Date(maxDate + 'T00:00:00') : null, [maxDate])

  // Format date for display
  const formatDisplayDate = (dateStr: string) => {
    if (!dateStr) return 'Выберите дату'
    const date = new Date(dateStr + 'T00:00:00')
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
  }

  // Update calendar position
  const updatePosition = () => {
    if (dropdownRef.current) {
      const rect = dropdownRef.current.getBoundingClientRect()
      const calendarHeight = 380 // Примерная высота календаря
      const bottomMargin = 20 // Минимальный отступ от низа экрана

      // Проверяем, поместится ли календарь снизу
      const spaceBelow = window.innerHeight - rect.bottom
      const spaceAbove = rect.top

      let top
      if (spaceBelow >= calendarHeight + bottomMargin) {
        // Достаточно места снизу - показываем под элементом
        top = rect.bottom + window.scrollY + 4
      } else if (spaceAbove >= calendarHeight + bottomMargin) {
        // Не помещается снизу, но помещается сверху
        top = rect.top + window.scrollY - calendarHeight - 4
      } else {
        // Не помещается ни сверху, ни снизу - показываем с отступом от низа экрана
        top = window.innerHeight - calendarHeight - bottomMargin + window.scrollY
      }

      const left = Math.max(8, Math.min(
        rect.left + window.scrollX,
        window.innerWidth - 288 - 8
      ))

      setPosition({ top, left })
    }
  }

  // Close dropdown when clicking outside and handle position updates
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    const handleResize = () => {
      if (isOpen) {
        updatePosition()
      }
    }

    const handleScroll = () => {
      if (isOpen) {
        updatePosition()
      }
    }

    if (isOpen) {
      updatePosition()
      window.addEventListener('resize', handleResize)
      window.addEventListener('scroll', handleScroll, true)
    }

    document.addEventListener('mousedown', handleClickOutside)

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('scroll', handleScroll, true)
    }
  }, [isOpen])

  // Set current month based on selected date, min date, or current date
  useEffect(() => {
    if (value) {
      const date = new Date(value + 'T00:00:00')
      setCurrentMonth(new Date(date.getFullYear(), date.getMonth(), 1))
    } else if (minDate) {
      const date = new Date(minDate + 'T00:00:00')
      setCurrentMonth(new Date(date.getFullYear(), date.getMonth(), 1))
    }
  }, [value, minDate])

  // Generate calendar days with memoization
  const days = useMemo(() => {
    const year = currentMonth.getFullYear()
    const month = currentMonth.getMonth()

    // Use UTC dates to avoid timezone issues
    const firstDay = new Date(Date.UTC(year, month, 1))
    const lastDay = new Date(Date.UTC(year, month + 1, 0))

    // Get first Monday of the calendar view
    const firstMonday = new Date(firstDay)
    const dayOfWeek = firstDay.getUTCDay()
    const daysToSubtract = dayOfWeek === 0 ? 6 : dayOfWeek - 1
    firstMonday.setUTCDate(firstDay.getUTCDate() - daysToSubtract)

    const days = []
    const currentDate = new Date(firstMonday)

    // Generate 42 days (6 weeks)
    for (let i = 0; i < 42; i++) {
      const isCurrentMonth = currentDate.getUTCMonth() === month
      const dateStr = currentDate.toISOString().slice(0, 10)

      // Check if date is in allowed range
      // Compare dates by comparing just the date strings to avoid time zone issues
      const currentDateStr = currentDate.toISOString().slice(0, 10)
      const minDateStr = minDate
      const maxDateStr = maxDate

      const isInRange = (!minDateStr || currentDateStr >= minDateStr) &&
                       (!maxDateStr || currentDateStr <= maxDateStr)

      const isSelected = selectedDate &&
                        currentDate.getUTCDate() === selectedDate.getUTCDate() &&
                        currentDate.getUTCMonth() === selectedDate.getUTCMonth() &&
                        currentDate.getUTCFullYear() === selectedDate.getUTCFullYear()

      const today = new Date()
      const todayUTC = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()))
      const isToday = currentDate.toDateString() === todayUTC.toDateString()

      // Check if this is the first or last day in range
      const isFirstDay = minDateStr && currentDateStr === minDateStr
      const isLastDay = maxDateStr && currentDateStr === maxDateStr

      days.push({
        date: new Date(currentDate),
        dateStr,
        day: currentDate.getUTCDate(),
        isCurrentMonth,
        isInRange,
        isSelected,
        isToday,
        isFirstDay,
        isLastDay
      })

      currentDate.setUTCDate(currentDate.getUTCDate() + 1)
    }

    return days
  }, [currentMonth, selectedDate, minDateObj, maxDateObj])

  const handleDateSelect = (dateStr: string) => {
    onChange(dateStr)
    setIsOpen(false)
  }

  const navigateMonth = (direction: 'prev' | 'next') => {
    const newMonth = new Date(currentMonth)
    if (direction === 'prev') {
      newMonth.setMonth(newMonth.getMonth() - 1)
    } else {
      newMonth.setMonth(newMonth.getMonth() + 1)
    }
    setCurrentMonth(newMonth)
  }


  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full px-2 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-1 focus:ring-blue-500 focus:border-transparent transition-all bg-white text-left flex items-center justify-between ${className}`}
        style={style}
      >
        <span className={value ? 'text-gray-900' : 'text-gray-500'}>
          {formatDisplayDate(value)}
        </span>
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </button>

      {isOpen && (
        <div className="fixed bg-white border border-gray-200 rounded-lg shadow-xl z-[9999] p-3 min-w-[280px]"
             style={{
               top: `${position.top}px`,
               left: `${position.left}px`
             }}>
          {/* Month navigation and range display */}
          <div className="mb-3">
            <div className="flex items-center justify-between mb-2">
              <button
                type="button"
                onClick={() => navigateMonth('prev')}
                className="p-1 hover:bg-gray-100 rounded-md transition-colors"
              >
                <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>

              <h3 className="text-sm font-semibold text-gray-900">
                {MONTHS[currentMonth.getMonth()]} {currentMonth.getFullYear()}
              </h3>

              <button
                type="button"
                onClick={() => navigateMonth('next')}
                className="p-1 hover:bg-gray-100 rounded-md transition-colors"
              >
                <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>

            {/* Date range indicator */}
            {(minDate || maxDate) && (
              <div className="text-center">
                <div className="inline-flex items-center px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-md border border-blue-200">
                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  {minDate && maxDate && minDate === maxDate
                    ? formatDisplayDate(minDate)
                    : `${minDate ? formatDisplayDate(minDate) : '...'} — ${maxDate ? formatDisplayDate(maxDate) : '...'}`
                  }
                </div>
              </div>
            )}
          </div>

          {/* Weekday headers */}
          <div className="grid grid-cols-7 gap-1 mb-2">
            {WEEKDAYS.map(day => (
              <div key={day} className="text-xs font-medium text-gray-500 text-center py-1">
                {day}
              </div>
            ))}
          </div>

          {/* Calendar days */}
          <div className="grid grid-cols-7 gap-1">
            {days.map((day, index) => (
              <button
                key={index}
                type="button"
                onClick={() => day.isInRange && handleDateSelect(day.dateStr)}
                disabled={!day.isInRange}
                className={`
                  w-8 h-8 text-xs rounded-md transition-all duration-150 relative
                  ${day.isCurrentMonth
                    ? day.isInRange
                      ? 'text-gray-900 hover:bg-blue-50 hover:text-blue-600 border border-transparent hover:border-blue-200'
                      : 'text-gray-300 cursor-not-allowed bg-gray-50 opacity-40'
                    : day.isInRange
                      ? 'text-gray-400 hover:bg-blue-50 hover:text-blue-600'
                      : 'text-gray-200 cursor-not-allowed bg-gray-50 opacity-20'
                  }
                  ${day.isSelected
                    ? 'bg-blue-600 text-white hover:bg-blue-700 border-blue-600'
                    : ''
                  }
                  ${day.isToday && !day.isSelected
                    ? day.isInRange
                      ? 'bg-blue-100 text-blue-600 font-semibold border border-blue-300'
                      : 'bg-gray-100 text-gray-400 font-semibold border border-gray-300 opacity-50'
                    : ''
                  }
                  ${(day.isFirstDay || day.isLastDay) && !day.isSelected
                    ? 'ring-2 ring-green-400 ring-opacity-50 bg-green-50 text-green-700 font-semibold'
                    : ''
                  }
                `}
              >
                {day.day}
                {day.isToday && !day.isSelected && (
                  <div className="absolute bottom-0.5 left-1/2 transform -translate-x-1/2 w-1 h-1 bg-blue-600 rounded-full"></div>
                )}
              </button>
            ))}
          </div>

          {/* Additional info */}
          {(minDate || maxDate) && (
            <div className="mt-3 pt-2 border-t border-gray-100">
              <div className="text-xs text-gray-500 text-center">
                Выберите дату в указанном диапазоне
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default CustomDatePicker