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
    { path: '/spending', label: 'Spending' },
  ];

  return (
    <nav className="w-48 min-h-screen bg-calm-surface border-r border-calm-border p-6 flex-shrink-0 flex flex-col">
      <h1 className="text-lg font-semibold text-calm-text mb-8 tracking-tight">Salubrious</h1>
      <ul className="space-y-1">
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
        <div className="mt-auto pt-6 border-t border-calm-border">
          <p className="text-xs text-calm-muted truncate px-3 mb-2">{user.email || user.name}</p>
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
