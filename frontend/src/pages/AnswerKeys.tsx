import React, { useState, useEffect } from 'react';
import { collection, getDocs, doc, setDoc, getDoc } from 'firebase/firestore';
import { db } from '../firebase';
import type { Exam } from '../types';

const AnswerKeys: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedExam, setSelectedExam] = useState('');
  const [selectedClass, setSelectedClass] = useState('');
  const [selectedSet, setSelectedSet] = useState('A');
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [keys, setKeys] = useState<Record<number, string>>({});
  const [keyStatus, setKeyStatus] = useState<'DRAFT' | 'PUBLISHED'>('DRAFT');
  const [isTestKey, setIsTestKey] = useState(false);
  const [message, setMessage] = useState('');
  
  useEffect(() => {
    const fetchExams = async () => {
      const snap = await getDocs(collection(db, 'exams'));
      setExams(snap.docs.map(d => ({ ...d.data(), examId: d.id } as Exam)));
      setLoading(false);
    };
    fetchExams();
  }, []);
  
  const loadKeys = async (examId: string, cls: string, set: string) => {
    setMessage('');
    try {
      const docRef = doc(db, 'answerKeys', `${examId}_${cls}_${set}`);
      const docSnap = await getDoc(docRef);
      if (docSnap.exists()) {
        const data = docSnap.data();
        setKeys(data.keys || {});
        setKeyStatus(data.status || 'DRAFT');
      } else {
        setKeys({});
        setKeyStatus('DRAFT');
      }
    } catch (err: any) {
      console.error(err);
      setMessage(err.message);
    }
  };
  
  useEffect(() => {
    if (selectedExam && selectedClass && selectedSet) {
      loadKeys(selectedExam, selectedClass, selectedSet);
    }
  }, [selectedExam, selectedClass, selectedSet]);

  const activeExam = exams.find(e => e.examId === selectedExam);
  
  const handleOptionSelect = (q: number, opt: string) => {
    if (keyStatus === 'PUBLISHED') return;
    setKeys(prev => ({
      ...prev,
      [q]: prev[q] === opt ? '' : opt
    }));
  };

  const [uploadStats, setUploadStats] = useState<any>(null);
  const [uploading, setUploading] = useState(false);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedExam || !selectedClass || !selectedSet) return;
    setUploading(true);
    setMessage('');
    setUploadStats(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('exam_id', selectedExam);
    formData.append('class_id', selectedClass);
    formData.append('paper_set', selectedSet);
    formData.append('is_test_data', 'true');

    try {
      const res = await fetch('http://localhost:8000/api/answer-keys/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok || !data.valid) {
        throw new Error(data.errors?.join(' | ') || data.detail || 'Upload failed');
      }

      setKeys(data.keys);
      setIsTestKey(true);
      setUploadStats(data.timings);
      setMessage(`Successfully imported 50 answers from ${file.name} (TEST DATA / NOT OFFICIAL). Total time: ${data.timings.total_time_s}s`);
    } catch (err: any) {
      setMessage(`Upload error: ${err.message}`);
    } finally {
      setUploading(false);
      // Reset input
      e.target.value = '';
    }
  };

  const handleLoadTestData = () => {
    if (keyStatus === 'PUBLISHED') return;
    const testKeys: Record<number, string> = {};
    const pattern = ['A', 'B', 'C', 'D'];
    for (let i = 1; i <= 50; i++) {
      testKeys[i] = pattern[(i - 1) % 4];
    }
    setKeys(testKeys);
    setIsTestKey(true);
    setMessage('Loaded 50-Question TEST DATA pattern. Explicitly marked for test evaluation verification.');
  };

  const handleCreateNewRevision = () => {
    setKeyStatus('DRAFT');
    setMessage('Answer key unlocked for new draft revision.');
  };

  const handleSave = async (status: 'DRAFT' | 'PUBLISHED') => {
    if (!selectedExam || !selectedClass || !selectedSet) return;

    if (status === 'PUBLISHED') {
      const filled = Object.entries(keys).filter(([_, v]) => Boolean(v)).length;
      if (filled < 50) {
        setMessage(`Cannot publish: all 50 questions must have answer keys (currently ${filled}/50). Save Draft instead.`);
        return;
      }
    }

    setSaving(true);
    setMessage('');
    try {
      const docId = `${selectedExam}_${selectedClass}_${selectedSet}`;
      await setDoc(doc(db, 'answerKeys', docId), {
        examId: selectedExam,
        class: selectedClass,
        paperSet: selectedSet,
        keys,
        status,
        isTestData: isTestKey,
        label: isTestKey ? "TEST DATA / NOT OFFICIAL" : "OFFICIAL",
        updatedAt: new Date().toISOString()
      });
      setKeyStatus(status);
      setMessage(`Answer key saved as ${status}${isTestKey ? ' (TEST DATA / NOT OFFICIAL)' : ''}`);
    } catch (err: any) {
      setMessage(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <>
      <header className="page-header">
        <h2>Answer Keys</h2>
      </header>
      <div className="page-body">
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <div className="form-group" style={{ flex: 1, minWidth: '200px' }}>
              <label className="form-label">Exam</label>
              <select className="form-control" value={selectedExam} onChange={e => { setSelectedExam(e.target.value); setSelectedClass(''); }}>
                <option value="">-- Select Exam --</option>
                {exams.map(e => <option key={e.examId} value={e.examId}>{e.name} ({e.examId})</option>)}
              </select>
            </div>
            
            {activeExam && (
              <>
                <div className="form-group" style={{ flex: 1, minWidth: '150px' }}>
                  <label className="form-label">Class</label>
                  <select className="form-control" value={selectedClass} onChange={e => setSelectedClass(e.target.value)}>
                    <option value="">-- Select --</option>
                    {activeExam.classes?.map(c => <option key={c} value={c}>Class {c}</option>)}
                  </select>
                </div>
                
                <div className="form-group" style={{ flex: 1, minWidth: '150px' }}>
                  <label className="form-label">Paper Set</label>
                  <select className="form-control" value={selectedSet} onChange={e => setSelectedSet(e.target.value)}>
                    {['A', 'B', 'C', 'D'].map(s => <option key={s} value={s}>Set {s}</option>)}
                  </select>
                </div>
              </>
            )}
          </div>
        </div>

        {message && <div style={{ padding: '1rem', background: '#dcfce7', color: '#166534', borderRadius: '8px', marginBottom: '1rem' }}>{message}</div>}

        {selectedExam && selectedClass && selectedSet && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <h3 style={{ margin: 0 }}>Enter Answers (Set {selectedSet})</h3>
                <span style={{
                  padding: '0.25rem 0.5rem',
                  borderRadius: '9999px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  backgroundColor: keyStatus === 'PUBLISHED' ? '#dcfce7' : '#fef3c7',
                  color: keyStatus === 'PUBLISHED' ? '#166534' : '#b45309'
                }}>
                  {keyStatus === 'PUBLISHED' ? '✓ PUBLISHED & IMMUTABLE' : 'DRAFT'}
                </span>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                  ({Object.values(keys).filter(Boolean).length}/50 filled)
                </span>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                <input 
                  type="file" 
                  accept=".csv,.json" 
                  id="key-file-upload" 
                  style={{ display: 'none' }} 
                  onChange={handleFileUpload} 
                  disabled={keyStatus === 'PUBLISHED' || uploading}
                />
                {keyStatus !== 'PUBLISHED' && (
                  <>
                    <label htmlFor="key-file-upload" className="btn btn-outline" style={{ fontSize: '0.8rem', cursor: 'pointer', margin: 0 }}>
                      {uploading ? 'Uploading...' : '📁 Upload Key File (CSV/JSON)'}
                    </label>
                    <button className="btn btn-outline" onClick={handleLoadTestData} disabled={saving} style={{ fontSize: '0.8rem' }}>
                      Load Test Key (TEST DATA)
                    </button>
                    <button className="btn btn-outline" onClick={() => handleSave('DRAFT')} disabled={saving}>Save Draft</button>
                    <button className="btn btn-primary" onClick={() => handleSave('PUBLISHED')} disabled={saving}>Publish Key</button>
                  </>
                )}
                {keyStatus === 'PUBLISHED' && (
                  <button className="btn btn-outline" onClick={handleCreateNewRevision}>Create New Revision</button>
                )}
              </div>
            </div>

            {uploadStats && (
              <div style={{ padding: '0.75rem 1rem', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', marginBottom: '1.25rem', fontSize: '0.8rem' }}>
                <strong style={{ color: 'var(--primary-color)' }}>⏱ Upload & Mapping Performance Measurements:</strong>
                <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                  <div>File Upload: <strong>{uploadStats.upload_time_s}s</strong></div>
                  <div>Parsing: <strong>{uploadStats.parse_time_s}s</strong></div>
                  <div>Q1–Q50 Mapping: <strong>{uploadStats.mapping_time_s}s</strong></div>
                  <div>Validation: <strong>{uploadStats.validation_time_s}s</strong></div>
                  <div>Total Time: <strong style={{ color: '#166534' }}>{uploadStats.total_time_s}s</strong></div>
                </div>
              </div>
            )}
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: '1rem' }}>
              {Array.from({ length: 50 }, (_, i) => i + 1).map(q => (
                <div key={q} style={{ border: '1px solid var(--border-color)', padding: '0.5rem', borderRadius: '4px', textAlign: 'center' }}>
                  <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Q{q}</div>
                  <div style={{ display: 'flex', gap: '0.25rem', justifyContent: 'center' }}>
                    {['A', 'B', 'C', 'D'].map(opt => (
                      <button
                        key={opt}
                        onClick={() => handleOptionSelect(q, opt)}
                        style={{
                          width: '24px', height: '24px', borderRadius: '50%', border: '1px solid var(--primary-color)',
                          background: keys[q] === opt ? 'var(--primary-color)' : 'transparent',
                          color: keys[q] === opt ? 'white' : 'var(--primary-color)',
                          cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px'
                        }}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default AnswerKeys;
