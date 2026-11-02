import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './AuthContext';
import { ProtectedRoute } from './ProtectedRoute';
import Login from './Login';
import { Seeder } from './Seeder';
import DashboardHome from './pages/DashboardHome';
import Exams from './pages/Exams';
import CreateExam from './pages/CreateExam';
import ExamDetail from './pages/ExamDetail';
import TemplateGallery from './pages/TemplateGallery';
import TemplateWorkspace from './pages/TemplateWorkspace';
import AnswerKeys from './pages/AnswerKeys';
import ScannerWorkspace from './pages/ScannerWorkspace';
import ResultsDashboard from './pages/ResultsDashboard';
import './index.css';

// Layout Component
const DashboardLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const { logout, currentUser } = useAuth();
  
  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>RISE OMR</h2>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            {currentUser?.email}
          </div>
        </div>
        <nav className="sidebar-nav">
          <Link to="/" className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}>Dashboard</Link>
          <Link to="/exams" className={`nav-link ${location.pathname.startsWith('/exams') ? 'active' : ''}`}>Exams</Link>
          <Link to="/templates" className={`nav-link ${location.pathname.startsWith('/templates') ? 'active' : ''}`}>Templates</Link>
          <Link to="/keys" className={`nav-link ${location.pathname.startsWith('/keys') ? 'active' : ''}`}>Answer Keys</Link>
          <Link to="/scanner" className={`nav-link ${location.pathname.startsWith('/scanner') ? 'active' : ''}`}>Scanner</Link>
          <Link to="/results" className={`nav-link ${location.pathname.startsWith('/results') ? 'active' : ''}`}>Results</Link>
          <Link to="/settings" className={`nav-link ${location.pathname.startsWith('/settings') ? 'active' : ''}`}>Settings</Link>
        </nav>
        <div style={{ padding: '1rem', borderTop: '1px solid var(--border-color)' }}>
          <button onClick={logout} className="btn btn-outline" style={{ width: '100%' }}>Logout</button>
        </div>
      </aside>
      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

// Main App
const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route path="/" element={<ProtectedRoute><DashboardLayout><DashboardHome /></DashboardLayout></ProtectedRoute>} />
          <Route path="/exams" element={<ProtectedRoute><DashboardLayout><Exams /></DashboardLayout></ProtectedRoute>} />
          <Route path="/exams/create" element={<ProtectedRoute><DashboardLayout><CreateExam /></DashboardLayout></ProtectedRoute>} />
          <Route path="/exams/:examId" element={<ProtectedRoute><DashboardLayout><ExamDetail /></DashboardLayout></ProtectedRoute>} />
          <Route path="/templates" element={<ProtectedRoute><DashboardLayout><TemplateGallery /></DashboardLayout></ProtectedRoute>} />
          <Route path="/templates/:templateId" element={<ProtectedRoute><DashboardLayout><TemplateWorkspace /></DashboardLayout></ProtectedRoute>} />
          <Route path="/keys" element={<ProtectedRoute><DashboardLayout><AnswerKeys /></DashboardLayout></ProtectedRoute>} />
          <Route path="/scanner" element={<ProtectedRoute><DashboardLayout><ScannerWorkspace /></DashboardLayout></ProtectedRoute>} />
          <Route path="/results" element={<ProtectedRoute><DashboardLayout><ResultsDashboard /></DashboardLayout></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><DashboardLayout>
            <header className="page-header"><h2>Settings</h2></header>
            <div className="page-body"><Seeder /></div>
          </DashboardLayout></ProtectedRoute>} />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;
