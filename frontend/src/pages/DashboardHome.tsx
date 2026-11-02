import React, { useState, useEffect } from 'react';
import { collection, query, getDocs, where } from 'firebase/firestore';
import { db } from '../firebase';
import type { Exam } from '../types';
import { Link } from 'react-router-dom';

const DashboardHome: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalExams: 0,
    activeExams: 0,
    draftExams: 0,
    configuredClasses: 0,
    activeTemplates: 0,
  });
  const [recentExams, setRecentExams] = useState<Exam[]>([]);
  const [error, setError] = useState('');

  const fetchDashboardData = async () => {
    setLoading(true);
    setError('');
    try {
      // Fetch exams
      const examsSnap = await getDocs(query(collection(db, 'exams')));
      const examsList = examsSnap.docs.map(d => d.data() as Exam);
      
      const totalExams = examsList.length;
      const activeExams = examsList.filter(e => e.status === 'ACTIVE').length;
      const draftExams = examsList.filter(e => e.status === 'DRAFT').length;
      
      // Calculate configured classes by summing all classes arrays
      const configuredClasses = examsList.reduce((acc, e) => acc + (e.classes?.length || 0), 0);
      
      setRecentExams(examsList.slice(0, 5)); // Just take first 5 for now

      // Fetch templates
      const templatesSnap = await getDocs(query(collection(db, 'templates'), where('status', '==', 'APPROVED')));
      const activeTemplates = templatesSnap.docs.length;

      setStats({
        totalExams,
        activeExams,
        draftExams,
        configuredClasses,
        activeTemplates
      });
    } catch (err: any) {
      console.error(err);
      setError('Failed to load dashboard statistics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  return (
    <>
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
        <h2>Platform Overview</h2>
        <button className="btn btn-outline" onClick={fetchDashboardData} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh / Sync'}
        </button>
      </header>
      
      {error && <div style={{ color: '#991b1b', backgroundColor: '#fee2e2', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem' }}>{error}</div>}

      <div className="page-body">
        {loading ? (
          <div className="card">Loading real-time statistics...</div>
        ) : (
          <>
            <div className="stat-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
              <div className="stat-card" style={{ padding: '1.5rem', backgroundColor: '#fff', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                <div className="stat-title" style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Total Exams</div>
                <div className="stat-value" style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--primary-color)' }}>{stats.totalExams}</div>
              </div>
              <div className="stat-card" style={{ padding: '1.5rem', backgroundColor: '#fff', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                <div className="stat-title" style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Active Exams</div>
                <div className="stat-value" style={{ fontSize: '2rem', fontWeight: 600, color: '#166534' }}>{stats.activeExams}</div>
              </div>
              <div className="stat-card" style={{ padding: '1.5rem', backgroundColor: '#fff', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                <div className="stat-title" style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Draft Exams</div>
                <div className="stat-value" style={{ fontSize: '2rem', fontWeight: 600, color: '#b45309' }}>{stats.draftExams}</div>
              </div>
              <div className="stat-card" style={{ padding: '1.5rem', backgroundColor: '#fff', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                <div className="stat-title" style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Configured Classes</div>
                <div className="stat-value" style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--primary-color)' }}>{stats.configuredClasses}</div>
              </div>
              <div className="stat-card" style={{ padding: '1.5rem', backgroundColor: '#fff', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                <div className="stat-title" style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Active Templates</div>
                <div className="stat-value" style={{ fontSize: '2rem', fontWeight: 600, color: 'var(--primary-color)' }}>{stats.activeTemplates}</div>
              </div>
            </div>
            
            <div className="card">
              <h3 style={{ marginBottom: '1rem' }}>Recent Exams</h3>
              {recentExams.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)' }}>No exams configured yet.</p>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                      <th style={{ padding: '0.75rem' }}>Exam Name</th>
                      <th style={{ padding: '0.75rem' }}>ID</th>
                      <th style={{ padding: '0.75rem' }}>Status</th>
                      <th style={{ padding: '0.75rem' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentExams.map(exam => (
                      <tr key={exam.examId} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '0.75rem', fontWeight: 500 }}>{exam.name}</td>
                        <td style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>{exam.examId}</td>
                        <td style={{ padding: '0.75rem' }}>{exam.status}</td>
                        <td style={{ padding: '0.75rem' }}>
                          <Link to={`/exams/${exam.examId}`} style={{ color: 'var(--primary-color)', textDecoration: 'none' }}>Manage &rarr;</Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </>
        )}
      </div>
    </>
  );
};

export default DashboardHome;
