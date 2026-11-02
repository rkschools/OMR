import React, { useState, useEffect } from 'react';
import { collection, query, getDocs } from 'firebase/firestore';
import { db } from '../firebase';
import type { Exam } from '../types';
import { Link } from 'react-router-dom';

const Exams: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchExams = async () => {
      try {
        const q = query(collection(db, 'exams'));
        const snapshot = await getDocs(q);
        const data = snapshot.docs.map(doc => doc.data() as Exam);
        setExams(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchExams();
  }, []);

  const filteredExams = exams.filter(e => 
    e.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    e.examId.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <>
      <header className="page-header">
        <h2>Exams</h2>
        <Link to="/exams/create" className="btn btn-primary">Create Exam</Link>
      </header>
      <div className="page-body">
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <input 
            type="text" 
            className="form-control" 
            placeholder="Search exams by name or ID..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        
        {loading ? (
          <div>Loading exams...</div>
        ) : filteredExams.length === 0 ? (
          <div className="card">No exams found.</div>
        ) : (
          <div className="table-responsive card" style={{ padding: 0 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', backgroundColor: '#f8fafc' }}>
                  <th style={{ padding: '1rem' }}>Exam Name</th>
                  <th style={{ padding: '1rem' }}>ID</th>
                  <th style={{ padding: '1rem' }}>Year</th>
                  <th style={{ padding: '1rem' }}>Status</th>
                  <th style={{ padding: '1rem' }}>Classes</th>
                  <th style={{ padding: '1rem' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredExams.map(exam => (
                  <tr key={exam.examId} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '1rem', fontWeight: 500 }}>{exam.name}</td>
                    <td style={{ padding: '1rem', color: 'var(--text-secondary)' }}>{exam.examId}</td>
                    <td style={{ padding: '1rem' }}>{exam.year}</td>
                    <td style={{ padding: '1rem' }}>
                      <span style={{ 
                        padding: '0.25rem 0.5rem', 
                        borderRadius: '9999px', 
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        backgroundColor: exam.status === 'ACTIVE' ? '#dcfce7' : '#f1f5f9',
                        color: exam.status === 'ACTIVE' ? '#166534' : '#475569'
                      }}>
                        {exam.status}
                      </span>
                    </td>
                    <td style={{ padding: '1rem', fontSize: '0.875rem' }}>
                      {exam.classes?.length || 0} configured
                    </td>
                    <td style={{ padding: '1rem' }}>
                      <Link to={`/exams/${exam.examId}`} className="btn btn-outline" style={{ padding: '0.25rem 0.5rem', fontSize: '0.875rem' }}>Manage</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
};

export default Exams;
