import styles from './ApprovalTimeline.module.css';
import { LeaveApprovalStep } from '../api/leaves';
import { format } from 'date-fns';

interface ApprovalTimelineProps {
  steps: LeaveApprovalStep[];
}

const ApprovalTimeline = ({ steps }: ApprovalTimelineProps) => {
  return (
    <div className={styles.timeline}>
      {steps.sort((a, b) => a.sequence - b.sequence).map((step, idx) => (
        <div key={step.uuid} className={styles.node}>
          <div className={`${styles.dot} ${styles[step.status.toLowerCase()]}`}>
            {step.status === 'PENDING' && <div className={styles.pulse}></div>}
          </div>
          {idx < steps.length - 1 && <div className={styles.line}></div>}
          <div className={styles.content}>
            <div className={styles.stage}>{step.stage} - {step.approver}</div>
            <div className={styles.status}>{step.status}</div>
            {step.decided_at && (
              <div className={styles.date}>{format(new Date(step.decided_at), 'MMM dd, yyyy HH:mm')}</div>
            )}
            {step.decision_reason && (
              <div className={styles.reason}>Reason: {step.decision_reason}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default ApprovalTimeline;
