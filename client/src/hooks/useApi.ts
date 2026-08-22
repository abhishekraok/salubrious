import { useCallback, useEffect, useRef, useState } from 'react';
import { get } from '../api/client';

interface ApiState<T> {
  path: string;
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useApi<T>(path: string) {
  const [state, setState] = useState<ApiState<T>>({
    path,
    data: null,
    loading: true,
    error: null,
  });
  const requestId = useRef(0);

  const load = useCallback(async () => {
    const currentRequestId = ++requestId.current;

    try {
      const data = await get<T>(path);
      if (currentRequestId === requestId.current) {
        setState({ path, data, loading: false, error: null });
      }
    } catch (error) {
      if (currentRequestId === requestId.current) {
        setState((current) => ({
          path,
          data: current.path === path ? current.data : null,
          loading: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        }));
      }
    }
  }, [path]);

  useEffect(() => {
    void load();

    return () => {
      requestId.current += 1;
    };
  }, [load]);

  const refetch = useCallback(() => {
    setState((current) => ({
      path,
      data: current.path === path ? current.data : null,
      loading: true,
      error: null,
    }));
    void load();
  }, [load, path]);

  const isCurrentPath = state.path === path;

  return {
    data: isCurrentPath ? state.data : null,
    loading: isCurrentPath ? state.loading : true,
    error: isCurrentPath ? state.error : null,
    refetch,
  };
}
