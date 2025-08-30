export const API_URL = import.meta.env.VITE_API_URL || (
  // В продакшене используем относительный путь через nginx proxy
  window.location.hostname === 'localhost' ? 'http://localhost:8000' : '/api'
);

// Enhanced fetch with automatic logout on 401
export const authFetch = async (url: string, options: RequestInit = {}) => {
  const token = localStorage.getItem('token');
  
  const headers = {
    ...options.headers,
    ...(token && { Authorization: `Bearer ${token}` })
  };
  
  const response = await fetch(url, {
    ...options,
    headers
  });
  
  // If unauthorized, clear auth data and redirect to login
  if (response.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('userId');
    window.location.href = '/login';
    throw new Error('Unauthorized - redirecting to login');
  }
  
  return response;
};
