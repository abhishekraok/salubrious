import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { NavBar } from './NavBar';
import { get, post } from '../api/client';

export function Layout() {
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function checkAndRefresh() {
      try {
        const status = await get<{ stale: boolean }>('/prices/status');
        if (status.stale && !cancelled) {
          setRefreshing(true);
          await post('/prices/refresh');
          if (!cancelled) setRefreshing(false);
        }
      } catch {
        // silently ignore — prices just stay stale
      }
    }
    checkAndRefresh();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="flex min-h-screen font-sans">
      <NavBar />
      <main className="flex-1 p-8 max-w-4xl">
        {refreshing && (
          <div className="mb-4 px-3 py-2 bg-calm-blue/10 text-calm-blue text-sm rounded">
            Updating prices...
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
