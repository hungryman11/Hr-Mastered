import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useToast } from '../contexts/ToastContext';
import { 
  getDashboardSummary, DashboardSummary,
  getRecentEmployees, RecentEmployee,
  getEmployeeStats, DepartmentStats,
  getOrgStructure, OrgStructure,
} from '../api/adminDashboard';
import { getEmployees, EmployeeOption } from '../api/employees';
import LoadingSpinner from '../components/LoadingSpinner';
import styles from './AdminDashboard.module.css';
import opStyles from './Operations.module.css';
import { format } from 'date-fns';

const AdminDashboard = () => {
  const { addToast } = useToast();
  
  const [activeTab, setActiveTab] = useState<'summary' | 'employees' | 'organization' | 'stats'>('summary');
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recentEmployees, setRecentEmployees] = useState<RecentEmployee[]>([]);
  const [deptStats, setDeptStats] = useState<DepartmentStats[]>([]);
  const [orgStructure, setOrgStructure] = useState<OrgStructure | null>(null);
  const [allEmployees, setAllEmployees] = useState<EmployeeOption[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [summaryData, recentData, statsData, structureData, allEmpData] = await Promise.all([
          getDashboardSummary(),
          getRecentEmployees(),
          getEmployeeStats(),
          getOrgStructure(),
          getEmployees(),
        ]);
        setSummary(summaryData);
        setRecentEmployees(recentData);
        setDeptStats(statsData);
        setOrgStructure(structureData);
        setAllEmployees(allEmpData);
      } catch (err) {
        addToast('Failed to load dashboard data', 'error');
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [addToast]);

  if (loading) return <LoadingSpinner />;

  // Filter employees based on search and filters
  const filteredEmployees = allEmployees.filter(emp => {
    const name = `${emp.first_name} ${emp.last_name}`.toLowerCase();
    const email = (emp.email ?? '').toLowerCase();
    const term = searchTerm.toLowerCase();
    return name.includes(term) || email.includes(term);
  });

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Admin Dashboard</h1>
          <p className={styles.subtitle}>Organization & HR management</p>
        </div>
        <Link to="/app/employee-create" className="btn-primary">
          Add Employee
        </Link>
      </header>

      {/* Tab Navigation */}
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === 'summary' ? styles.activeTab : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          Summary
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'employees' ? styles.activeTab : ''}`}
          onClick={() => setActiveTab('employees')}
        >
          Employees
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'organization' ? styles.activeTab : ''}`}
          onClick={() => setActiveTab('organization')}
        >
          Organization
        </button>
        <button
          className={`${styles.tab} ${activeTab === 'stats' ? styles.activeTab : ''}`}
          onClick={() => setActiveTab('stats')}
        >
          Statistics
        </button>
      </div>

      <div className={`card ${styles.contentCard}`}>
        {/* SUMMARY TAB */}
        {activeTab === 'summary' && summary && (
          <div className={styles.summaryContent}>
            <section className={opStyles.metrics}>
              <div className={opStyles.metricCard}>
                <div className={opStyles.metricLabel}>Active Employees</div>
                <div className={opStyles.metricValue}>{summary.total_active_employees}</div>
              </div>
              <div className={opStyles.metricCard}>
                <div className={opStyles.metricLabel}>Inactive Employees</div>
                <div className={opStyles.metricValue}>{summary.total_inactive_employees}</div>
              </div>
              <div className={opStyles.metricCard}>
                <div className={opStyles.metricLabel}>Pending Onboarding</div>
                <div className={opStyles.metricValue}>{summary.pending_onboarding}</div>
              </div>
              <div className={opStyles.metricCard}>
                <div className={opStyles.metricLabel}>Departments</div>
                <div className={opStyles.metricValue}>{summary.departments}</div>
              </div>
              <div className={opStyles.metricCard}>
                <div className={opStyles.metricLabel}>Pending Leave Requests</div>
                <div className={opStyles.metricValue}>{summary.pending_leave_requests}</div>
              </div>
              <div className={opStyles.metricCard}>
                <div className={opStyles.metricLabel}>Payroll Runs In Progress</div>
                <div className={opStyles.metricValue}>{summary.payroll_runs_in_progress}</div>
              </div>
            </section>

            {/* Employees by Role */}
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Employees by Role</h3>
              <table className={styles.roleTable}>
                <thead>
                  <tr>
                    <th>Role</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(summary.employees_by_role).map(([role, count]) => (
                    <tr key={role}>
                      <td>{role}</td>
                      <td>{count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            {/* Recent Employees */}
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Recently Added Employees</h3>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Role</th>
                      <th>Status</th>
                      <th>Added</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentEmployees.length === 0 ? (
                      <tr>
                        <td colSpan={5} style={{ textAlign: 'center', padding: '1rem' }}>
                          No recent employees
                        </td>
                      </tr>
                    ) : (
                      recentEmployees.map(emp => (
                        <tr key={emp.uuid}>
                          <td>{emp.first_name} {emp.last_name}</td>
                          <td>{emp.email}</td>
                          <td>{emp.role}</td>
                          <td>{emp.onboarding_status}</td>
                          <td>{format(new Date(emp.created_at), 'MMM dd, yyyy')}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}

        {/* EMPLOYEES TAB */}
        {activeTab === 'employees' && (
          <div className={styles.employeesContent}>
            <div className={styles.searchBar}>
              <input
                type="text"
                placeholder="Search by name or email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className={styles.searchInput}
              />
            </div>

            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Department</th>
                    <th>Position</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEmployees.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: '1rem' }}>
                        No employees found
                      </td>
                    </tr>
                  ) : (
                    filteredEmployees.map(emp => (
                      <tr key={emp.uuid}>
                        <td>{emp.first_name} {emp.last_name}</td>
                        <td>{emp.email || '-'}</td>
                        <td>{emp.department_name || '-'}</td>
                        <td>{emp.org_unit_name || '-'}</td>
                        <td>{emp.role || 'EMPLOYEE'}</td>
                        <td>Active</td>
                        <td>
                          <Link to={`/app/employee/${emp.uuid}`} className="btn-secondary" style={{ fontSize: '0.85rem' }}>
                            Edit
                          </Link>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ORGANIZATION TAB */}
        {activeTab === 'organization' && orgStructure && (
          <div className={styles.organizationContent}>
            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Organization Units</h3>
              <table className={styles.orgTable}>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Employees</th>
                  </tr>
                </thead>
                <tbody>
                  {orgStructure.org_units.map(unit => (
                    <tr key={unit.id}>
                      <td>{unit.name}</td>
                      <td>{unit.type}</td>
                      <td>{unit.employee_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>

            <section className={styles.section}>
              <h3 className={styles.sectionTitle}>Positions</h3>
              <table className={styles.orgTable}>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Org Unit</th>
                    <th>Filled</th>
                  </tr>
                </thead>
                <tbody>
                  {orgStructure.positions.map(pos => (
                    <tr key={pos.id}>
                      <td>{pos.title}</td>
                      <td>-</td>
                      <td>{pos.employee_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>
        )}

        {/* STATISTICS TAB */}
        {activeTab === 'stats' && deptStats && (
          <div className={styles.statsContent}>
            <h3 className={styles.sectionTitle}>Employees by Department</h3>
            <table className={styles.statsTable}>
              <thead>
                <tr>
                  <th>Department</th>
                  <th>Active</th>
                  <th>Inactive</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {deptStats.map(dept => (
                  <tr key={dept.department_id}>
                    <td>{dept.department_name}</td>
                    <td>{dept.active_count}</td>
                    <td>{dept.inactive_count}</td>
                    <td>{dept.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
