import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { format } from 'date-fns';
import {
  decideLoanCase,
  getLoanCase,
  LoanCase,
  verifyChecklistItem,
} from '../api/loans';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusBadge from '../components/StatusBadge';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import styles from './Operations.module.css';

const CHECKLIST_STATUSES = ['RECEIVED', 'MISSING', 'REJECTED', 'NOT_APPLICABLE'] as const;
const DECISIONS = ['APPROVED', 'RETURNED', 'REJECTED', 'MORE_INFO'] as const;

const LoanCaseDetail = () => {
  const { uuid } = useParams<{ uuid: string }>();
  const { user } = useAuth();
  const [loanCase, setLoanCase] = useState<LoanCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [itemDraft, setItemDraft] = useState<Record<string, { status: string; note: string; evidence: string }>>({});
  const [decision, setDecision] = useState<(typeof DECISIONS)[number]>('APPROVED');
  const [decisionReason, setDecisionReason] = useState('');
  const { addToast } = useToast();

  const isRisk = user?.role === 'RISK_CHECKER';
  const isCompliance = user?.role === 'COMPLIANCE_ADMIN';

  const load = async () => {
    if (!uuid) return;
    setLoanCase(await getLoanCase(uuid));
  };

  useEffect(() => {
    load()
      .catch(() => addToast('Failed to load case', 'error'))
      .finally(() => setLoading(false));
  }, [uuid]);

  const verifyItem = async (itemUuid: string) => {
    if (!loanCase || !uuid) return;
    const draft = itemDraft[itemUuid] || { status: 'RECEIVED', note: '', evidence: '' };
    try {
      await verifyChecklistItem(uuid, itemUuid, draft.status, draft.note, draft.evidence);
      addToast('Checklist updated', 'success');
      await load();
    } catch (err: unknown) {
      const data =
        typeof err === 'object' && err !== null && 'response' in err
          ? (err as { response?: { data?: Record<string, string> } }).response?.data
          : undefined;
      const msg = data?.detail || data?.note || data?.evidence_reference || 'Verification failed';
      addToast(typeof msg === 'string' ? msg : 'Verification failed', 'error');
    }
  };

  const submitDecision = async () => {
    if (!uuid) return;
    try {
      await decideLoanCase(uuid, decision, decisionReason);
      addToast('Decision recorded', 'success');
      await load();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err !== null && 'response' in err
          ? (err as { response?: { data?: { detail?: string; reason?: string } } }).response?.data
          : undefined;
      addToast(detail?.detail || detail?.reason || 'Decision failed', 'error');
    }
  };

  if (loading || !loanCase) return <LoadingSpinner />;

  return (
    <div className={styles.page}>
      <Link to="/app/loans">&larr; All loan cases</Link>

      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>{loanCase.product_name}</h1>
          <p className={styles.subtitle}>
            {loanCase.applicant_name} · {loanCase.requested_amount} · {loanCase.repayment_months} months
          </p>
        </div>
        <StatusBadge status={loanCase.status} />
      </header>

      <div className="card">
        <p>{loanCase.purpose}</p>
        <p className={styles.muted}>
          Collateral: {loanCase.collateral_type} ({loanCase.collateral_value}) — {loanCase.collateral_details}
        </p>
        {loanCase.decision_reason && (
          <p className={styles.muted}>Decision note: {loanCase.decision_reason}</p>
        )}
        <p className={styles.muted}>Last updated {format(new Date(loanCase.updated_at), 'PPpp')}</p>
      </div>

      <div className="card">
        <h2 className={styles.title} style={{ fontSize: '1.125rem', marginBottom: '1rem' }}>
          Compliance checklist
        </h2>
        {loanCase.checklist_items.map((item) => {
          const draft = itemDraft[item.uuid] || {
            status: item.status,
            note: item.note,
            evidence: item.evidence_reference,
          };
          return (
            <div key={item.uuid} className={styles.checklistRow}>
              <div>
                <strong>{item.name}</strong>
                {item.required && <span className={styles.muted}> (required)</span>}
              </div>
              <StatusBadge status={item.status} />
              {item.checked_at && (
                <span className={styles.muted}>Verified {format(new Date(item.checked_at), 'PP')}</span>
              )}
              {isRisk && (
                <div className={styles.inlineForm} style={{ maxWidth: '100%' }}>
                  <select
                    className="input-field"
                    value={draft.status}
                    onChange={(e) =>
                      setItemDraft((prev) => ({
                        ...prev,
                        [item.uuid]: { ...draft, status: e.target.value },
                      }))
                    }
                  >
                    {CHECKLIST_STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>
                  <input
                    className="input-field"
                    placeholder="Evidence reference"
                    value={draft.evidence}
                    onChange={(e) =>
                      setItemDraft((prev) => ({
                        ...prev,
                        [item.uuid]: { ...draft, evidence: e.target.value },
                      }))
                    }
                  />
                  <textarea
                    className="input-field"
                    rows={2}
                    placeholder="Note"
                    value={draft.note}
                    onChange={(e) =>
                      setItemDraft((prev) => ({
                        ...prev,
                        [item.uuid]: { ...draft, note: e.target.value },
                      }))
                    }
                  />
                  <button type="button" className="btn-secondary" onClick={() => verifyItem(item.uuid)}>
                    Save verification
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {isCompliance && (
        <div className="card">
          <h2 className={styles.title} style={{ fontSize: '1.125rem', marginBottom: '1rem' }}>
            Compliance decision
          </h2>
          <div className={styles.inlineForm} style={{ maxWidth: '100%' }}>
            <select
              className="input-field"
              value={decision}
              onChange={(e) => setDecision(e.target.value as (typeof DECISIONS)[number])}
            >
              {DECISIONS.map((d) => (
                <option key={d} value={d}>
                  {d.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
            <textarea
              className="input-field"
              rows={3}
              placeholder="Decision reason"
              value={decisionReason}
              onChange={(e) => setDecisionReason(e.target.value)}
            />
            <button type="button" className="btn-primary" onClick={submitDecision}>
              Submit decision
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoanCaseDetail;
