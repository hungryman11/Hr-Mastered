import clsx from 'clsx';
import styles from './StatusBadge.module.css';

const STATUS_MAP: Record<string, string> = {
  DRAFT: 'draft',
  CALCULATED: 'info',
  REVIEWED: 'info',
  APPROVED: 'success',
  EXPORTED: 'success',
  RECONCILED: 'success',
  FAILED: 'danger',
  PENDING: 'pending',
  IN_REVIEW: 'info',
  RETURNED: 'warning',
  REJECTED: 'danger',
  MORE_INFO: 'warning',
  RECEIVED: 'success',
  MISSING: 'warning',
  NOT_APPLICABLE: 'muted',
  SUCCESS: 'success',
};

interface StatusBadgeProps {
  status: string;
  label?: string;
}

const StatusBadge = ({ status, label }: StatusBadgeProps) => {
  const variant = STATUS_MAP[status] || 'muted';
  return (
    <span className={clsx(styles.badge, styles[variant])}>
      {label || status.replace(/_/g, ' ')}
    </span>
  );
};

export default StatusBadge;
