import { useState, useEffect } from 'react';

// Hook для сохранения состояния фильтров в localStorage
export const usePersistedState = <T>(key: string, defaultValue: T): [T, (value: T) => void] => {
  const [state, setState] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return defaultValue;
    }
  });

  const setValue = (value: T) => {
    try {
      setState(value);
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.warn(`Error setting localStorage key "${key}":`, error);
    }
  };

  return [state, setValue];
};

// Очистить все сохраненные фильтры (утилита для отладки)
export const clearAllFilters = () => {
  const keys = Object.keys(localStorage);
  const filterKeys = keys.filter(key => key.startsWith('filter_') || key.includes('_filter_') || key.includes('_tab'));
  
  filterKeys.forEach(key => {
    localStorage.removeItem(key);
  });
  
  console.log(`Cleared ${filterKeys.length} filter keys from localStorage`);
};

// Экспортировать все сохраненные фильтры (утилита для отладки)
export const exportFilters = () => {
  const keys = Object.keys(localStorage);
  const filterKeys = keys.filter(key => key.startsWith('filter_') || key.includes('_filter_') || key.includes('_tab'));
  
  const filters: Record<string, any> = {};
  filterKeys.forEach(key => {
    try {
      filters[key] = JSON.parse(localStorage.getItem(key) || '');
    } catch (error) {
      filters[key] = localStorage.getItem(key);
    }
  });
  
  return filters;
};