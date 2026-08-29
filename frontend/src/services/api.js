import axios from 'axios';

// In-Memory SWR Cache & Inflight Promise Deduplication Store
const cacheMap = new Map();
const inflightMap = new Map();

const DEFAULT_TTL_MS = 25000; // 25 seconds default TTL

const rawAxios = axios.create({
  baseURL: `${import.meta.env.VITE_API_BASE_URL}/api`,
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Strips Content-Type on FormData and attaches JWT tokens
rawAxios.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }

  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  return config;
});

// Automatic Token Refresh Interceptor
rawAxios.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/refresh')
    ) {
      originalRequest._retry = true;
      try {
        await axios.post('/api/auth/refresh', {}, { withCredentials: true });
        return rawAxios(originalRequest);
      } catch (refreshError) {
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export function invalidateCache(prefix = '') {
  if (!prefix) {
    cacheMap.clear();
    return;
  }
  for (const key of cacheMap.keys()) {
    if (key.includes(prefix)) {
      cacheMap.delete(key);
    }
  }
}

export function invalidateScopedCache(url = '') {
  if (!url) {
    cacheMap.clear();
    return;
  }
  const cleanUrl = url.toLowerCase();

  if (cleanUrl.includes('/resumes') || cleanUrl.includes('/applications')) {
    invalidateCache('/resumes');
    invalidateCache('/applications');
    invalidateCache('/dashboard');
    invalidateCache('/reports');
  } else if (cleanUrl.includes('/requirements')) {
    invalidateCache('/requirements');
    invalidateCache('/dashboard');
    invalidateCache('/reports');
  } else if (cleanUrl.includes('/targets')) {
    invalidateCache('/targets');
    invalidateCache('/dashboard');
  } else if (cleanUrl.includes('/attendance')) {
    invalidateCache('/attendance');
    invalidateCache('/dashboard');
  } else if (cleanUrl.includes('/notifications')) {
    invalidateCache('/notifications');
  } else if (cleanUrl.includes('/chat')) {
    invalidateCache('/chat');
  } else if (cleanUrl.includes('/users') || cleanUrl.includes('/clients')) {
    invalidateCache('/users');
    invalidateCache('/clients');
    invalidateCache('/dashboard');
  } else {
    invalidateCache(url);
    invalidateCache('/dashboard');
  }
}

// Wrapper with in-memory caching and concurrent request deduplication
const api = {
  ...rawAxios,

  async get(url, config = {}) {
    const isCacheDisabled = config.cache === false || config.responseType === 'blob';
    const ttl = config.ttl || DEFAULT_TTL_MS;
    const cacheKey = `${url}__${JSON.stringify(config.params || {})}`;

    // 1. Check in-memory cache
    if (!isCacheDisabled) {
      const cached = cacheMap.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < cached.ttl) {
        return {
          data: cached.data,
          status: 200,
          statusText: 'OK (Cached)',
          headers: {},
          config,
          fromCache: true,
        };
      }
    }

    // 2. Check inflight duplicate requests
    if (!isCacheDisabled && inflightMap.has(cacheKey)) {
      return inflightMap.get(cacheKey);
    }

    const requestPromise = (async () => {
      try {
        const response = await rawAxios.get(url, config);
        if (!isCacheDisabled && response.status === 200) {
          cacheMap.set(cacheKey, {
            data: response.data,
            timestamp: Date.now(),
            ttl,
          });
        }
        return response;
      } finally {
        inflightMap.delete(cacheKey);
      }
    })();

    if (!isCacheDisabled) {
      inflightMap.set(cacheKey, requestPromise);
    }

    return requestPromise;
  },

  async post(url, data, config) {
    invalidateScopedCache(url);
    return rawAxios.post(url, data, config);
  },

  async put(url, data, config) {
    invalidateScopedCache(url);
    return rawAxios.put(url, data, config);
  },

  async patch(url, data, config) {
    invalidateScopedCache(url);
    return rawAxios.patch(url, data, config);
  },

  async delete(url, config) {
    invalidateScopedCache(url);
    return rawAxios.delete(url, config);
  },

  invalidateCache,
  invalidateScopedCache,
};

export default api;
