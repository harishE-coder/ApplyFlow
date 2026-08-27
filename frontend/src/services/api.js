import axios from 'axios';

// In-Memory SWR Cache & Inflight Promise Deduplication Store
const cacheMap = new Map();
const inflightMap = new Map();

const DEFAULT_TTL_MS = 25000; // 25 seconds default TTL

const rawAxios = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Strips Content-Type on FormData
rawAxios.interceptors.request.use((config) => {
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
    invalidateCache();
    return rawAxios.post(url, data, config);
  },

  async put(url, data, config) {
    invalidateCache();
    return rawAxios.put(url, data, config);
  },

  async patch(url, data, config) {
    invalidateCache();
    return rawAxios.patch(url, data, config);
  },

  async delete(url, config) {
    invalidateCache();
    return rawAxios.delete(url, config);
  },

  invalidateCache,
};

export default api;
