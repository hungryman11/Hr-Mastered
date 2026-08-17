import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getLeaveTypes, LeaveType, updateLeaveType } from '../api/leaveTypes';
import { getDeliveryJobs, retryDeliveryJob, DeliveryJob } from '../api/deliveryJobs';
import client from '../api/client';
import { useToast } from '../contexts/ToastContext';
import LoadingSpinner from '../components/LoadingSpinner';
import styles from './HRAdmin.module.css';

const HRAdmin = () => {
  const [activeTab, setActiveTab] = useState<'types' | 'jobs' | 'health'>('types');
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([]);
  const [deliveryJobs, setDeliveryJobs] = useState<DeliveryJob[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();

  const fetchLeaveTypes = async () => {
    try {
      const data = await getLeaveTypes();
      setLeaveTypes(data);
    } catch (err) {
      addToast('Failed to fetch leave types', 'error');
    }
  };

  const fetchJobs = async () => {
    try {
      const data = await getDeliveryJobs();
      setDeliveryJobs(data);
    } catch (err) {
      addToast('Failed to fetch jobs', 'error');
    }
  };

  const fetchHealth = async () => {
    try {
      const res = await client.get('/healthz/');
      setHealth(res.data);
    } catch (err) {
      setHealth({ status: 'unhealthy' });
    }
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchLeaveTypes(), fetchJobs(), fetchHealth()]).finally(() => setLoading(false));

    const jobsInterval = setInterval(fetchJobs, 30000);
    const healthInterval = setInterval(fetchHealth, 60000);

    return () => {
      clearInterval(jobsInterval);
      clearInterval(healthInterval);
    };
  }, []);

  const handleToggleDocReq = async (type: LeaveType) => {
    try {
      await updateLeaveType(type.uuid, { requires_supporting_document: !type.requires_supporting_document });
      addToast('Leave type updated', 'success');
      fetchLeaveTypes();
    } catch (err) {
      addToast('Failed to update leave type', 'error');
    }
  };

  const handleRetryJob = async (uuid: string) => {
    try {
      await retryDeliveryJob(uuid);
      addToast('Job retry initiated', 'success');
      fetchJobs();
    } catch (err) {
      addToast('Failed to retry job', 'error');
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className={styles.adminContainer}>
      <h1 className={styles.title}>HR Administration</h1>
      <div style={{display: 'flex', gap: '0.5rem', marginBottom: '0.5rem'}}>
        <Link to="/app/kpi/templates" className="btn-secondary">KPI Templates</Link>
        <Link to="/app/kpi/frameworks" className="btn-secondary">KPI Frameworks</Link>
        <Link to="/app/kpi/cycles" className="btn-secondary">Performance Cycles</Link>
        <Link to="/app/kpi/assignments" className="btn-secondary">KPI Assignments</Link>
      </div>
      
      <div className={styles.tabs}>
        <button className={`${styles.tab} ${activeTab === 'types' ? styles.activeTab : ''}`} onClick={() => setActiveTab('types')}>Leave Types</button>
        <button className={`${styles.tab} ${activeTab === 'jobs' ? styles.activeTab : ''}`} onClick={() => setActiveTab('jobs')}>Delivery Jobs</button>
        <button className={`${styles.tab} ${activeTab === 'health' ? styles.activeTab : ''}`} onClick={() => setActiveTab('health')}>System Health</button>
      </div>

      <div className={`card ${styles.contentCard}`}>
        {activeTab === 'types' && (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Default Days</th>
                  <th>Max/Request</th>
                  <th>Carry Over</th>
                  <th>Requires Doc</th>
                </tr>
              </thead>
              <tbody>
                {leaveTypes.map(t => (
                  <tr key={t.uuid}>
                    <td>{t.name}</td>
                    <td>{t.default_days}</td>
                    <td>{t.max_days_per_request}</td>
                    <td>{t.carry_over_days}</td>
                    <td>
                      <label className={styles.switch}>
                        <input type="checkbox" checked={t.requires_supporting_document} onChange={() => handleToggleDocReq(t)} />
                        <span className={styles.slider}></span>
                      </label>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'jobs' && (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Job ID</th>
                  <th>Kind</th>
                  <th>Status</th>
                  <th>Attempts</th>
                  <th>Error</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {deliveryJobs.map(j => (
                  <tr key={j.uuid}>
                    <td>{j.uuid.substring(0, 8)}...</td>
                    <td>{j.kind}</td>
                    <td>
                      <span className={`${styles.badge} ${styles[j.status.toLowerCase()]}`}>{j.status}</span>
                    </td>
                    <td>{j.attempts}</td>
                    <td>{j.last_error || '-'}</td>
                    <td>
                      {j.status === 'FAILED' && (
                        <button className="btn-secondary" onClick={() => handleRetryJob(j.uuid)}>Retry</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'health' && (
          <div className={styles.healthContainer}>
            <div className={styles.healthStatus}>
              <h3>Overall Status: <span className={health?.status === 'unhealthy' ? styles.errorText : styles.successText}>{health?.status || 'Unknown'}</span></h3>
            </div>
            <pre className={styles.healthData}>
              {JSON.stringify(health, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default HRAdmin;
