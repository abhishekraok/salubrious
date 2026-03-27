import { NavLink } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { useAuth } from '../contexts/AuthContext';
import type { InvestmentPolicy } from '../types';

export function NavBar() {
  const { data: policy } = useApi<InvestmentPolicy>('/policy');
  const { user, logout } = useAuth();
  const isCategory = policy?.targeting_mode === 'category';

  const navItems = [
    { path: '/', label: 'Today' },
    { path: '/plan', label: 'Plan' },
    { path: '/holdings', label: 'Holdings' },
    ...(!isCategory ? [{ path: '/allocation', label: 'Allocation' }] : []),
    { path: '/insights', label: 'Insights' },
    { path: '/spending', label: 'Spending' },
    { path: '/review', label: 'Review' },
    { path: '/settings', label: 'Settings' },
  ];

  return (
    <nav className="w-48 min-h-screen bg-calm-surface border-r border-calm-border p-6 flex-shrink-0 flex flex-col">
      <h1 className="text-lg font-semibold text-calm-text mb-8 tracking-tight">Salubrious</h1>
      <ul className="space-y-1 flex-1">
        {navItems.map((item) => (
          <li key={item.path}>
            <NavLink
              to={item.path}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? 'bg-calm-bg text-calm-text font-medium'
                    : 'text-calm-muted hover:text-calm-text hover:bg-calm-bg'
                }`
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
      {user && (
        <div className="border-t border-calm-border pt-4 mt-4">
          <div className="flex items-center gap-2 px-3 mb-2">
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="" className="w-6 h-6 rounded-full" />
            ) : (
              <div className="w-6 h-6 rounded-full bg-calm-blue text-white flex items-center justify-center text-xs font-medium">
                {user.name.charAt(0).toUpperCase()}
              </div>
            )}
            <span className="text-sm text-calm-text truncate">{user.name}</span>
          </div>
          <button
            onClick={logout}
            className="block w-full text-left px-3 py-2 rounded-md text-sm text-calm-muted hover:text-calm-text hover:bg-calm-bg transition-colors"
          >
            Sign out
          </button>
        </div>
      )}
    </nav>
  );
}
