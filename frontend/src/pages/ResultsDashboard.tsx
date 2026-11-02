import React, { useState, useEffect } from 'react';
import { collection, getDocs, query, where } from 'firebase/firestore';
import { db } from '../firebase';
import type { Exam } from '../types';

const ResultsDashboard: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedExam, setSelectedExam] = useState('');
  const [selectedClass, setSelectedClass] = useState('');
  const [selectedSet, setSelectedSet] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [selectedDetail, setSelectedDetail] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchExams = async () => {
      const snap = await getDocs(collection(db, 'exams'));
      setExams(snap.docs.map(d => ({ ...d.data(), examId: d.id } as Exam)));
      setLoading(false);
    };
    fetchExams();
  }, []);

  const fetchResults = async () => {
    if (!selectedExam) return;
    setLoading(true);
    try {
      let q = query(collection(db, 'results'), where('examId', '==', selectedExam));
      if (selectedClass) {
        q = query(q, where('class', '==', selectedClass));
      }
      const snap = await getDocs(q);
      setResults(snap.docs.map(d => ({ ...d.data(), id: d.id })));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, [selectedExam, selectedClass]);

  const activeExam = exams.find(e => e.examId === selectedExam);

  // Leaderboard ranking logic:
  // 1. Higher total_score first
  // 2. More correct_count next
  // Leaderboard ranking logic:
  // 1. Filter: exclude REVIEW_REQUIRED and FAILED sheets (official leaderboard requires VALID status)
  // 2. Higher total_score first
  // 3. More correct_count next
  // 4. Fewer wrong_count next
  // 5. Stable tie-break by registration number
  const sortedResults = [...results]
    .filter(r => r.status !== 'REVIEW_REQUIRED' && r.status !== 'FAILED')
    .filter(r => !selectedSet || r.paperSet === selectedSet)
    .sort((a, b) => {
      const scoreDiff = (b.total_score ?? b.score ?? 0) - (a.total_score ?? a.score ?? 0);
      if (Math.abs(scoreDiff) > 0.0001) return scoreDiff;
      const correctDiff = (b.correct_count ?? 0) - (a.correct_count ?? 0);
      if (correctDiff !== 0) return correctDiff;
      const wrongDiff = (a.wrong_count ?? 0) - (b.wrong_count ?? 0);
      if (wrongDiff !== 0) return wrongDiff;
      return String(a.registrationNumber || a.registration_number || '').localeCompare(String(b.registrationNumber || b.registration_number || ''));
    });

  const exportCSV = () => {
    if (sortedResults.length === 0) return;
    const headers = ['Rank', 'Student Name', 'Registration Number', 'Class', 'Paper Set', 'Correct', 'Wrong', 'Unanswered', 'Ambiguous', 'Score', 'Percentage'];
    const rows = sortedResults.map((r, idx) => [
      idx + 1,
      r.studentName || r.student_name || r.registrationNumber || `Student ${idx + 1}`,
      r.registrationNumber || r.registration_number || '-',
      r.class || r.class_id || '-',
      r.paperSet || r.paper_set || '-',
      r.correct_count ?? 0,
      r.wrong_count ?? 0,
      r.unanswered_count ?? 0,
      r.ambiguous_count ?? 0,
      (r.total_score ?? r.score ?? 0).toFixed(2),
      (((r.total_score ?? r.score ?? 0) / 50) * 100).toFixed(1) + '%'
    ]);
    
    const csvContent = "data:text/csv;charset=utf-8," 
      + headers.join(",") + "\n" 
      + rows.map(e => e.join(",")).join("\n");
      
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `leaderboard_${selectedExam}_${selectedClass || 'all'}_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <>
      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
        <h2>Results & Analytics</h2>
        <button className="btn btn-primary" onClick={exportCSV} disabled={results.length === 0}>Export CSV</button>
      </header>
      
      <div className="page-body">
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <div className="form-group" style={{ flex: 1, minWidth: '200px' }}>
              <label className="form-label">Exam</label>
              <select className="form-control" value={selectedExam} onChange={e => { setSelectedExam(e.target.value); setSelectedClass(''); }}>
                <option value="">-- Select Exam --</option>
                {exams.map(e => <option key={e.examId} value={e.examId}>{e.name}</option>)}
              </select>
            </div>
            
            {activeExam && (
              <>
                <div className="form-group" style={{ flex: 1, minWidth: '150px' }}>
                  <label className="form-label">Class</label>
                  <select className="form-control" value={selectedClass} onChange={e => setSelectedClass(e.target.value)}>
                    <option value="">All Classes</option>
                    {activeExam.classes?.map(c => <option key={c} value={c}>Class {c}</option>)}
                  </select>
                </div>

                <div className="form-group" style={{ flex: 1, minWidth: '150px' }}>
                  <label className="form-label">Paper Set</label>
                  <select className="form-control" value={selectedSet} onChange={e => setSelectedSet(e.target.value)}>
                    <option value="">All Sets</option>
                    {['A', 'B', 'C', 'D'].map(s => <option key={s} value={s}>Set {s}</option>)}
                  </select>
                </div>
              </>
            )}
          </div>
        </div>

        {selectedExam && (
          <>
            {sortedResults.length > 0 && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                <div className="card" style={{ textAlign: 'center' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Total Processed</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>{sortedResults.length}</div>
                </div>
                <div className="card" style={{ textAlign: 'center' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Average Score</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>{(sortedResults.reduce((acc, r) => acc + (r.total_score ?? r.score ?? 0), 0) / sortedResults.length).toFixed(2)}</div>
                </div>
                <div className="card" style={{ textAlign: 'center' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Highest Score</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#166534' }}>{Math.max(...sortedResults.map(r => r.total_score ?? r.score ?? 0)).toFixed(2)}</div>
                </div>
                <div className="card" style={{ textAlign: 'center' }}>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Lowest Score</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#991b1b' }}>{Math.min(...sortedResults.map(r => r.total_score ?? r.score ?? 0)).toFixed(2)}</div>
                </div>
              </div>
            )}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0 }}>Leaderboard ({sortedResults.length})</h3>
              <button className="btn btn-outline" style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }} onClick={fetchResults}>
                🔄 Refresh Leaderboard
              </button>
            </div>
            <div style={{ overflowX: 'auto', marginTop: '1rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '0.75rem 0' }}>Rank</th>
                    <th style={{ padding: '0.75rem 0' }}>Student Name</th>
                    <th style={{ padding: '0.75rem 0' }}>Reg. Number</th>
                    <th style={{ padding: '0.75rem 0' }}>Class</th>
                    <th style={{ padding: '0.75rem 0' }}>Set</th>
                    <th style={{ padding: '0.75rem 0' }}>Correct</th>
                    <th style={{ padding: '0.75rem 0' }}>Wrong</th>
                    <th style={{ padding: '0.75rem 0' }}>Unanswered</th>
                    <th style={{ padding: '0.75rem 0' }}>Ambiguous</th>
                    <th style={{ padding: '0.75rem 0' }}>Score</th>
                    <th style={{ padding: '0.75rem 0' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedResults.length === 0 && !loading ? (
                    <tr><td colSpan={11} style={{ padding: '2rem 0', textAlign: 'center', color: 'var(--text-secondary)' }}>No results found. Scan and evaluate sheets first.</td></tr>
                  ) : (
                    sortedResults.map((r, idx) => (
                      <tr key={r.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '1rem 0', fontWeight: 700, color: idx < 3 ? 'var(--primary-color)' : 'inherit' }}>
                          #{idx + 1}
                        </td>
                        <td style={{ padding: '1rem 0', fontWeight: 600 }}>
                          {r.studentName || r.student_name || `Student ${idx + 1}`}
                        </td>
                        <td style={{ padding: '1rem 0', fontWeight: 500 }}>{r.registrationNumber || r.registration_number || '-'}</td>
                        <td style={{ padding: '1rem 0' }}>{r.class || r.class_id || '-'}</td>
                        <td style={{ padding: '1rem 0' }}>{r.paperSet || r.paper_set || '-'}</td>
                        <td style={{ padding: '1rem 0', color: '#166534' }}>{r.correct_count ?? 0}</td>
                        <td style={{ padding: '1rem 0', color: '#991b1b' }}>{r.wrong_count ?? 0}</td>
                        <td style={{ padding: '1rem 0', color: '#64748b' }}>{r.unanswered_count ?? 0}</td>
                        <td style={{ padding: '1rem 0', color: '#b45309' }}>{r.ambiguous_count ?? 0}</td>
                        <td style={{ padding: '1rem 0', fontWeight: 700, color: 'var(--primary-color)' }}>{(r.total_score ?? r.score ?? 0).toFixed(2)}</td>
                        <td style={{ padding: '1rem 0' }}>
                          <button 
                            className="btn btn-outline" 
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                            onClick={() => setSelectedDetail(r)}
                          >
                            Inspect Answers
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
          </>
        )}

        {selectedDetail && (
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
            <div className="card" style={{ width: '90%', maxWidth: '700px', maxHeight: '90vh', overflowY: 'auto' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
                <div>
                  <h3 style={{ margin: 0 }}>Student Answer Breakdown</h3>
                  <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                    {selectedDetail.registrationNumber} | Class {selectedDetail.class} | Set {selectedDetail.paperSet} | Score: {(selectedDetail.total_score || 0).toFixed(2)}
                  </div>
                </div>
                <button onClick={() => setSelectedDetail(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.5rem' }}>&times;</button>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '0.75rem' }}>
                {selectedDetail.details ? (
                  Object.entries(selectedDetail.details).map(([q, d]: [string, any]) => (
                    <div key={q} style={{ 
                      border: '1px solid var(--border-color)', 
                      padding: '0.5rem', 
                      borderRadius: '6px',
                      backgroundColor: d.status === 'CORRECT' ? '#f0fdf4' : (d.status === 'WRONG' || d.status?.includes('INVALID') ? '#fef2f2' : '#f8fafc')
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, fontSize: '0.8rem' }}>
                        <span>Q{q}</span>
                        <span style={{ 
                          color: d.status === 'CORRECT' ? '#166534' : (d.status === 'WRONG' || d.status?.includes('INVALID') ? '#991b1b' : '#64748b'),
                          fontSize: '0.7rem'
                        }}>
                          {d.status}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.75rem', marginTop: '0.25rem', color: 'var(--text-secondary)' }}>
                        Ans: <strong>{d.student_ans || '-'}</strong> | Key: <strong>{d.correct_ans || '-'}</strong>
                      </div>
                    </div>
                  ))
                ) : (
                  <p style={{ color: 'var(--text-secondary)' }}>No question-level details available for this record.</p>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem', borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                <button className="btn btn-primary" onClick={() => setSelectedDetail(null)}>Close</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default ResultsDashboard;
