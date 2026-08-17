import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getLeaveRequestDetail, getLeaveRequestRouting, cancelLeave, LeaveRequest, RoutingInfo } from '../api/leaves';
import LeaveStatusBadge from '../components/LeaveStatusBadge';
import ApprovalTimeline from '../components/ApprovalTimeline';
import LoadingSpinner from '../components/LoadingSpinner';
import { useToast } from '../contexts/ToastContext';
import { ExternalLink } from 'lucide-react';
import styles from './LeaveDetail.module.css';

const LeaveDetail = () => {
  const { uuid } = useParams<{ uuid: string }>();
  const [request, setRequest] = useState<LeaveRequest | null>(null);
  const [routing, setRouting] = useState<RoutingInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    if (uuid) {
      Promise.all([
        getLeaveRequestDetail(uuid),
        getLeaveRequestRouting(uuid)
      ]).then(([req, route]) => {
        setRequest(req);
        setRouting(route);
      }).catch(() => {
        addToast('Failed to load leave details', 'error');
        navigate('/app/dashboard');
      }).finally(() => setLoading(false));
    }
  }, [uuid, navigate, addToast]);

  const handleCancel = async () => {
    if (uuid && confirm('Are you sure you want to cancel this request?')) {
      try {
        await cancelLeave(uuid);
        addToast('Request cancelled', 'success');
        setRequest(prev => prev ? { ...prev, status: 'CANCELLED' } : null);
      } catch (err) {
        addToast('Failed to cancel', 'error');
      }
    }
  };

  if (loading || !request) return <LoadingSpinner />;

  return (
    <div className={styles.detailContainer}>
      <div className={`card ${styles.mainCard}`}>
        <div className={styles.header}>
          <h2>{request.leave_type} Leave</h2>
          <LeaveStatusBadge status={request.status} />
        </div>
        
        <div className={styles.grid}>
          <div className={styles.field}>
            <span className={styles.label}>Dates</span>
            <span className={styles.value}>{request.start_date} to {request.end_date}</span>
          </div>
          <div className={styles.field}>
            <span className={styles.label}>Days</span>
            <span className={styles.value}>{request.days_requested}</span>
          </div>
          <div className={styles.field}>
            <span className={styles.label}>Reason</span>
            <span className={styles.value}>{request.reason}</span>
          </div>
          {request.workdrive_url && (
            <div className={styles.field}>
              <span className={styles.label}>Document</span>
              <a href={request.workdrive_url} target="_blank" rel="noopener noreferrer" className={styles.docLink}>
                View Document <ExternalLink size={16} />
              </a>
            </div>
          )}
        </div>

        {request.status === 'PENDING' && new Date(request.start_date) > new Date() && (
          <div className={styles.actions}>
            <button className="btn-secondary" onClick={handleCancel}>Cancel Request</button>
          </div>
        )}
      </div>

      <div className={`card ${styles.timelineCard}`}>
        <h3>Approval Flow</h3>
        {routing && <ApprovalTimeline steps={routing.approval_steps} />}
      </div>
    </div>
  );
};

export default LeaveDetail;
