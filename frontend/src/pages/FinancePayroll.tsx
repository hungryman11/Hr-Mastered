import { useEffect, useState } from 'react';
import { format } from 'date-fns';
import {
  approvePayrollRun,
  calculatePayrollRun,
  createPayrollRun,
  exportPayrollRun,
  getPayrollRuns,
  PayrollRun,
  reconcilePayrollRun,
  reviewPayrollRun,
} from '../api/payroll';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusBadge from '../components/StatusBadge';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import styles from './Operations.module.css';
import clsx from 'clsx';

const FinancePayroll = () => {
  const { user } = useAuth();
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [newMonth, setNewMonth] = useState('');
  const [reconcileTarget, setReconcileTarget] = useState<PayrollRun | null>(null);
  const [bankRef, setBankRef] = useState('');
  const [reconcileResult, setReconcileResult] = useState<'SUCCESS' | 'FAILED'>('SUCCESS');
  const { addToast } = useToast();

  const isFinance = user?.role === 'FINANCE';

  const refresh = async () => {
    try {
      setRuns(await getPayrollRuns());
    } catch {
      addToast('Failed to load payroll runs', 'error');
    }
  };

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, []);

  const runAction = async (label: string, fn: () => Promise<unknown>) => {
    try {
      await fn();
      addToast(label, 'success');
      await refresh();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err !== null && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      addToast(detail || 'Action failed', 'error');
    }
  };

  const handleCreate = () => {
    if (!newMonth) {
      addToast('Pick a payroll month', 'error');
      return;
    }
    runAction('Payroll run created', () => createPayrollRun(newMonth));
  };

  const handleReconcile = async () => {
    if (!reconcileTarget || !bankRef.trim()) {
      addToast('Bank reference is required', 'error');
      return;
    }
    await runAction('Run reconciled', () =>
      reconcilePayrollRun(reconcileTarget.uuid, bankRef.trim(), reconcileResult)
    );
    setReconcileTarget(null);
    setBankRef('');
  };

  if (loading) return <LoadingSpinner />;

  const exported = runs.filter((r) => ['EXPORTED', 'RECONCILED'].includes(r.status));
  const pendingReconcile = runs.filter((r) => r.status === 'EXPORTED');

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Finance payroll</h1>
          <p className={styles.subtitle}>Review runs, export settlement packs, and reconcile bank outcomes.</p>
        </div>
      </header>

      <section className={styles.metrics}>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Total runs</div>
          <div className={styles.metricValue}>{runs.length}</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Awaiting reconciliation</div>
          <div className={styles.metricValue}>{pendingReconcile.length}</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Exported / reconciled</div>
          <div className={styles.metricValue}>{exported.length}</div>
        </div>
      </section>

      {isFinance && (
        <div className="card">
          <div className={styles.toolbar}>
            <input
              type="month"
              className="input-field"
              style={{ maxWidth: '200px' }}
              value={newMonth}
              onChange={(e) => setNewMonth(e.target.value ? `${e.target.value}-01` : '')}
            />
            <button type="button" className="btn-primary" onClick={handleCreate}>
              Open payroll run
            </button>
          </div>
        </div>
      )}

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Month</th>
                <th>Status</th>
                <th>Gross</th>
                <th>Net</th>
                <th>Settlement</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>
                    No payroll runs yet
                  </td>
                </tr>
              ) : (
                runs.map((run) => (
                  <tr key={run.uuid}>
                    <td>{format(new Date(run.month), 'MMMM yyyy')}</td>
                    <td>
                      <StatusBadge status={run.status} />
                    </td>
                    <td>{run.total_gross}</td>
                    <td>{run.net_payroll}</td>
                    <td>
                      {run.reconciliation ? (
                        <div
                          className={clsx(styles.reconcileCard, {
                            [styles.success]: run.reconciliation.result === 'SUCCESS',
                            [styles.failed]: run.reconciliation.result === 'FAILED',
                          })}
                        >
                          <StatusBadge status={run.reconciliation.result} />
                          <div className={styles.muted}>{run.reconciliation.bank_reference}</div>
                          <div className={styles.muted}>
                            {format(new Date(run.reconciliation.created_at), 'MMM d, yyyy HH:mm')}
                          </div>
                        </div>
                      ) : (
                        <span className={styles.muted}>Not reconciled</span>
                      )}
                    </td>
                    <td>
                      <div className={styles.actions}>
                        {isFinance && run.status === 'DRAFT' && (
                          <button type="button" className="btn-secondary" onClick={() => runAction('Calculated', () => calculatePayrollRun(run.uuid))}>
                            Calculate
                          </button>
                        )}
                        {isFinance && run.status === 'CALCULATED' && (
                          <button type="button" className="btn-secondary" onClick={() => runAction('Marked reviewed', () => reviewPayrollRun(run.uuid))}>
                            Review
                          </button>
                        )}
                        {isFinance && run.status === 'REVIEWED' && (
                          <button type="button" className="btn-primary" onClick={() => runAction('Approved', () => approvePayrollRun(run.uuid))}>
                            Approve
                          </button>
                        )}
                        {isFinance && run.status === 'APPROVED' && (
                          <button
                            type="button"
                            className="btn-primary"
                            onClick={() =>
                              runAction('Export queued', () => exportPayrollRun(run.uuid))
                            }
                          >
                            Export pack
                          </button>
                        )}
                        {isFinance && run.status === 'EXPORTED' && (
                          <button type="button" className="btn-secondary" onClick={() => setReconcileTarget(run)}>
                            Reconcile
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {reconcileTarget && (
        <div className={styles.modalBackdrop} role="presentation" onClick={() => setReconcileTarget(null)}>
          <div className={styles.modal} role="dialog" onClick={(e) => e.stopPropagation()}>
            <h2 className={styles.modalTitle}>
              Reconcile {format(new Date(reconcileTarget.month), 'MMMM yyyy')}
            </h2>
            <div className={styles.inlineForm}>
              <label>
                <span className={styles.muted}>Bank reference</span>
                <input className="input-field" value={bankRef} onChange={(e) => setBankRef(e.target.value)} />
              </label>
              <label>
                <span className={styles.muted}>Outcome</span>
                <select
                  className="input-field"
                  value={reconcileResult}
                  onChange={(e) => setReconcileResult(e.target.value as 'SUCCESS' | 'FAILED')}
                >
                  <option value="SUCCESS">Success</option>
                  <option value="FAILED">Failed</option>
                </select>
              </label>
              <div className={styles.toolbar}>
                <button type="button" className="btn-secondary" onClick={() => setReconcileTarget(null)}>
                  Cancel
                </button>
                <button type="button" className="btn-primary" onClick={handleReconcile}>
                  Save reconciliation
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FinancePayroll;
