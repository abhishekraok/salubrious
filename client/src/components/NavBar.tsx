import { NavLink } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import type { InvestmentPolicy } from '../types';

export function NavBar() {
  const { data: policy } = useApi<InvestmentPolicy>('/policy');
  const isCategory = policy?.targeting_mode === 'category';

  const navItems = [
    { path: '/', label: 'Today' },
    { path: '/plan', label: 'Plan' },
    { path: '/holdings', label: 'Holdings' },
    ...(!isCategory ? [{ path: '/allocation', label: 'Allocation' }] : []),
    { path: '/spending', label: 'Spending' },
  ];

  return (
    <nav className="w-48 min-h-screen bg-calm-surface border-r border-calm-border p-6 flex-shrink-0">
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
    </nav>
  );
}
