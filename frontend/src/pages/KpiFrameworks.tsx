import { useEffect, useState } from 'react';
import { getKpiFrameworks, KpiFramework } from '../api/kpi';
import LoadingSpinner from '../components/LoadingSpinner';
import { useToast } from '../contexts/ToastContext';
import { Link } from 'react-router-dom';

const KpiFrameworks = () => {
  const [frameworks, setFrameworks] = useState<KpiFramework[]>([]);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();

  useEffect(() => {
    setLoading(true);
    getKpiFrameworks().then(setFrameworks).catch(() => addToast('Failed to load KPI frameworks', 'error')).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="card">
        <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <h2>KPI Frameworks</h2>
          <Link to="/app/kpi/frameworks/new" className="btn-primary">Create Framework</Link>
        </div>
      <h2>KPI Frameworks</h2>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Scope</th>
              <th>Config</th>
                <th />
            </tr>
          </thead>
          <tbody>
            {frameworks.map(f => (
              <tr key={f.uuid}>
                <td>{f.name}</td>
                <td>{f.scope_type}</td>
                <td><pre style={{whiteSpace: 'pre-wrap'}}>{JSON.stringify(f.configuration || {}, null, 2)}</pre></td>
                  <td>
                    <Link to={`/app/kpi/frameworks/${f.uuid}/edit`} className="btn-secondary">Edit</Link>
                  </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default KpiFrameworks;
