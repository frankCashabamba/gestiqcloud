/**
 * Hook to fetch document ID types from API.
 */

import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';

export interface DocumentIDType {
  id: string;
  country_code: string;
  code: string;
  name_en: string;
  name_es?: string;
  name_pt?: string;
  regex_pattern?: string;
  sort_order: number;
}

interface UseDocumentIDTypesOptions {
  country_code?: string;
}

export function useDocumentIDTypes(options?: UseDocumentIDTypesOptions) {
  const { profile } = useAuth();
  const [data, setData] = useState<DocumentIDType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!profile?.tenant_id) {
      setData([]);
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        const url = new URL('/api/v1/hr/document-id-types', window.location.origin);
        if (options?.country_code) {
          url.searchParams.set('country_code', options.country_code);
        }

        const response = await fetch(url.toString(), {
          headers: {
            'tenant-id': profile.tenant_id,
          },
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch document ID types: ${response.statusText}`);
        }

        const result = await response.json();
        setData(result.data || []);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Unknown error'));
        setData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [profile?.tenant_id, options?.country_code]);

  return { data, loading, error };
}

// Convenience hook for getting display label
export function useDocumentIDTypeLabel(code: string) {
  const { data } = useDocumentIDTypes();
  const [label, setLabel] = useState<string>(code);

  useEffect(() => {
    const type = data.find((t) => t.code === code);
    if (type) {
      // Use user's language or default to English
      const lang = localStorage.getItem('language') || 'en';
      const labelKey = `name_${lang}` as keyof DocumentIDType;
      setLabel((type[labelKey] as string) || type.name_en);
    }
  }, [code, data]);

  return label;
}
