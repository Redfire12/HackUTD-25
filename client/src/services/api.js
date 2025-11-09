import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

// Log API base URL for debugging
console.log('API Base URL:', API_BASE_URL);

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  signup: (userData) => api.post('/auth/signup', userData),
  login: (credentials) => api.post('/auth/login', credentials),
  getCurrentUser: () => api.get('/auth/me'),
};

// Feedback API
export const feedbackAPI = {
  analyze: (text) => api.post('/feedback/analyze', { text }),
  generateStory: (text) => api.post('/feedback/generate-story', { text }),
  getInsights: (text) => api.post('/feedback/insights', { text }),
  submit: (text) => api.post('/feedback/submit', { text }),
  update: (id, text) => api.put(`/feedback/${id}`, { text }),
  getHistory: (skip = 0, limit = 100) => api.get(`/feedback/history?skip=${skip}&limit=${limit}`),
  getFeedback: (id) => api.get(`/feedback/${id}`),
  deleteFeedback: (id) => api.delete(`/feedback/${id}`),
};

export default api;

