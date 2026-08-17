import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getKpiFramework, createKpiFramework, updateKpiFramework, KpiFramework } from '../api/kpi';
import LoadingSpinner from '../components/LoadingSpinner';
import { useToast } from '../contexts/ToastContext';

const KpiFrameworkForm = () => {
  const { uuid } = useParams();
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [loading, setLoading] = useState<boolean>(!!uuid);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<Partial<KpiFramework>>({ name: '', scope_type: 'DEPARTMENT', configuration: {} });
  const [jsonError, setJsonError] = useState<string | null>(null);
  const sampleConfig = JSON.stringify([
    { template: '<template-uuid-1>', weight: 50, target: '90' },
    { template: '<template-uuid-2>', weight: 50, target: '75' }
  ], null, 2);

  useEffect(() => {
    if (!uuid) return;
    setLoading(true);
    getKpiFramework(uuid as string)
      .then((data) => setForm(data))
      .catch(() => addToast('Failed to load framework', 'error'))
      .finally(() => setLoading(false));
  }, [uuid]);

  const handleChange = (key: keyof KpiFramework, value: any) => setForm((s) => ({ ...s, [key as string]: value }));

  const handleSubmit = async (e: any) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (uuid) {
        await updateKpiFramework(uuid, form as Partial<KpiFramework>);
        addToast('Framework updated', 'success');
      } else {
        await createKpiFramework(form as Partial<KpiFramework>);
        addToast('Framework created', 'success');
      }
      navigate('/app/kpi/frameworks');
    } catch (err) {
      addToast('Failed to save framework', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="card">
      <h2>{uuid ? 'Edit' : 'Create'} KPI Framework</h2>
      <form onSubmit={handleSubmit} style={{display: 'grid', gap: '0.5rem'}}>
        <label>
          Name
          <input value={form.name || ''} onChange={(e) => handleChange('name', e.target.value)} required />
        </label>

        <label>
          Scope
          <select value={form.scope_type || 'DEPARTMENT'} onChange={(e) => handleChange('scope_type', e.target.value)}>
            <option value="DEPARTMENT">Department</option>
            <option value="POSITION">Position</option>
          </select>
        </label>

        <label>
          Position (if scope is Position)
          <input value={form.position || ''} onChange={(e) => handleChange('position', e.target.value)} />
        </label>

        <label>
          Configuration (JSON)
          <div style={{display: 'flex', gap: '0.5rem', alignItems: 'center'}}>
            <button type="button" className="btn-secondary" onClick={() => {
              try {
                const parsed = JSON.parse(sampleConfig);
                handleChange('configuration', parsed);
                setJsonError(null);
              } catch (e) {
                // ignore
              }
            }}>Insert sample</button>
            <button type="button" className="btn-secondary" onClick={() => {
              // pretty-print current configuration
              try {
                const pretty = JSON.stringify(typeof form.configuration === 'string' ? JSON.parse(form.configuration) : form.configuration || {}, null, 2)
                handleChange('configuration', JSON.parse(pretty))
                setJsonError(null)
              } catch (e) {
                setJsonError('Cannot pretty-print invalid JSON')
              }
            }}>Pretty print</button>
          </div>
          <textarea value={JSON.stringify(form.configuration || {}, null, 2)} onChange={(e) => {
            const v = e.target.value;
            try {
              const parsed = JSON.parse(v);
              handleChange('configuration', parsed);
              setJsonError(null);
            } catch (err: any) {
              // keep raw string in form but mark error
              handleChange('configuration', v);
              setJsonError(err?.message || 'Invalid JSON');
            }
          }} rows={8} onBlur={(e) => {
            // attempt to pretty print on blur if valid
            try {
              const parsed = JSON.parse(e.currentTarget.value);
              handleChange('configuration', parsed);
            } catch (err) {
              // ignore
            }
          }} />
          {jsonError && <div style={{color: 'var(--color-danger)', marginTop: '0.25rem'}}>{jsonError}</div>}
        </label>

        <div style={{display: 'flex', gap: '0.5rem'}}>
          <button type="submit" className="btn-primary" disabled={saving || !!jsonError}>{saving ? 'Saving…' : 'Save'}</button>
          <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
        </div>
      </form>
    </div>
  );
};

export default KpiFrameworkForm;
