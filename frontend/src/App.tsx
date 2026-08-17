import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';

import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

import Login from './pages/Login';
import DemoLogin from './pages/DemoLogin';
import OAuthCallback from './pages/OAuthCallback';
import Dashboard from './pages/Dashboard';
import AdminDashboard from './pages/AdminDashboard';
import LeaveForm from './pages/LeaveForm';
import LeaveDetail from './pages/LeaveDetail';
import Reviewer from './pages/Reviewer';
import HRAdmin from './pages/HRAdmin';
import PayrollProfiles from './pages/PayrollProfiles';
import FinancePayroll from './pages/FinancePayroll';
import DeductionDisputes from './pages/DeductionDisputes';
import KpiTemplates from './pages/KpiTemplates';
import KpiFrameworks from './pages/KpiFrameworks';
import PerformanceCycles from './pages/PerformanceCycles';
import KpiAssignments from './pages/KpiAssignments';
import KpiTemplateForm from './pages/KpiTemplateForm';
import KpiFrameworkForm from './pages/KpiFrameworkForm';
import KpiAssignmentDetail from './pages/KpiAssignmentDetail';
import PerformanceReviews from './pages/PerformanceReviews';
import PerformanceReviewDetail from './pages/PerformanceReviewDetail';
import SalaryCurrent from './pages/SalaryCurrent';
import SalaryRecords from './pages/SalaryRecords';

const App = () => {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <Routes>
            <Route path="/app/login" element={<Login />} />
            <Route path="/app/demo-login" element={<DemoLogin />} />
            <Route path="/app/callback" element={<OAuthCallback />} />
            
            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route path="/app/dashboard" element={<Dashboard />} />
                <Route path="/app/leave/new" element={<LeaveForm />} />
                <Route path="/app/leave/:uuid" element={<LeaveDetail />} />
                <Route path="/app/my-leaves" element={<Navigate to="/app/dashboard" replace />} />
                
                {/* Role gated */}
                <Route element={<ProtectedRoute allowedRoles={['MANAGER', 'HOD', 'HR_ADMIN']} />}>
                  <Route path="/app/approvals" element={<Reviewer />} />
                </Route>
                
                <Route path="/app/deductions" element={<DeductionDisputes />} />
                <Route path="/app/performance/reviews" element={<PerformanceReviews />} />
                <Route path="/app/performance/reviews/:uuid" element={<PerformanceReviewDetail />} />
                <Route path="/app/salary/current" element={<SalaryCurrent />} />

                <Route element={<ProtectedRoute allowedRoles={['HR_ADMIN', 'FINANCE']} />}>
                  <Route path="/app/payroll/profiles" element={<PayrollProfiles />} />
                  <Route path="/app/payroll/finance" element={<FinancePayroll />} />
                </Route>

                <Route element={<ProtectedRoute allowedRoles={['HR_ADMIN']} />}>
                  <Route path="/app/admin-dashboard" element={<AdminDashboard />} />
                  <Route path="/app/hr-admin" element={<HRAdmin />} />
                  <Route path="/app/kpi/templates" element={<KpiTemplates />} />
                  <Route path="/app/kpi/templates/new" element={<KpiTemplateForm />} />
                  <Route path="/app/kpi/templates/:uuid/edit" element={<KpiTemplateForm />} />
                  <Route path="/app/kpi/frameworks" element={<KpiFrameworks />} />
                  <Route path="/app/kpi/frameworks/new" element={<KpiFrameworkForm />} />
                  <Route path="/app/kpi/frameworks/:uuid/edit" element={<KpiFrameworkForm />} />
                  <Route path="/app/kpi/cycles" element={<PerformanceCycles />} />
                  <Route path="/app/kpi/assignments" element={<KpiAssignments />} />
                  <Route path="/app/kpi/assignments/:uuid" element={<KpiAssignmentDetail />} />
                  <Route path="/app/salary/records" element={<SalaryRecords />} />
                </Route>
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
          </Routes>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
};

export default App;
