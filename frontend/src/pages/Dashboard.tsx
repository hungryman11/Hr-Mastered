import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getLeaveBalances, getLeaveRequests, LeaveBalance, LeaveRequest } from '../api/leaves';
import { getPayrollDeductions, getPayrollRuns } from '../api/payroll';
import BalanceCard from '../components/BalanceCard';
import LeaveStatusBadge from '../components/LeaveStatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import { format } from 'date-fns';
import styles from './Dashboard.module.css';
import opStyles from './Operations.module.css';

const Dashboard = () => {
  const { user } = useAuth();
  const [balances, setBalances] = useState<LeaveBalance[]>([]);
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [payrollOpen, setPayrollOpen] = useState(0);
  const [payrollAwaitingReconcile, setPayrollAwaitingReconcile] = useState(0);
  const [heldDeductions, setHeldDeductions] = useState(0);
  const [loading, setLoading] = useState(true);

  const showPayrollMetrics = user && ['HR_ADMIN', 'FINANCE'].includes(user.role);

  useEffect(() => {
    if (!user) return;

    const tasks: Promise<void>[] = [
      getLeaveBalances(user.uuid).then(setBalances),
      getLeaveRequests().then((data) => setRequests(data.slice(0, 5))),
    ];

    if (showPayrollMetrics) {
      tasks.push(
        getPayrollRuns().then((runs) => {
          setPayrollOpen(runs.filter((r) => !['RECONCILED', 'FAILED'].includes(r.status)).length);
          setPayrollAwaitingReconcile(runs.filter((r) => r.status === 'EXPORTED').length);
        })
      );
    }

    tasks.push(
      getPayrollDeductions().then((rows) => {
        setHeldDeductions(rows.filter((d) => d.is_held).length);
      })
    );

    Promise.all(tasks).finally(() => setLoading(false));
  }, [user, showPayrollMetrics]);

  if (loading) return <LoadingSpinner />;

  return (
    <div className={styles.dashboard}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Welcome back, {user?.first_name}!</h1>
          <p className={styles.subtitle}>Leave and payroll at a glance.</p>
        </div>
        <Link to="/app/leave/new" className="btn-primary">
          Request Leave
        </Link>
      </header>

      {(showPayrollMetrics || heldDeductions > 0) && (
        <section className={opStyles.metrics}>
          {showPayrollMetrics && (
            <>
              <div className={opStyles.metricCard}>
                <div className={opStyles.metricLabel}>Active payroll runs</div>
                <div className={opStyles.metricValue}>{payrollOpen}</div>
              </div>
              <div className={opStyles.metricCard}>
                <div className={opStyles.metricLabel}>Awaiting reconciliation</div>
                <div className={opStyles.metricValue}>{payrollAwaitingReconcile}</div>
              </div>
            </>
          )}
          <div className={opStyles.metricCard}>
            <div className={opStyles.metricLabel}>Held deductions</div>
            <div className={opStyles.metricValue}>{heldDeductions}</div>
          </div>
        </section>
      )}

      <section className={styles.balances}>
        {balances.map((b) => (
          <BalanceCard
            key={b.leave_type_name}
            typeName={b.leave_type_name}
            remainingDays={b.remaining_days}
            allocatedDays={b.allocated_days || b.remaining_days + 10}
          />
        ))}
      </section>

      <section className={styles.recentRequests}>
        <div className="card">
          <h2 className={styles.sectionTitle}>Recent Leave Requests</h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Dates</th>
                  <th>Days</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {requests.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>
                      No recent requests
                    </td>
                  </tr>
                ) : (
                  requests.map((req) => (
                    <tr key={req.uuid}>
                      <td>{req.leave_type}</td>
                      <td>
                        {format(new Date(req.start_date), 'MMM dd, yyyy')} -{' '}
                        {format(new Date(req.end_date), 'MMM dd, yyyy')}
                      </td>
                      <td>{req.days_requested}</td>
                      <td>
                        <LeaveStatusBadge status={req.status} />
                      </td>
                      <td>
                        <Link to={`/app/leave/${req.uuid}`}>View</Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
