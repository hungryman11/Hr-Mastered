import styles from './BalanceCard.module.css';

interface BalanceCardProps {
  typeName: string;
  remainingDays: number;
  allocatedDays: number;
}

const BalanceCard = ({ typeName, remainingDays, allocatedDays }: BalanceCardProps) => {
  const percentage = allocatedDays > 0 ? (remainingDays / allocatedDays) * 100 : 0;
  
  let color = 'var(--color-success)';
  if (percentage <= 50 && percentage > 25) color = 'var(--color-warning)';
  if (percentage <= 25) color = 'var(--color-danger)';

  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className={`card ${styles.balanceCard}`}>
      <h3 className={styles.title}>{typeName}</h3>
      <div className={styles.chartContainer}>
        <svg className={styles.chart} width="100" height="100" viewBox="0 0 100 100">
          <circle 
            className={styles.chartBackground}
            cx="50" cy="50" r={radius} 
            strokeWidth="8"
          />
          <circle 
            className={styles.chartProgress}
            cx="50" cy="50" r={radius} 
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            stroke={color}
          />
        </svg>
        <div className={styles.chartText}>
          <span className={styles.remaining}>{remainingDays}</span>
          <span className={styles.allocated}>/ {allocatedDays}</span>
        </div>
      </div>
      <p className={styles.daysText}>Days Remaining</p>
    </div>
  );
};

export default BalanceCard;
