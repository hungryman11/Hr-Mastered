import { useEffect, useState } from 'react';
import { format } from 'date-fns';
import {
  contestDeduction,
  getPayrollDeductions,
  PayrollDeduction,
  resolveDeduction,
} from '../api/payroll';
import LoadingSpinner from '../components/LoadingSpinner';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import styles from './Operations.module.css';

const DeductionDisputes = () => {
  const { user } = useAuth();
  const [deductions, setDeductions] = useState<PayrollDeduction[]>([]);
  const [loading, setLoading] = useState(true);
  const [contestReason, setContestReason] = useState<Record<string, string>>({});
  const [resolveNotes, setResolveNotes] = useState<Record<string, string>>({});
  const { addToast } = useToast();

  const isFinance = user?.role === 'FINANCE';

  const refresh = async () => {
    try {
      setDeductions(await getPayrollDeductions());
    } catch {
      addToast('Failed to load deductions', 'error');
    }
  };

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, []);

  const contested = deductions.filter((d) => d.contested_at);
  const held = deductions.filter((d) => d.is_held);

  if (loading) return <LoadingSpinner />;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Deduction disputes</h1>
          <p className={styles.subtitle}>Employees may contest held deductions; finance resolves contested items.</p>
        </div>
      </header>

      <section className={styles.metrics}>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Held deductions</div>
          <div className={styles.metricValue}>{held.length}</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Open contests</div>
          <div className={styles.metricValue}>{contested.filter((d) => d.is_held).length}</div>
        </div>
      </section>

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Employee</th>
                <th>Run month</th>
                <th>Deduction</th>
                <th>Amount</th>
                <th>Held</th>
                <th>Contest</th>
                <th>Resolution</th>
              </tr>
            </thead>
            <tbody>
              {deductions.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '2rem' }}>
                    No deductions on record
                  </td>
                </tr>
              ) : (
                deductions.map((d) => (
                  <tr key={d.uuid}>
                    <td>{d.employee_name}</td>
                    <td>{d.payroll_month}</td>
                    <td>
                      {d.name} ({d.kind})
                    </td>
                    <td>{d.amount}</td>
                    <td>{d.is_held ? 'Yes' : 'No'}</td>
                    <td>
                      {d.contested_at ? (
                        <div>
                          <div className={styles.muted}>{format(new Date(d.contested_at), 'MMM d, yyyy')}</div>
                          <div>{d.contest_reason}</div>
                        </div>
                      ) : d.is_held && user?.uuid === d.employee_uuid ? (
                        <div className={styles.inlineForm}>
                          <textarea
                            className="input-field"
                            rows={2}
                            placeholder="Reason for contest"
                            value={contestReason[d.uuid] || ''}
                            onChange={(e) =>
                              setContestReason((prev) => ({ ...prev, [d.uuid]: e.target.value }))
                            }
                          />
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={async () => {
                              try {
                                await contestDeduction(d.uuid, contestReason[d.uuid] || '');
                                addToast('Contest submitted', 'success');
                                await refresh();
                              } catch (err: unknown) {
                                const detail =
                                  typeof err === 'object' && err !== null && 'response' in err
                                    ? (err as { response?: { data?: { detail?: string } } }).response?.data
                                        ?.detail
                                    : undefined;
                                addToast(detail || 'Could not contest', 'error');
                              }
                            }}
                          >
                            Contest
                          </button>
                        </div>
                      ) : (
                        <span className={styles.muted}>—</span>
                      )}
                    </td>
                    <td>
                      {isFinance && d.is_held && d.contested_at ? (
                        <div className={styles.inlineForm}>
                          <textarea
                            className="input-field"
                            rows={2}
                            placeholder="Resolution notes"
                            value={resolveNotes[d.uuid] || ''}
                            onChange={(e) =>
                              setResolveNotes((prev) => ({ ...prev, [d.uuid]: e.target.value }))
                            }
                          />
                          <div className={styles.actions}>
                            <button
                              type="button"
                              className="btn-primary"
                              onClick={async () => {
                                try {
                                  await resolveDeduction(d.uuid, true, resolveNotes[d.uuid] || '');
                                  addToast('Deduction upheld', 'success');
                                  await refresh();
                                } catch {
                                  addToast('Resolution failed', 'error');
                                }
                              }}
                            >
                              Uphold
                            </button>
                            <button
                              type="button"
                              className="btn-danger"
                              onClick={async () => {
                                try {
                                  await resolveDeduction(d.uuid, false, resolveNotes[d.uuid] || '');
                                  addToast('Deduction removed', 'success');
                                  await refresh();
                                } catch {
                                  addToast('Resolution failed', 'error');
                                }
                              }}
                            >
                              Remove
                            </button>
                          </div>
                          {d.resolution_notes && <div className={styles.muted}>{d.resolution_notes}</div>}
                        </div>
                      ) : (
                        d.resolution_notes || <span className={styles.muted}>—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DeductionDisputes;
