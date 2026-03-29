import type { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
}

export function Button({ variant = 'primary', className = '', children, ...props }: ButtonProps) {
  const base = 'px-4 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer';
  const variants = {
    primary: 'bg-calm-blue text-white hover:bg-calm-blue/90',
    secondary: 'bg-calm-surface border border-calm-border text-calm-text hover:bg-calm-bg',
    ghost: 'text-calm-muted hover:text-calm-text hover:bg-calm-bg',
  };

  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}
