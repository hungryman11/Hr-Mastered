import { useEffect, useState } from 'react';
import { getPerformanceCycles, PerformanceCycle, generateAssignments } from '../api/kpi';
import { updatePerformanceCycle } from '../api/kpi';
import LoadingSpinner from '../components/LoadingSpinner';
import { useToast } from '../contexts/ToastContext';

const PerformanceCycles = () => {
  const [cycles, setCycles] = useState<PerformanceCycle[]>([]);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();

  useEffect(() => {
    setLoading(true);
    getPerformanceCycles().then(setCycles).catch(() => addToast('Failed to load cycles', 'error')).finally(() => setLoading(false));
  }, []);

  const handleGenerate = async (c: PerformanceCycle) => {
    try {
      addToast('Generating assignments — this may take a moment', 'info');
      await generateAssignments(c.uuid);
      addToast('Assignments generated', 'success');
    } catch (err) {
      addToast('Failed to generate assignments', 'error');
    }
  };

  const handleToggleLock = async (c: PerformanceCycle) => {
    try {
      const updated = await updatePerformanceCycle(c.uuid, { locked: !c.locked });
      setCycles((prev) => prev.map(p => p.uuid === updated.uuid ? updated : p));
      addToast(updated.locked ? 'Cycle locked' : 'Cycle unlocked', 'success');
    } catch (err) {
      addToast('Failed to update cycle', 'error');
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="card">
      <h2>Performance Cycles</h2>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Period</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {cycles.map(c => (
              <tr key={c.uuid}>
                <td>{c.name}</td>
                <td>{c.start_date} — {c.end_date}</td>
                <td>
                  <button className="btn-primary" onClick={() => handleGenerate(c)}>Generate Assignments</button>
                  <button style={{marginLeft: '0.5rem'}} className="btn-secondary" onClick={() => handleToggleLock(c)}>{c.locked ? 'Unlock' : 'Lock'}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PerformanceCycles;
