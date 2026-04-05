const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

interface ApiResponse<T = any> {
  code: number;
  message: string;
  data?: T;
}

interface User {
  id: number;
  username: string;
  role: string;
}

interface LoginResponse {
  token: string;
  user: User;
}

class ApiError extends Error {
  code: number;
  constructor(message: string, code: number) {
    super(message);
    this.code = code;
    this.name = 'ApiError';
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  const data: ApiResponse<T> = await response.json();

  if (data.code !== 0) {
    throw new ApiError(data.message, data.code);
  }

  return data.data as T;
}

export const api = {
  auth: {
    login: (username: string, password: string) =>
      request<LoginResponse>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }),

    register: (username: string, password: string) =>
      request<LoginResponse>('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }),

    logout: () => {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      }
    },

    getCurrentUser: (): User | null => {
      if (typeof window === 'undefined') return null;
      const userStr = localStorage.getItem('user');
      return userStr ? JSON.parse(userStr) : null;
    },

    getToken: (): string | null => {
      if (typeof window === 'undefined') return null;
      return localStorage.getItem('token');
    },
  },

  categories: {
    list: () => request<any[]>('/api/categories'),
    create: (name: string, description?: string) =>
      request<any>('/api/categories', {
        method: 'POST',
        body: JSON.stringify({ name, description }),
      }),
    update: (id: number, name: string, description?: string) =>
      request<any>(`/api/categories/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ name, description }),
      }),
    delete: (id: number) =>
      request<void>(`/api/categories/${id}`, {
        method: 'DELETE',
      }),
  },

  feeds: {
    list: () => request<any[]>('/api/feeds'),
    get: (id: number) => request<any>(`/api/feeds/${id}`),
    create: (data: any) =>
      request<any>('/api/feeds', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: number, data: any) =>
      request<any>(`/api/feeds/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (id: number) =>
      request<void>(`/api/feeds/${id}`, {
        method: 'DELETE',
      }),
    fetch: (id: number) =>
      request<any>(`/api/feeds/${id}/fetch`, {
        method: 'POST',
      }),
    getTweets: (id: number, params?: any) => {
      const query = params ? `?${new URLSearchParams(params)}` : '';
      return request<any[]>(`/api/feeds/${id}/tweets${query}`);
    },
  },

  summaries: {
    list: () => request<any[]>('/api/summaries'),
    generate: () =>
      request<any>('/api/summaries/generate', {
        method: 'POST',
      }),
    getByCategory: (categoryId: number) =>
      request<any[]>(`/api/summaries?category_id=${categoryId}`),
    getByDate: (date: string) =>
      request<any[]>(`/api/summaries?date=${date}`),
  },

  twitter: {
    getUserInfo: (username: string) =>
      request<any>(`/api/twitter/user-info/${username}`),
  },
};

export { ApiError };
