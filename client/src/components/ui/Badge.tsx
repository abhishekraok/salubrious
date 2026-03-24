interface BadgeProps {
  status: 'ok' | 'watch' | 'action' | 'calm' | 'action_needed';
  children: React.ReactNode;
}

export function Badge({ status, children }: BadgeProps) {
  const colors = {
    ok: 'bg-calm-green/10 text-calm-green',
    calm: 'bg-calm-green/10 text-calm-green',
    watch: 'bg-calm-amber/10 text-calm-amber',
    action: 'bg-calm-red/10 text-calm-red',
    action_needed: 'bg-calm-red/10 text-calm-red',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[status]}`}>
      {children}
    </span>
  );
}
