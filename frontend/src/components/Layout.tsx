import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Home, Plus, List, CheckSquare, Settings, Menu, X, LogOut, Upload, Landmark, Scale, Target, ClipboardCheck, Wallet } from 'lucide-react';
import styles from './Layout.module.css';
import clsx from 'clsx';

const Layout = () => {
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const toggleSidebar = () => setSidebarOpen(!sidebarOpen);

  const navItems = [
    { to: '/app/dashboard', icon: <Home size={20} />, label: 'Dashboard', roles: ['EMPLOYEE', 'MANAGER', 'HOD', 'HR_ADMIN', 'FINANCE', 'ADMIN', 'SUPERVISOR'] },

    { to: '/app/admin-dashboard', icon: <Settings size={20} />, label: 'Admin Dashboard', roles: ['HR_ADMIN'] },
    { to: '/app/leave/new', icon: <Plus size={20} />, label: 'Request Leave', roles: ['EMPLOYEE', 'MANAGER', 'HOD', 'HR_ADMIN'] },
    { to: '/app/my-leaves', icon: <List size={20} />, label: 'My Leaves', roles: ['EMPLOYEE', 'MANAGER', 'HOD', 'HR_ADMIN'] },
    { to: '/app/approvals', icon: <CheckSquare size={20} />, label: 'Approvals', roles: ['MANAGER', 'HOD', 'HR_ADMIN'] },
    { to: '/app/kpi/assignments', icon: <Target size={20} />, label: 'KPI assignments', roles: ['EMPLOYEE', 'MANAGER', 'HOD', 'HR_ADMIN'] },
    { to: '/app/performance/reviews', icon: <ClipboardCheck size={20} />, label: 'Performance reviews', roles: ['EMPLOYEE', 'MANAGER', 'HOD', 'HR_ADMIN'] },
    { to: '/app/salary/current', icon: <Wallet size={20} />, label: 'My salary', roles: ['EMPLOYEE'] },
    { to: '/app/salary/records', icon: <Wallet size={20} />, label: 'Salary records', roles: ['HR_ADMIN'] },
    { to: '/app/payroll/profiles', icon: <Upload size={20} />, label: 'Payroll profiles', roles: ['HR_ADMIN', 'FINANCE'] },
    { to: '/app/payroll/finance', icon: <Landmark size={20} />, label: 'Finance payroll', roles: ['HR_ADMIN', 'FINANCE'] },
    { to: '/app/deductions', icon: <Scale size={20} />, label: 'Deduction disputes', roles: ['EMPLOYEE', 'MANAGER', 'HOD', 'HR_ADMIN', 'FINANCE'] },
    { to: '/app/hr-admin', icon: <Settings size={20} />, label: 'HR Admin', roles: ['HR_ADMIN'] },
    { to: '/app/kpi/templates', icon: <Settings size={20} />, label: 'KPI templates', roles: ['HR_ADMIN'] },
    { to: '/app/kpi/frameworks', icon: <Settings size={20} />, label: 'KPI frameworks', roles: ['HR_ADMIN'] },
    { to: '/app/kpi/cycles', icon: <Settings size={20} />, label: 'Performance cycles', roles: ['HR_ADMIN'] },
  ];

  return (
    <div className={styles.layout}>
      <aside className={clsx(styles.sidebar, { [styles.open]: sidebarOpen })}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logo}>HR Mastered</div>
          <button className={styles.closeBtn} onClick={toggleSidebar}><X size={24} /></button>
        </div>
        <nav className={styles.nav}>
          {navItems.filter(item => user && item.roles.includes(user.role)).map(item => (
            <NavLink 
              key={item.to} 
              to={item.to}
              className={({ isActive }) => clsx(styles.navItem, { [styles.active]: isActive })}
            >
              {item.icon} <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className={styles.main}>
        <header className={styles.topbar}>
          <button className={styles.menuBtn} onClick={toggleSidebar}>
            <Menu size={24} />
          </button>
          <div className={styles.userProfile}>
            <span>{user?.first_name} {user?.last_name}</span>
            <div className={styles.avatar}>{user?.first_name.charAt(0)}</div>
            <button onClick={logout} className={styles.logoutBtn} title="Sign Out">
              <LogOut size={20} />
            </button>
          </div>
        </header>
        <div className={styles.content}>
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
