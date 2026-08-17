import { useEffect, useState } from 'react';
import {
  CsvValidationError,
  getPayrollProfiles,
  importPayrollProfiles,
  parsePayrollImportError,
  PayrollProfile,
  validatePayrollProfilesCsv,
} from '../api/payroll';
import LoadingSpinner from '../components/LoadingSpinner';
import { useToast } from '../contexts/ToastContext';
import styles from './Operations.module.css';

const PayrollProfiles = () => {
  const [profiles, setProfiles] = useState<PayrollProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [validating, setValidating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [validCount, setValidCount] = useState<number | null>(null);
  const [errors, setErrors] = useState<CsvValidationError[]>([]);
  const { addToast } = useToast();

  const loadProfiles = async () => {
    try {
      setProfiles(await getPayrollProfiles());
    } catch {
      addToast('Failed to load payroll profiles', 'error');
    }
  };

  useEffect(() => {
    loadProfiles().finally(() => setLoading(false));
  }, []);

  const handleValidate = async () => {
    if (!file) {
      addToast('Choose a CSV file first', 'error');
      return;
    }
    setValidating(true);
    setErrors([]);
    setValidCount(null);
    try {
      const result = await validatePayrollProfilesCsv(file);
      setValidCount(result.valid_rows);
      setErrors(result.errors);
      if (result.errors.length === 0) {
        addToast(`${result.valid_rows} row(s) ready to import`, 'success');
      } else {
        addToast(`Found ${result.errors.length} validation issue(s)`, 'error');
      }
    } catch (err) {
      const parsed = parsePayrollImportError(err);
      if (Array.isArray(parsed)) {
        setErrors(parsed);
      } else {
        addToast(parsed, 'error');
      }
    } finally {
      setValidating(false);
    }
  };

  const handleImport = async () => {
    if (!file) {
      addToast('Choose a CSV file first', 'error');
      return;
    }
    setImporting(true);
    try {
      const result = await importPayrollProfiles(file);
      addToast(`Updated ${result.imported_profiles} profile(s)`, 'success');
      setErrors([]);
      setValidCount(null);
      setFile(null);
      await loadProfiles();
    } catch (err) {
      const parsed = parsePayrollImportError(err);
      if (Array.isArray(parsed)) {
        setErrors(parsed);
        addToast('Import blocked by validation errors', 'error');
      } else {
        addToast(parsed, 'error');
      }
    } finally {
      setImporting(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Payroll profiles</h1>
          <p className={styles.subtitle}>
            Upload CSV updates for employee_number, base_salary, bank_code, and hire_date (YYYY-MM-DD).
          </p>
        </div>
      </header>

      <div className="card">
        <div className={styles.uploadBox}>
          <input
            type="file"
            accept=".csv,text/csv"
            className="input-field"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setErrors([]);
              setValidCount(null);
            }}
          />
          <div className={styles.toolbar}>
            <button type="button" className="btn-secondary" disabled={!file || validating} onClick={handleValidate}>
              {validating ? 'Validating…' : 'Validate CSV'}
            </button>
            <button type="button" className="btn-primary" disabled={!file || importing} onClick={handleImport}>
              {importing ? 'Importing…' : 'Import profiles'}
            </button>
          </div>
          {validCount !== null && errors.length === 0 && (
            <p className={styles.muted}>{validCount} row(s) passed validation.</p>
          )}
          {errors.length > 0 && (
            <div className={styles.errorList}>
              {errors.map((row) => (
                <div key={row.line_number} className={styles.errorItem}>
                  <strong>Line {row.line_number}</strong>: {row.issues.join(', ')} invalid
                  <div className={styles.muted}>{JSON.stringify(row.row)}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h2 className={styles.title} style={{ fontSize: '1.125rem', marginBottom: '1rem' }}>
          Current profiles ({profiles.length})
        </h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Employee #</th>
                <th>Base salary</th>
                <th>Bank code</th>
                <th>Hire date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {profiles.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '2rem' }}>
                    No payroll profiles yet
                  </td>
                </tr>
              ) : (
                profiles.map((p) => (
                  <tr key={p.uuid}>
                    <td>{p.employee_number}</td>
                    <td>{p.base_salary}</td>
                    <td>{p.bank_code}</td>
                    <td>{p.hire_date}</td>
                    <td>{p.employment_status}</td>
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

export default PayrollProfiles;
