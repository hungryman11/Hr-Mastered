import { useEffect, useState } from 'react';
import { getKpiTemplates, KpiTemplate } from '../api/kpi';
import LoadingSpinner from '../components/LoadingSpinner';
import { Link } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';

const KpiTemplates = () => {
  const [templates, setTemplates] = useState<KpiTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();

  useEffect(() => {
    setLoading(true);
    getKpiTemplates().then(setTemplates).catch(() => addToast('Failed to load KPI templates', 'error')).finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="card">
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <h2>KPI Templates</h2>
        <Link to="/app/kpi/templates/new" className="btn-primary">Create Template</Link>
      </div>
      <h2>KPI Templates</h2>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Measurement</th>
              <th>Default Target</th>
              <th>Default Weight</th>
            </tr>
          </thead>
          <tbody>
            {templates.map(t => (
              <tr key={t.uuid}>
                <td>{t.name}</td>
                <td>{t.measurement_type}</td>
                <td>{t.default_target || '-'}</td>
                <td>{t.default_weight}</td>
                <td>
                  <Link to={`/app/kpi/templates/${t.uuid}/edit`} className="btn-secondary">Edit</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default KpiTemplates;
