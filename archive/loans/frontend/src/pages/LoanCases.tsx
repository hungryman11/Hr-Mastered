import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import {
  createLoanCase,
  getLoanCases,
  getLoanProducts,
  LoanCase,
  LoanProduct,
} from '../api/loans';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusBadge from '../components/StatusBadge';
import styles from './Operations.module.css';

const emptyForm = {
  loan_product: '',
  requested_amount: '',
  purpose: '',
  repayment_months: '12',
  collateral_type: '',
  collateral_value: '',
  collateral_details: '',
};

const LoanCases = () => {
  const { user } = useAuth();
  const [cases, setCases] = useState<LoanCase[]>([]);
  const [products, setProducts] = useState<LoanProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const { addToast } = useToast();

  const canApply = user?.role === 'EMPLOYEE' || user?.role === 'MANAGER';

  const refresh = async () => {
    const [caseData, productData] = await Promise.all([getLoanCases(), getLoanProducts()]);
    setCases(caseData);
    setProducts(productData.filter((p) => p.is_active));
  };

  useEffect(() => {
    refresh()
      .catch(() => addToast('Failed to load loan cases', 'error'))
      .finally(() => setLoading(false));
  }, []);

  const openCases = cases.filter((c) => !['APPROVED', 'REJECTED'].includes(c.status));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user?.id && !user?.uuid) {
      addToast('Employee profile unavailable', 'error');
      return;
    }
    try {
      await createLoanCase({
        applicant: user.uuid,
        loan_product: form.loan_product,
        requested_amount: form.requested_amount,
        purpose: form.purpose,
        repayment_months: Number(form.repayment_months),
        collateral_type: form.collateral_type,
        collateral_value: form.collateral_value,
        collateral_details: form.collateral_details,
      });
      addToast('Loan case submitted', 'success');
      setShowForm(false);
      setForm(emptyForm);
      await refresh();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err !== null && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      addToast(detail || 'Could not create case', 'error');
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Loan cases</h1>
          <p className={styles.subtitle}>Track compliance workflow from intake through risk and admin review.</p>
        </div>
        {canApply && products.length > 0 && (
          <button type="button" className="btn-primary" onClick={() => setShowForm((v) => !v)}>
            {showForm ? 'Cancel' : 'New application'}
          </button>
        )}
      </header>

      <section className={styles.metrics}>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Total cases</div>
          <div className={styles.metricValue}>{cases.length}</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>In progress</div>
          <div className={styles.metricValue}>{openCases.length}</div>
        </div>
      </section>

      {showForm && (
        <div className="card">
          <form className={styles.inlineForm} style={{ maxWidth: '100%' }} onSubmit={handleSubmit}>
            <label>
              <span className={styles.muted}>Product</span>
              <select
                className="input-field"
                required
                value={form.loan_product}
                onChange={(e) => setForm((f) => ({ ...f, loan_product: e.target.value }))}
              >
                <option value="">Select product</option>
                {products.map((p) => (
                  <option key={p.uuid} value={p.uuid}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className={styles.muted}>Requested amount</span>
              <input
                className="input-field"
                required
                value={form.requested_amount}
                onChange={(e) => setForm((f) => ({ ...f, requested_amount: e.target.value }))}
              />
            </label>
            <label>
              <span className={styles.muted}>Purpose</span>
              <textarea
                className="input-field"
                required
                rows={3}
                value={form.purpose}
                onChange={(e) => setForm((f) => ({ ...f, purpose: e.target.value }))}
              />
            </label>
            <label>
              <span className={styles.muted}>Repayment months</span>
              <input
                className="input-field"
                type="number"
                min={1}
                required
                value={form.repayment_months}
                onChange={(e) => setForm((f) => ({ ...f, repayment_months: e.target.value }))}
              />
            </label>
            <label>
              <span className={styles.muted}>Collateral type</span>
              <input
                className="input-field"
                required
                value={form.collateral_type}
                onChange={(e) => setForm((f) => ({ ...f, collateral_type: e.target.value }))}
              />
            </label>
            <label>
              <span className={styles.muted}>Collateral value</span>
              <input
                className="input-field"
                required
                value={form.collateral_value}
                onChange={(e) => setForm((f) => ({ ...f, collateral_value: e.target.value }))}
              />
            </label>
            <label>
              <span className={styles.muted}>Collateral details</span>
              <textarea
                className="input-field"
                required
                rows={2}
                value={form.collateral_details}
                onChange={(e) => setForm((f) => ({ ...f, collateral_details: e.target.value }))}
              />
            </label>
            <button type="submit" className="btn-primary">
              Submit application
            </button>
          </form>
        </div>
      )}

      <div className="card">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Applicant</th>
                <th>Product</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Updated</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {cases.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>
                    No loan cases yet
                  </td>
                </tr>
              ) : (
                cases.map((c) => (
                  <tr key={c.uuid}>
                    <td>{c.applicant_name}</td>
                    <td>{c.product_name}</td>
                    <td>{c.requested_amount}</td>
                    <td>
                      <StatusBadge status={c.status} />
                    </td>
                    <td>{format(new Date(c.updated_at), 'MMM d, yyyy')}</td>
                    <td>
                      <Link to={`/app/loans/${c.uuid}`}>Open</Link>
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

export default LoanCases;
