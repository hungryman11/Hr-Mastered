import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getKpiAssignments } from '../api/kpi';
import LoadingSpinner from '../components/LoadingSpinner';
import { useToast } from '../contexts/ToastContext';

const KpiAssignmentDetail = () => {
  const { uuid } = useParams();
  const [loading, setLoading] = useState(true);
  const [assignment, setAssignment] = useState<any>(null);
  const { addToast } = useToast();

  useEffect(() => {
    setLoading(true);
    // API currently exposes list endpoint; fetch and filter client-side
    getKpiAssignments()
      .then((rows) => setAssignment(rows.find((r: any) => r.uuid === uuid) || null))
      .catch(() => addToast('Failed to load assignment', 'error'))
      .finally(() => setLoading(false));
  }, [uuid]);

  if (loading) return <LoadingSpinner />;
  if (!assignment) return <div className="card">Assignment not found</div>;

  return (
    <div className="card">
      <h2>Assignment: {assignment.template?.name}</h2>
      <p><strong>Employee:</strong> {assignment.employee?.name || assignment.employee?.email}</p>
      <p><strong>Target:</strong> {assignment.target || '-'}</p>
      <p><strong>Weight:</strong> {assignment.weight}</p>
      <pre style={{whiteSpace: 'pre-wrap'}}>{JSON.stringify(assignment.source || {}, null, 2)}</pre>
    </div>
  );
};

export default KpiAssignmentDetail;
