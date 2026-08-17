import { FormEvent, useEffect, useMemo, useState } from 'react';
import { createSalaryRecord, getSalaryRecords, SalaryRecord, supersedeSalaryRecord } from '../api/salary';
import { employeeLabel, EmployeeOption, getEmployees } from '../api/employees';
import LoadingSpinner from '../components/LoadingSpinner';
import StatusBadge from '../components/StatusBadge';
import { useToast } from '../contexts/ToastContext';

const emptyForm = { employeeId: '', effectiveDate: '', currency: 'NGN', base: '0', housing: '0', transport: '0', meal: '0', other: '0', reason: '' };
type FormData = typeof emptyForm;

const inputLabels: Array<[keyof FormData, string, 'text' | 'number' | 'date']> = [
  ['effectiveDate', 'Effective from', 'date'], ['currency', 'Currency', 'text'], ['base', 'Base salary', 'number'],
  ['housing', 'Housing allowance', 'number'], ['transport', 'Transport allowance', 'number'],
  ['meal', 'Meal allowance', 'number'], ['other', 'Other allowances', 'number'], ['reason', 'Reason', 'text'],
];

export default function SalaryRecords() {
  const [records, setRecords] = useState<SalaryRecord[]>([]);
  const [employees, setEmployees] = useState<EmployeeOption[]>([]);
  const [form, setForm] = useState<FormData>(emptyForm);
  const [mode, setMode] = useState<'create' | 'supersede' | null>(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const { addToast } = useToast();

  const load = async () => {
    setLoading(true);
    try { const [salaryRows, employeeRows] = await Promise.all([getSalaryRecords(), getEmployees()]); setRecords(salaryRows); setEmployees(employeeRows); }
    catch { addToast('Unable to load salary records or employees.', 'error'); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);
  const selectedEmployee = employees.find(employee => employee.id === Number(form.employeeId));
  const candidates = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return employees.slice(0, 12);
    return employees.filter(employee => `${employee.first_name} ${employee.last_name} ${employee.username} ${employee.org_unit_name || ''} ${employee.department_name || ''}`.toLowerCase().includes(term)).slice(0, 12);
  }, [employees, search]);
  const open = (nextMode: 'create' | 'supersede', record?: SalaryRecord) => { setMode(nextMode); setSearch(''); setForm(record ? { ...emptyForm, employeeId: String(record.employee), currency: record.currency } : emptyForm); };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!selectedEmployee) { addToast('Select an employee from the company employee list.', 'error'); return; }
    if (!confirm(mode === 'supersede' ? 'Supersede the selected employee’s active salary record? History will be retained.' : 'Create this salary record?')) return;
    setSaving(true);
    try {
      const payload = { effective_date: form.effectiveDate, currency: form.currency, base_salary: form.base, housing_allowance: form.housing, transport_allowance: form.transport, meal_allowance: form.meal, other_allowances: form.other, reason: form.reason };
      if (mode === 'supersede') await supersedeSalaryRecord({ ...payload, employee_uuid: selectedEmployee.uuid });
      else await createSalaryRecord({ ...payload, employee: selectedEmployee.id, status: 'ACTIVE' });
      addToast('Salary record saved.', 'success'); setMode(null); setForm(emptyForm); await load();
    } catch { addToast('Unable to save salary record. Review the required fields and effective dates.', 'error'); }
    finally { setSaving(false); }
  };
  if (loading) return <LoadingSpinner />;
  return <div className="card"><div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 16 }}><div><h1>Salary records</h1><p style={{ color: 'var(--color-text-muted)' }}>Company salary history and effective-dated changes.</p></div><button className="btn-primary" onClick={() => open('create')}>New record</button></div><div className="table-container"><table><thead><tr><th>Employee</th><th>Gross</th><th>Effective</th><th>Status</th><th /></tr></thead><tbody>{records.length === 0 ? <tr><td colSpan={5}>No salary records are available.</td></tr> : records.map(record => <tr key={record.uuid}><td>{record.employee_name}</td><td>{record.currency} {record.gross_salary}</td><td>{record.effective_date}{record.end_date ? ` — ${record.end_date}` : ''}</td><td><StatusBadge status={record.status} /></td><td>{record.status === 'ACTIVE' && <button className="btn-secondary" onClick={() => open('supersede', record)}>Supersede</button>}</td></tr>)}</tbody></table></div>{mode && <div className="modal-overlay"><form className="card modal-content" onSubmit={submit}><div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><h2>{mode === 'supersede' ? 'Supersede salary' : 'Create salary record'}</h2><button type="button" className="btn-secondary" onClick={() => setMode(null)}>Close</button></div><p style={{ color: 'var(--color-text-muted)', margin: '8px 0 14px' }}>Only employees in your company appear here. The backend validates the final selection.</p><label>Find employee<input autoFocus className="input-field" placeholder="Name, username, department, or org unit" value={search} onChange={event => setSearch(event.target.value)} /></label><div role="listbox" aria-label="Employee search results" style={{ border: '1px solid var(--color-border)', borderRadius: 8, marginTop: 8, maxHeight: 180, overflow: 'auto' }}>{candidates.length === 0 ? <p style={{ padding: 10 }}>No matching company employee.</p> : candidates.map(employee => <button type="button" key={employee.uuid} onClick={() => setForm({ ...form, employeeId: String(employee.id) })} style={{ display: 'block', width: '100%', padding: 10, textAlign: 'left', color: 'var(--color-text)', background: employee.id === selectedEmployee?.id ? 'var(--color-primary-glow)' : 'transparent' }}>{employeeLabel(employee)}<small style={{ display: 'block' }}>Employee ID: {employee.id}</small></button>)}</div>{selectedEmployee && <p style={{ marginTop: 8 }}><strong>Selected:</strong> {employeeLabel(selectedEmployee)}</p>}<div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginTop: 12 }}>{inputLabels.map(([key, label, type]) => <label key={key}>{label}<input required={key === 'effectiveDate'} className="input-field" type={type} min={type === 'number' ? '0' : undefined} step={type === 'number' ? '0.01' : undefined} value={form[key]} onChange={event => setForm({ ...form, [key]: event.target.value })} /></label>)}</div><div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}><button type="button" className="btn-secondary" onClick={() => setMode(null)}>Cancel</button><button disabled={saving || !selectedEmployee} type="submit" className="btn-primary">{saving ? 'Saving…' : 'Save salary record'}</button></div></form></div>}</div>;
}
