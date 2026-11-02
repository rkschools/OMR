import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { collection, query, getDocs } from 'firebase/firestore';
import { db } from '../firebase';
import type { Template } from '../types';

const TemplateGallery: React.FC = () => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        const snap = await getDocs(query(collection(db, 'templates')));
        setTemplates(snap.docs.map(doc => ({...doc.data(), _id: doc.id} as Template & { _id: string })));
      } catch (err: any) {
        console.error(err);
        setError('Failed to fetch templates');
      } finally {
        setLoading(false);
      }
    };
    fetchTemplates();
  }, []);

  if (loading) return <div>Loading templates...</div>;

  return (
    <>
      <header className="page-header">
        <h2>Template Gallery</h2>
      </header>
      
      {error && <div style={{ color: '#991b1b', backgroundColor: '#fee2e2', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem' }}>{error}</div>}
      {templates.length === 0 && !error && <div className="card">No templates found.</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
        {templates.map(tpl => (
          <div key={(tpl as any)._id || tpl.examId} className="card" style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ margin: 0 }}>{tpl.name}</h3>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Exam ID: {tpl.examId}</div>
              </div>
              <span style={{ 
                padding: '0.25rem 0.5rem', 
                borderRadius: '9999px', 
                fontSize: '0.75rem',
                fontWeight: 600,
                backgroundColor: tpl.status === 'APPROVED' ? '#dcfce7' : '#f1f5f9',
                color: tpl.status === 'APPROVED' ? '#166534' : '#475569'
              }}>
                {tpl.status}
              </span>
            </div>
            
            <div style={{ padding: '1rem', backgroundColor: '#f8fafc', borderRadius: '8px', marginBottom: '1.5rem', flex: 1 }}>
              <div style={{ marginBottom: '0.5rem' }}><strong>Active Version:</strong> {tpl.currentVersion || 'None'}</div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Templates control the layout, option counts, and student field coordinates for the OMR scanning engine.
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
              <Link to={`/templates/${(tpl as any)._id}`} className="btn btn-primary" style={{ flex: 1, textAlign: 'center', textDecoration: 'none' }}>Open Workspace</Link>
            </div>
          </div>
        ))}
      </div>
    </>
  );
};

export default TemplateGallery;
