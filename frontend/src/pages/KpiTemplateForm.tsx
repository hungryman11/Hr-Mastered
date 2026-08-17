import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getKpiTemplate, createKpiTemplate, updateKpiTemplate, KpiTemplate } from '../api/kpi';
import LoadingSpinner from '../components/LoadingSpinner';
import { useToast } from '../contexts/ToastContext';

const KpiTemplateForm = () => {
  const { uuid } = useParams();
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [loading, setLoading] = useState<boolean>(!!uuid);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<Partial<KpiTemplate>>({ name: '', measurement_type: 'NUMBER', default_weight: 10 });

  useEffect(() => {
    if (!uuid) return;
    setLoading(true);
    getKpiTemplate(uuid as string)
      .then((data) => setForm(data))
      .catch(() => addToast('Failed to load template', 'error'))
      .finally(() => setLoading(false));
  }, [uuid]);

  const handleChange = (key: keyof KpiTemplate, value: any) => setForm((s) => ({ ...s, [key]: value }));

  const handleSubmit = async (e: any) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (uuid) {
        await updateKpiTemplate(uuid, form as Partial<KpiTemplate>);
        addToast('Template updated', 'success');
      } else {
        await createKpiTemplate(form as Partial<KpiTemplate>);
        addToast('Template created', 'success');
      }
      navigate('/app/kpi/templates');
    } catch (err) {
      addToast('Failed to save template', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="card">
      <h2>{uuid ? 'Edit' : 'Create'} KPI Template</h2>
      <form onSubmit={handleSubmit} style={{display: 'grid', gap: '0.5rem'}}>
        <label>
          Name
          <input value={form.name || ''} onChange={(e) => handleChange('name', e.target.value)} required />
        </label>

        <label>
          Measurement Type
          <select value={form.measurement_type || 'NUMBER'} onChange={(e) => handleChange('measurement_type', e.target.value)}>
            <option value="NUMBER">Number</option>
            <option value="BOOLEAN">Boolean</option>
            <option value="PERCENT">Percent</option>
          </select>
        </label>

        <label>
          Default Target
          <input value={form.default_target || ''} onChange={(e) => handleChange('default_target', e.target.value)} />
        </label>

        <label>
          Default Weight
          <input type="number" value={form.default_weight || 0} onChange={(e) => handleChange('default_weight', Number(e.target.value))} />
        </label>

        <div style={{display: 'flex', gap: '0.5rem'}}>
          <button type="submit" className="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
          <button type="button" className="btn-secondary" onClick={() => navigate(-1)}>Cancel</button>
        </div>
      </form>
    </div>
  );
};

export default KpiTemplateForm;
