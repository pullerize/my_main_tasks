import { API_URL, authFetch } from '../api';

// Re-export base configuration
export { API_URL, authFetch };

// API endpoints
export const endpoints = {
  auth: {
    login: `${API_URL}/token`,
    me: `${API_URL}/users/me`,
  },
  users: {
    list: `${API_URL}/users/`,
    create: `${API_URL}/users/`,
    stats: (userId: number) => `${API_URL}/users/${userId}/stats`,
    report: (userId: number) => `${API_URL}/users/${userId}/report`,
  },
  tasks: {
    list: `${API_URL}/tasks/`,
    create: `${API_URL}/tasks/`,
    update: (id: number) => `${API_URL}/tasks/${id}`,
    delete: (id: number) => `${API_URL}/tasks/${id}`,
    complete: (id: number) => `${API_URL}/tasks/${id}/complete`,
  },
  projects: {
    list: `${API_URL}/projects/`,
    create: `${API_URL}/projects/`,
    update: (id: number) => `${API_URL}/projects/${id}`,
    delete: (id: number) => `${API_URL}/projects/${id}`,
    archive: (id: number) => `${API_URL}/projects/${id}/archive`,
    posts: (id: number) => `${API_URL}/projects/${id}/posts`,
  },
  digital: {
    projects: `${API_URL}/digital-projects/`,
    services: `${API_URL}/digital-services/`,
    tasks: (projectId: number) => `${API_URL}/digital-projects/${projectId}/tasks`,
    finance: (projectId: number) => `${API_URL}/digital-projects/${projectId}/finance`,
  },
  calendar: {
    shootings: `${API_URL}/shootings/`,
    operators: `${API_URL}/operators/`,
  },
  finance: {
    taxes: `${API_URL}/taxes/`,
    reports: `${API_URL}/project-reports/`,
    expenses: `${API_URL}/project-expenses/`,
    receipts: `${API_URL}/project-receipts/`,
  },
  resources: {
    files: `${API_URL}/resources/files`,
    upload: `${API_URL}/resources/upload`,
    download: (id: number) => `${API_URL}/resources/files/${id}/download`,
  },
  expenses: {
    categories: `${API_URL}/expense-categories/`,
    createCategory: `${API_URL}/expense-categories/`,
    updateCategory: (id: number) => `${API_URL}/expense-categories/${id}`,
    deleteCategory: (id: number) => `${API_URL}/expense-categories/${id}`,
    common: `${API_URL}/common-expenses/`,
    createCommon: `${API_URL}/common-expenses/`,
    updateCommon: (id: number) => `${API_URL}/common-expenses/${id}`,
    deleteCommon: (id: number) => `${API_URL}/common-expenses/${id}`,
    updateProject: (id: number) => `${API_URL}/project-expenses/${id}`,
    reports: `${API_URL}/expense-reports/`,
  }
};

// Helper functions
export const handleResponse = async (response: Response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }
  return response.json();
};

export const apiRequest = async (
  url: string,
  method: string = 'GET',
  data?: any,
  isFormData: boolean = false
) => {
  const options: RequestInit = {
    method,
    headers: isFormData ? {} : {
      'Content-Type': 'application/json',
    },
  };

  if (data) {
    options.body = isFormData ? data : JSON.stringify(data);
  }

  const response = await authFetch(url, options);
  return handleResponse(response);
};