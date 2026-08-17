import { useEffect, useState } from 'react';
import { getKpiAssignments } from '../api/kpi';
import LoadingSpinner from '../components/LoadingSpinner';
import { useToast } from '../contexts/ToastContext';

const KpiAssignments = () => {
  const [assignments, setAssignments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();

  useEffect(() => {
    setLoading(true);
    getKpiAssignments().then(setAssignments).catch(() => addToast('Failed to load assignments', 'error')).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="card">
      <h2>KPI Assignments</h2>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Employee</th>
              <th>KPI</th>
              <th>Target</th>
              <th>Weight</th>
            </tr>
          </thead>
          <tbody>
            {assignments.map(a => (
              <tr key={a.uuid}>
                <td>{a.employee?.name || a.employee?.email || '—'}</td>
                <td>{a.template?.name}</td>
                <td>{a.target || '-'}</td>
                <td>{a.weight}</td>
                <td><a href={`/app/kpi/assignments/${a.uuid}`}>View</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default KpiAssignments;
