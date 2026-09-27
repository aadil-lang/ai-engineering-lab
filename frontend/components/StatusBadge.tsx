import React from 'react';
import { getStatusColor } from '@/lib/utils';
import { CheckCircle, AlertTriangle, XCircle, Clock, Loader2 } from 'lucide-react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  showIcon = true,
}) => {
  const colors = getStatusColor(status);

  const getIcon = () => {
    switch (status) {
      case 'PASSED':
        return <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />;
      case 'FAILED':
      case 'ERROR':
        return <XCircle className="h-3.5 w-3.5 text-rose-400" />;
      case 'RUNNING':
        return <Loader2 className="h-3.5 w-3.5 text-cyan-400 animate-spin" />;
      case 'QUEUED':
      case 'PENDING':
        return <Clock className="h-3.5 w-3.5 text-amber-400" />;
      default:
        return null;
    }
  };

  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5 space-x-1',
    md: 'text-xs px-2.5 py-1 space-x-1.5',
    lg: 'text-sm px-3.5 py-1.5 space-x-2 font-semibold',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border font-medium uppercase tracking-wider ${colors.badge} ${sizeClasses[size]}`}
    >
      {showIcon && getIcon()}
      <span>{status}</span>
    </span>
  );
};
