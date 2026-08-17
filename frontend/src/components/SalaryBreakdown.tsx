import { SalaryRecord } from '../api/salary';
import StatusBadge from './StatusBadge';

const money = (amount: string, currency: string) => `${currency} ${Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
export default function SalaryBreakdown({ record }: { record: SalaryRecord }) {
  const rows = [['Base', record.base_salary], ['Housing', record.housing_allowance], ['Transport', record.transport_allowance], ['Meal', record.meal_allowance], ['Other', record.other_allowances]];
  return <div className="card"><div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><h2>Current salary</h2><StatusBadge status={record.status} /></div><p style={{ color: 'var(--color-text-muted)', margin: '0.5rem 0 1rem' }}>Effective from {record.effective_date}</p>{rows.map(([label, value]) => <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.45rem 0' }}><span>{label}</span><strong>{money(value, record.currency)}</strong></div>)}<div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--color-border)', marginTop: 8, paddingTop: 12 }}><strong>Gross salary</strong><strong>{money(record.gross_salary, record.currency)}</strong></div></div>;
}
