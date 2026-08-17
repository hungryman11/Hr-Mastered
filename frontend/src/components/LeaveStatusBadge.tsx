import styles from './LeaveStatusBadge.module.css';

interface LeaveStatusBadgeProps {
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
}

const LeaveStatusBadge = ({ status }: LeaveStatusBadgeProps) => {
  return (
    <span className={`${styles.badge} ${styles[status.toLowerCase()]}`}>
      {status}
    </span>
  );
};

export default LeaveStatusBadge;
