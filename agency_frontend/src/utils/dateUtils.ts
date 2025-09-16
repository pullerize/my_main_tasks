// Утилиты для работы с датами в UTC+5

// Получить текущее время в формате ISO string с учетом UTC+5
export const getCurrentTimeUTC5 = (): string => {
  const now = new Date();
  const utc5Offset = 5 * 60 * 60 * 1000; // 5 часов в миллисекундах
  const utc5Date = new Date(now.getTime() + utc5Offset);
  return utc5Date.toISOString();
};

// Получить текущую дату в формате YYYY-MM-DD с учетом UTC+5
export const getCurrentDateUTC5 = (): string => {
  const now = new Date();
  const utc5Offset = 5 * 60 * 60 * 1000;
  const utc5Date = new Date(now.getTime() + utc5Offset);
  return utc5Date.toISOString().split('T')[0];
};

// Отформатировать дату в короткий формат ДД.ММ.ГГГГ с добавлением 5 часов
export const formatDateShortUTC5 = (isoString: string): string => {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    const utc5Date = new Date(date.getTime() + 5 * 60 * 60 * 1000); // +5 часов
    const day = utc5Date.getDate().toString().padStart(2, '0');
    const month = (utc5Date.getMonth() + 1).toString().padStart(2, '0');
    const year = utc5Date.getFullYear();
    return `${day}.${month}.${year}`;
  } catch (error) {
    return '';
  }
};

// Отформатировать дату в полный формат ДД.ММ.ГГГГ ЧЧ:ММ с добавлением 5 часов
export const formatDateUTC5 = (isoString: string): string => {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    const utc5Date = new Date(date.getTime() + 5 * 60 * 60 * 1000); // +5 часов
    const day = utc5Date.getDate().toString().padStart(2, '0');
    const month = (utc5Date.getMonth() + 1).toString().padStart(2, '0');
    const year = utc5Date.getFullYear();
    const hours = utc5Date.getHours().toString().padStart(2, '0');
    const minutes = utc5Date.getMinutes().toString().padStart(2, '0');
    return `${day}.${month}.${year} ${hours}:${minutes}`;
  } catch (error) {
    return '';
  }
};

// Преобразовать дату из формата ДД.ММ.ГГГГ в ISO string
export const parseRussianDate = (russianDate: string): string => {
  if (!russianDate) return '';
  try {
    const [day, month, year] = russianDate.split('.');
    const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    return date.toISOString();
  } catch (error) {
    return '';
  }
};

// Проверить, является ли дата сегодняшней
export const isToday = (isoString: string): boolean => {
  if (!isoString) return false;
  try {
    const date = new Date(isoString);
    const today = new Date();
    return date.toDateString() === today.toDateString();
  } catch (error) {
    return false;
  }
};

// Получить разность в днях между двумя датами
export const getDaysDifference = (date1: string, date2: string): number => {
  try {
    const d1 = new Date(date1);
    const d2 = new Date(date2);
    const diffTime = Math.abs(d2.getTime() - d1.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  } catch (error) {
    return 0;
  }
};

// Отформатировать дату и время для отображения (alias для formatDateUTC5)
export const formatDateTimeUTC5 = (isoString: string): string => {
  return formatDateUTC5(isoString);
};

// Отформатировать дедлайн БЕЗ добавления 5 часов
export const formatDeadline = (isoString: string): string => {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${day}.${month}.${year} ${hours}:${minutes}`;
  } catch (error) {
    return '';
  }
};

// Отформатировать дедлайн с учетом цветовой индикации
export const formatDeadlineUTC5 = (isoString: string): string => {
  if (!isoString) return '';
  try {
    const formatted = formatDeadline(isoString);
    
    // Возвращаем только форматированную дату, без стилей
    // Стили будут применяться в компоненте
    return formatted;
  } catch (error) {
    return '';
  }
};

// Получить статус дедлайна (для применения стилей в компонентах)
export const getDeadlineStatus = (isoString: string): 'overdue' | 'urgent' | 'normal' => {
  if (!isoString) return 'normal';
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffTime = date.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) return 'overdue'; // Просрочено
    if (diffDays <= 2) return 'urgent';  // Срочно (осталось 2 дня или меньше)
    return 'normal'; // Нормально
  } catch (error) {
    return 'normal';
  }
};