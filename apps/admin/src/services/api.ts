/**
 * Centralized API Client
 * All backend API calls go through this client
 * Configuration is centralized in constants/api.ts
 */
import { API_BASE } from "../constants/api";

const getAuthToken = () =>
  typeof window !== "undefined"
    ? sessionStorage.getItem("access_token_admin")
    : null;

interface ApiError extends Error {
  status: number;
  data?: any;
}

class ApiErrorImpl extends Error implements ApiError {
  status: number;
  data?: any;

  constructor(status: number, data?: any) {
    super("API Error");
    this.status = status;
    this.data = data;
  }
}
// ============ HTTP Methods ============

async function request<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const token = getAuthToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = new ApiErrorImpl(response.status);
      try {
        error.data = await response.json();
      } catch {
        error.data = { message: response.statusText };
      }
      throw error;
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  } catch (error) {
    if (error instanceof ApiErrorImpl) throw error;
    throw new Error(`API request failed: ${error}`);
  }
}

function GET<T = any>(endpoint: string): Promise<T> {
  return request<T>(endpoint, { method: "GET" });
}

function POST<T = any>(endpoint: string, data?: any): Promise<T> {
  return request<T>(endpoint, {
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
  });
}

function PUT<T = any>(endpoint: string, data?: any): Promise<T> {
  return request<T>(endpoint, {
    method: "PUT",
    body: data ? JSON.stringify(data) : undefined,
  });
}

function PATCH<T = any>(endpoint: string, data?: any): Promise<T> {
  return request<T>(endpoint, {
    method: "PATCH",
    body: data ? JSON.stringify(data) : undefined,
  });
}

function DELETE<T = any>(endpoint: string): Promise<T> {
  return request<T>(endpoint, { method: "DELETE" });
}

const withParams = (endpoint: string, params?: Record<string, any>) => {
  if (!params) return endpoint;
  const query = new URLSearchParams(params).toString();
  if (!query) return endpoint;
  return `${endpoint}${endpoint.includes("?") ? "&" : "?"}${query}`;
};

// ============ UI Config API ============

export const apiClient = {
  // Axios-like helpers kept for compatibility
  get: async <T = any>(
    endpoint: string,
    config?: { params?: Record<string, any> }
  ): Promise<{ data: T }> => {
    const data = await GET<T>(withParams(endpoint, config?.params));
    return { data };
  },
  post: async <T = any>(
    endpoint: string,
    body?: any,
    config?: { params?: Record<string, any> }
  ): Promise<{ data: T }> => {
    const data = await POST<T>(withParams(endpoint, config?.params), body);
    return { data };
  },
  put: async <T = any>(
    endpoint: string,
    body?: any,
    config?: { params?: Record<string, any> }
  ): Promise<{ data: T }> => {
    const data = await PUT<T>(withParams(endpoint, config?.params), body);
    return { data };
  },
  patch: async <T = any>(
    endpoint: string,
    body?: any,
    config?: { params?: Record<string, any> }
  ): Promise<{ data: T }> => {
    const data = await PATCH<T>(withParams(endpoint, config?.params), body);
    return { data };
  },
  delete: async <T = any>(
    endpoint: string,
    config?: { params?: Record<string, any> }
  ): Promise<{ data: T }> => {
    const data = await DELETE<T>(withParams(endpoint, config?.params));
    return { data };
  },

  // UI Configuration Endpoints
  uiConfig: {
    basePath: "/v1/admin/ui-config",
    // Sections
    getSections: (params?: Record<string, any>) => {
      const query = new URLSearchParams(params).toString();
      return GET(
        `${apiClient.uiConfig.basePath}/sections${query ? `?${query}` : ""}`
      );
    },

    createSection: (data: any) =>
      POST(`${apiClient.uiConfig.basePath}/sections`, data),
    updateSection: (sectionId: string, data: any) =>
      PUT(`${apiClient.uiConfig.basePath}/sections/${sectionId}`, data),
    deleteSection: (sectionId: string) =>
      DELETE(`${apiClient.uiConfig.basePath}/sections/${sectionId}`),

    // Widgets
    getWidgetsBySection: (sectionId: string, params?: Record<string, any>) => {
      const query = new URLSearchParams(params).toString();
      return GET(
        `${apiClient.uiConfig.basePath}/sections/${sectionId}/widgets${
          query ? `?${query}` : ""
        }`
      );
    },

    createWidget: (data: any) =>
      POST(`${apiClient.uiConfig.basePath}/widgets`, data),
    updateWidget: (widgetId: string, data: any) =>
      PUT(`${apiClient.uiConfig.basePath}/widgets/${widgetId}`, data),
    deleteWidget: (widgetId: string) =>
      DELETE(`${apiClient.uiConfig.basePath}/widgets/${widgetId}`),

    // Tables
    getTables: () => GET(`${apiClient.uiConfig.basePath}/tables`),
    getTableConfig: (tableSlug: string) =>
      GET(`${apiClient.uiConfig.basePath}/tables/${tableSlug}`),
    createTable: (data: any) =>
      POST(`${apiClient.uiConfig.basePath}/tables`, data),
    updateTable: (tableId: string, data: any) =>
      PUT(`${apiClient.uiConfig.basePath}/tables/${tableId}`, data),
    deleteTable: (tableId: string) =>
      DELETE(`${apiClient.uiConfig.basePath}/tables/${tableId}`),

    // Forms
    getForms: () => GET(`${apiClient.uiConfig.basePath}/forms`),
    getFormConfig: (formSlug: string) =>
      GET(`${apiClient.uiConfig.basePath}/forms/${formSlug}`),
    createForm: (data: any) =>
      POST(`${apiClient.uiConfig.basePath}/forms`, data),
    updateForm: (formId: string, data: any) =>
      PUT(`${apiClient.uiConfig.basePath}/forms/${formId}`, data),
    deleteForm: (formId: string) =>
      DELETE(`${apiClient.uiConfig.basePath}/forms/${formId}`),

    // Dashboards
    getDefaultDashboard: () =>
      GET(`${apiClient.uiConfig.basePath}/dashboards/default`),
    getDashboards: () => GET(`${apiClient.uiConfig.basePath}/dashboards`),
    createDashboard: (data: any) =>
      POST(`${apiClient.uiConfig.basePath}/dashboards`, data),
    updateDashboard: (dashboardId: string, data: any) =>
      PUT(`${apiClient.uiConfig.basePath}/dashboards/${dashboardId}`, data),
    deleteDashboard: (dashboardId: string) =>
      DELETE(`${apiClient.uiConfig.basePath}/dashboards/${dashboardId}`),
  },

  // Dashboard Stats Endpoints
  dashboard: {
    getStats: (params?: Record<string, any>) => {
      const query = new URLSearchParams(params).toString();
      return GET(`/dashboard_stats${query ? `?${query}` : ""}`);
    },

    getKpis: (params?: Record<string, any>) => {
      const query = new URLSearchParams(params).toString();
      return GET(`/dashboard_kpis${query ? `?${query}` : ""}`);
    },
  },

  // Incidents API
  incidents: {
    list: (params?: Record<string, any>) => {
      const query = new URLSearchParams(params).toString();
      return GET(`/incidents${query ? `?${query}` : ""}`);
    },

    get: (incidentId: string) => GET(`/incidents/${incidentId}`),
    create: (data: any) => POST("/incidents", data),
    update: (incidentId: string, data: any) =>
      PUT(`/incidents/${incidentId}`, data),
    delete: (incidentId: string) => DELETE(`/incidents/${incidentId}`),
  },

  // Notifications API
  notifications: {
    list: (params?: Record<string, any>) => {
      const query = new URLSearchParams(params).toString();
      return GET(`/notifications${query ? `?${query}` : ""}`);
    },

    get: (notificationId: string) =>
      GET(`/notifications/${notificationId}`),
    markAsRead: (notificationId: string) =>
      PUT(`/notifications/${notificationId}`, { read: true }),
  },

  // Payments API
  payments: {
    list: (params?: Record<string, any>) => {
      const query = new URLSearchParams(params).toString();
      return GET(`/payments${query ? `?${query}` : ""}`);
    },

    get: (paymentId: string) => GET(`/payments/${paymentId}`),
    create: (data: any) => POST("/payments", data),
    update: (paymentId: string, data: any) =>
      PUT(`/payments/${paymentId}`, data),
  },

  // Webhooks API
  webhooks: {
    list: (params?: Record<string, any>) => {
      const query = new URLSearchParams(params).toString();
      return GET(`/webhooks${query ? `?${query}` : ""}`);
    },

    get: (webhookId: string) => GET(`/webhooks/${webhookId}`),
    create: (data: any) => POST("/webhooks", data),
    update: (webhookId: string, data: any) =>
      PUT(`/webhooks/${webhookId}`, data),
    delete: (webhookId: string) => DELETE(`/webhooks/${webhookId}`),

    test: (webhookId: string) =>
      POST(`/webhooks/${webhookId}/test`),
    getLogs: (webhookId: string, params?: Record<string, any>) => {
      const query = new URLSearchParams(params).toString();
      return GET(
        `/webhooks/${webhookId}/logs${query ? `?${query}` : ""}`
      );
    },
  },

  // E-invoicing API
  einvoicing: {
    list: (params?: Record<string, any>) => {
      const query = new URLSearchParams(params).toString();
      return GET(`/einvoicing${query ? `?${query}` : ""}`);
    },

    get: (documentId: string) =>
      GET(`/einvoicing/${documentId}`),
    send: (documentId: string) =>
      POST(`/einvoicing/${documentId}/send`),
    download: (documentId: string) =>
      GET(`/einvoicing/${documentId}/download`),
  },

  // Admin Config API
  admin: {
    getCompanies: (params?: Record<string, any>) => {
      const query = new URLSearchParams(params).toString();
      return GET(`/admin/companies${query ? `?${query}` : ""}`);
    },

    getUsers: (params?: Record<string, any>) => {
      const query = new URLSearchParams(params).toString();
      return GET(`/admin/users${query ? `?${query}` : ""}`);
    },

    getRoles: () => GET("/admin/roles"),
    getSectors: () => GET("/admin/sectors"),
    getCurrencies: () => GET("/admin/currencies"),
    getCountries: () => GET("/admin/countries"),
  },
};

export default apiClient;
