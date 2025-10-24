// src/lib/api.ts
import api from "../utils/axios"; // tu instancia con baseURL y token

// GET
export const apiGet = async <T>(url: string): Promise<T> => {
  const res = await api.get<T>(url);
  return res.data;
};

// POST
const normalizeUrl = (url: string): string => {
  return url.endsWith("/") ? url : `${url}/`;
};

export const apiPost = async <T>(url: string, body: any = {}): Promise<T> => {
  const normalized = normalizeUrl(url);
  const res = await api.post<T>(normalized, body);
  return res.data;
};

// PUT
export const apiPut = async <T>(url: string, body: any): Promise<T> => {
  const res = await api.put<T>(url, body);
  return res.data;
};

// DELETE
export const apiDelete = async <T>(url: string): Promise<T> => {
  const res = await api.delete<T>(url);
  return res.data;
};

export const apiPostForm = async <T>(url: string, form: FormData): Promise<T> => {
  const res = await api.post<T>(url, form, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return res.data; 
};



