import React, { useState } from 'react';
import { doc, setDoc, serverTimestamp } from 'firebase/firestore';
import { db } from '../firebase';
import { useNavigate } from 'react-router-dom';

const CreateExam: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    examId: '',
    year: new Date().getFullYear().toString(),
    description: '',
    status: 'DRAFT',
  });
  const [classes, setClasses] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleClassToggle = (cls: string) => {
    if (classes.includes(cls)) {
      setClasses(classes.filter(c => c !== cls));
    } else {
      setClasses([...classes, cls].sort((a, b) => parseInt(a) - parseInt(b)));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!formData.name || !formData.examId) {
      setError('Name and Exam ID are required.');
      return;
    }
    if (classes.length === 0) {
      setError('At least one class must be selected.');
      return;
    }

    setLoading(true);
    try {
      const examRef = doc(db, 'exams', formData.examId);
      await setDoc(examRef, {
        ...formData,
        classes,
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp()
      });
      navigate(`/exams/${formData.examId}`);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to create exam');
      setLoading(false);
    }
  };

  return (
    <>
      <header className="page-header">
        <h2>Create Exam</h2>
      </header>
      <div className="page-body">
        <form onSubmit={handleSubmit} className="card" style={{ maxWidth: '600px' }}>
          {error && <div style={{ color: 'red', marginBottom: '1rem', padding: '0.5rem', backgroundColor: '#fee2e2', borderRadius: '4px' }}>{error}</div>}
          
          <div className="form-group">
            <label className="form-label">Exam Name *</label>
            <input type="text" className="form-control" required value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} placeholder="e.g. RISE 2027" />
          </div>
          
          <div className="form-group">
            <label className="form-label">Exam ID *</label>
            <input type="text" className="form-control" required value={formData.examId} onChange={e => setFormData({...formData, examId: e.target.value})} placeholder="e.g. exam_rise_2027" />
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label className="form-label">Year *</label>
              <input type="text" className="form-control" required value={formData.year} onChange={e => setFormData({...formData, year: e.target.value})} />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label className="form-label">Status</label>
              <select className="form-control" value={formData.status} onChange={e => setFormData({...formData, status: e.target.value})}>
                <option value="DRAFT">Draft</option>
                <option value="ACTIVE">Active</option>
                <option value="ARCHIVED">Archived</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea className="form-control" rows={3} value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})}></textarea>
          </div>

          <div className="form-group">
            <label className="form-label">Classes *</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {['1','2','3','4','5','6','7','8','9','10'].map(cls => (
                <button 
                  type="button" 
                  key={cls}
                  onClick={() => handleClassToggle(cls)}
                  className={`btn ${classes.includes(cls) ? 'btn-primary' : 'btn-outline'}`}
                  style={{ minWidth: '40px', padding: '0.25rem 0.5rem' }}
                >
                  {cls}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? 'Creating...' : 'Create Exam'}
            </button>
            <button type="button" className="btn btn-outline" onClick={() => navigate('/exams')}>Cancel</button>
          </div>
        </form>
      </div>
    </>
  );
};

export default CreateExam;
