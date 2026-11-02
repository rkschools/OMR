import React, { useState, useEffect } from 'react';
import { collection, getDocs, onSnapshot, query, orderBy, limit, where, getDoc, doc, setDoc, serverTimestamp } from 'firebase/firestore';
import { db, auth } from '../firebase';
import type { Exam } from '../types';

interface ScanJob {
  id: string;
  file?: File;
  fileName?: string;
  status: 'pending' | 'processing' | 'success' | 'failed' | 'review_required';
  progress: number;
  result?: any;
  error?: string;
}

const ScannerWorkspace: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedExam, setSelectedExam] = useState('');
  const [selectedClass, setSelectedClass] = useState('');
  const [jobs, setJobs] = useState<ScanJob[]>([]);
  const [networkJobs, setNetworkJobs] = useState<ScanJob[]>([]);
  
  useEffect(() => {
    const fetchExams = async () => {
      const snap = await getDocs(collection(db, 'exams'));
      setExams(snap.docs.map(d => ({ ...d.data(), examId: d.id } as Exam)));
    };
    fetchExams();
  }, []);

  useEffect(() => {
    if (!selectedExam || !selectedClass || !auth.currentUser) return;
    
    // Listen for recent network ingestion jobs for this exam/class
    const classVariants = [selectedClass, `class_${selectedClass}`, selectedClass.replace('class_', '')];
    const q = query(
      collection(db, 'scanSheets'),
      where('examId', '==', selectedExam),
      where('classId', 'in', Array.from(new Set(classVariants))),
      orderBy('timestamp', 'desc'),
      limit(50)
    );

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const nwJobs: ScanJob[] = snapshot.docs.map(doc => {
        const data = doc.data();
        return {
          id: doc.id,
          fileName: data.fileName || 'Network Scan',
          status: data.status === 'VALID' ? 'success' : (data.status === 'REVIEW_REQUIRED' ? 'review_required' : 'failed'),
          progress: 100,
          result: data.answers
        };
      });
      setNetworkJobs(nwJobs);
    }, (error) => {
      console.warn("scanSheets onSnapshot:", error.message);
    });

    return () => unsubscribe();
  }, [selectedExam, selectedClass]);

  const activeExam = exams.find(e => e.examId === selectedExam);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const newJobs: ScanJob[] = Array.from(e.target.files).map((f, i) => ({
      id: `${Date.now()}_${i}`,
      file: f,
      status: 'pending',
      progress: 0
    }));
    setJobs(prev => [...prev, ...newJobs]);
  };

  const processQueue = async () => {
    if (!selectedExam || !selectedClass) {
      alert('Please select Exam and Class first');
      return;
    }

    const pendingJobs = jobs.filter(j => j.status === 'pending');
    if (pendingJobs.length === 0) return;

    // Fetch the template config for the given exam
    const examDoc = await getDoc(doc(db, 'exams', selectedExam));
    let templateId = examDoc.data()?.templateId;
    let currentVersionId = examDoc.data()?.templateVersionId;
    if (!templateId) templateId = `template_${selectedExam}`;

    const templateDoc = await getDoc(doc(db, 'templates', templateId));
    if (!templateDoc.exists()) {
      alert("Template not found for this exam.");
      return;
    }
    if (!currentVersionId) {
      currentVersionId = templateDoc.data().currentVersion;
    }

    let configStr = '';
    try {
      const vDoc = await getDoc(doc(db, `templates/${templateId}/versions`, currentVersionId));
      if (!vDoc.exists()) throw new Error("No config version found");
      const vData = vDoc.data();
      
      // Override with class specific sections if they exist
      const config = vData.configuration;
      if (config.classesConfig && config.classesConfig[selectedClass]) {
        config.sections = config.classesConfig[selectedClass].sections;
      }
      configStr = JSON.stringify(config);
    } catch(err) {
      alert("Error loading template config");
      return;
    }

    const token = await auth.currentUser?.getIdToken();

    // Process sequentially for simplicity, could be parallelized
    for (const job of pendingJobs) {
      setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status: 'processing', progress: 50 } : j));
      
      const formData = new FormData();
      formData.append('file', job.file);
      formData.append('template_config', configStr);

      try {
        const res = await fetch('http://localhost:8000/api/scan', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        });
        const data = await res.json();
        
        if (res.ok) {
          // Check if review is required (e.g. low confidence or ambiguous)
          const hasAmbiguous = Object.values(data.answers).some((a: any) => a.classification === 'AMBIGUOUS' || a.classification === 'MULTIPLE / INVALID');
          
          setJobs(prev => prev.map(j => j.id === job.id ? { 
            ...j, 
            status: hasAmbiguous ? 'review_required' : 'success', 
            progress: 100, 
            result: data.answers 
          } : j));
        } else {
          throw new Error(data.detail || 'Scan failed');
        }
      } catch (err: any) {
        setJobs(prev => prev.map(j => j.id === job.id ? { ...j, status: 'failed', progress: 100, error: err.message } : j));
      }
    }
  };

  const startNetworkIngestion = async () => {
    if (!selectedExam || !selectedClass) {
      alert('Please select Exam and Class first');
      return;
    }

    const examDoc = await getDoc(doc(db, 'exams', selectedExam));
    let templateId = examDoc.data()?.templateId;
    let currentVersionId = examDoc.data()?.templateVersionId;
    
    if (!templateId) templateId = `template_${selectedExam}`;
    
    const templateDoc = await getDoc(doc(db, 'templates', templateId));
    if (!templateDoc.exists()) {
      alert("Template not found for this exam.");
      return;
    }
    if (!currentVersionId) currentVersionId = templateDoc.data().currentVersion;
    
    let configStr = '';
    try {
      const vDoc = await getDoc(doc(db, `templates/${templateId}/versions`, currentVersionId));
      const vData = vDoc.data();
      if (!vData) throw new Error("No config found");
      
      const config = vData.configuration;
      if (config.classesConfig && config.classesConfig[selectedClass]) {
        config.sections = config.classesConfig[selectedClass].sections;
      }
      configStr = JSON.stringify(config);
    } catch(err) {
      alert("Error loading template config");
      return;
    }

    const token = await auth.currentUser?.getIdToken();

    try {
      const res = await fetch('http://localhost:8000/api/scanner/batch/active', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          batchId: `BATCH_${Date.now()}`,
          examId: selectedExam,
          classId: selectedClass,
          paperSet: 'A', // Or from a dropdown
          templateId: activeExam?.templateId || '',
          templateVersionId: activeExam?.templateVersionId || '',
          template_config: JSON.parse(configStr)
        })
      });
      if (res.ok) {
        alert("Network Ingestion is now ACTIVE for this configuration. Send scans from Ricoh to the Inbox folder.");
      } else {
        alert("Failed to activate network ingestion");
      }
    } catch (err) {
      alert("Error connecting to local ingestion service");
    }
  };

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'success': return '#166534';
      case 'failed': return '#991b1b';
      case 'review_required': return '#b45309';
      case 'processing': return '#1d4ed8';
      default: return '#4b5563';
    }
  };

  const getStatusBg = (status: string) => {
    switch(status) {
      case 'success': return '#dcfce7';
      case 'failed': return '#fee2e2';
      case 'review_required': return '#fef3c7';
      case 'processing': return '#dbeafe';
      default: return '#f3f4f6';
    }
  };

  const [evaluating, setEvaluating] = useState(false);

  const evaluateQueue = async () => {
    const allSuccessJobs = [...jobs, ...networkJobs].filter(j => j.status === 'success' && !j.result?.evaluated);
    if (allSuccessJobs.length === 0) return;

    setEvaluating(true);
    const token = await auth.currentUser?.getIdToken();

    // Fetch config
    let configStr = '';
    try {
      if (!activeExam?.templateId || !activeExam?.templateVersionId) throw new Error("No linked template on Exam");
      const vDoc = await getDoc(doc(db, `templates/${activeExam.templateId}/versions`, activeExam.templateVersionId));
      if (!vDoc.exists()) throw new Error("No config found");
      const config = vDoc.data().configuration;
      if (config.classesConfig && config.classesConfig[selectedClass]) {
        config.sections = config.classesConfig[selectedClass].sections;
      }
      configStr = JSON.stringify(config);
    } catch(err) {
      alert("Error loading template config");
      setEvaluating(false);
      return;
    }

    // Fetch Answer Key
    let keySnapDocs: any[] = [];
    try {
      const keySnap = await getDocs(collection(db, 'answerKeys'));
      keySnapDocs = keySnap.docs;
    } catch(err) {
      alert("Error loading answer keys");
      setEvaluating(false);
      return;
    }

    // Evaluate each job
    for (const job of allSuccessJobs) {
      try {
        const jobPaperSet = job.result?.paperSet || 'A';
        const keyMatch = keySnapDocs.find(d => d.id === `${selectedExam}_${selectedClass}_${jobPaperSet}`) ||
                         keySnapDocs.find(d => d.id === `${selectedExam}_${selectedClass}_A`);
        const setAnswerKey = keyMatch ? keyMatch.data().keys : {};

        const res = await fetch('http://localhost:8000/api/evaluate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            extracted_answers: job.result,
            answer_key: setAnswerKey,
            template_config: JSON.parse(configStr)
          })
        });
        const data = await res.json();
        
        if (res.ok) {
          // Idempotent deterministic result ID
          const resultId = `res_${selectedExam}_${selectedClass}_${job.id}`;
          const regNo = job.result?.registration_number || `REG-${job.id.substring(0, 6)}`;
          const templateId = activeExam?.templateId || `template_${selectedExam}`;
          const currentVersionId = activeExam?.templateVersionId || 'v1.0.0';
          const studentName = job.result?.student_name || job.result?.name || (job.fileName && !job.fileName.startsWith('scan_') ? job.fileName.replace(/\.[^/.]+$/, '').replace(/_/g, ' ') : `Student ${regNo}`);
          await setDoc(doc(db, 'results', resultId), {
            id: resultId,
            examId: selectedExam,
            exam_id: selectedExam,
            class: selectedClass,
            class_id: selectedClass,
            templateId: templateId,
            template_id: templateId,
            templateVersionId: currentVersionId,
            template_version_id: currentVersionId,
            paperSet: jobPaperSet,
            paper_set: jobPaperSet,
            studentName: studentName,
            student_name: studentName,
            registrationNumber: regNo,
            registration_number: regNo,
            score: data.results?.total_score ?? 0,
            total_score: data.results?.total_score ?? 0,
            answers: job.result,
            evaluation: data.results,
            ...data.results,
            createdAt: serverTimestamp(),
            updatedAt: serverTimestamp()
          }, { merge: true });

          setJobs(prev => prev.map(j => j.id === job.id ? { 
            ...j, 
            result: { ...j.result, evaluated: true, score: data.results.total_score } 
          } : j));
          setNetworkJobs(prev => prev.map(j => j.id === job.id ? { 
            ...j, 
            result: { ...j.result, evaluated: true, score: data.results.total_score } 
          } : j));
        }
      } catch (err) {
        console.error(err);
      }
    }
    setEvaluating(false);
  };

  const [reviewingJob, setReviewingJob] = useState<ScanJob | null>(null);

  const handleReviewSave = async (jobId: string, updatedResult: any) => {
    try {
      await setDoc(doc(db, 'scanSheets', jobId), {
        answers: updatedResult,
        status: 'VALID',
        reviewedAt: serverTimestamp()
      }, { merge: true });
    } catch (e) {
      console.warn("Could not sync scanSheets:", e);
    }

    setJobs(prev => prev.map(j => j.id === jobId ? {
      ...j,
      status: 'success',
      result: updatedResult
    } : j));
    setNetworkJobs(prev => prev.map(j => j.id === jobId ? {
      ...j,
      status: 'success',
      result: updatedResult
    } : j));
    setReviewingJob(null);
  };

  const ReviewModal = ({ job, onClose, onSave }: { job: ScanJob, onClose: () => void, onSave: (id: string, result: any) => void }) => {
    const [localResult, setLocalResult] = useState<any>(JSON.parse(JSON.stringify(job.result || {})));
    const [regNum, setRegNum] = useState<string>(job.result?.registration_number || '');

    const ambiguousQuestions = Object.keys(localResult).filter(q => {
      if (q.startsWith('REG_') || q === 'registration_number' || q === 'paperSet' || q === 'evaluated' || q === 'score') return false;
      const item = localResult[q];
      if (!item) return false;
      if (typeof item === 'object') {
        return item.classification === 'AMBIGUOUS' || item.classification === 'MULTIPLE / INVALID' || item.classification === 'MULTIPLE';
      }
      return item === 'AMBIGUOUS' || item === 'MULTIPLE';
    });

    const handleOption = (q: string, opt: string) => {
      setLocalResult((prev: any) => ({
        ...prev,
        [q]: typeof prev[q] === 'object' ? {
          ...prev[q],
          extracted: opt,
          classification: opt === 'BLANK' ? 'BLANK' : 'VALID'
        } : {
          extracted: opt,
          classification: opt === 'BLANK' ? 'BLANK' : 'VALID'
        }
      }));
    };

    const handleSave = () => {
      onSave(job.id, {
        ...localResult,
        registration_number: regNum
      });
    };

    return (
      <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
        <div className="card" style={{ width: '90%', maxWidth: '600px', maxHeight: '90vh', overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h3>Manual Review: {job.file?.name || job.fileName || 'Scan Sheet'}</h3>
            <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.5rem' }}>&times;</button>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Registration Number</label>
            <input 
              type="text" 
              className="input-field" 
              value={regNum} 
              onChange={e => setRegNum(e.target.value)} 
              placeholder="e.g. 102456"
              style={{ width: '100%', marginBottom: '1rem' }}
            />

            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>Please manually resolve the following ambiguous detections:</p>
            {ambiguousQuestions.length === 0 ? (
              <p style={{ color: '#166534', fontWeight: 600 }}>All ambiguous question marks resolved!</p>
            ) : (
              ambiguousQuestions.map(q => {
                const item = localResult[q];
                const classification = typeof item === 'object' ? item.classification : item;
                const extracted = typeof item === 'object' ? item.extracted : item;
                return (
                  <div key={q} style={{ border: '1px solid var(--border-color)', padding: '1rem', borderRadius: '8px', marginBottom: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                      <strong>Question {q}</strong>
                      <span style={{ color: '#b45309', fontSize: '0.875rem' }}>{classification}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      {['A', 'B', 'C', 'D', 'BLANK'].map(opt => (
                        <button 
                          key={opt}
                          onClick={() => handleOption(q, opt)}
                          className={`btn ${extracted === opt ? 'btn-primary' : 'btn-outline'}`}
                          style={{ padding: '0.5rem', flex: 1 }}
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
            <button className="btn btn-outline" onClick={onClose}>Cancel</button>
            <button 
              className="btn btn-primary" 
              disabled={ambiguousQuestions.length > 0} 
              onClick={handleSave}
            >
              Save Corrections
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <>
      {reviewingJob && <ReviewModal job={reviewingJob} onClose={() => setReviewingJob(null)} onSave={handleReviewSave} />}
      <header className="page-header">
        <h2>Scanner Workspace</h2>
      </header>
      
      <div className="page-body">
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <div className="form-group" style={{ flex: 1, minWidth: '200px' }}>
              <label className="form-label">Exam Target</label>
              <select className="form-control" value={selectedExam} onChange={e => { setSelectedExam(e.target.value); setSelectedClass(''); }}>
                <option value="">-- Select Exam --</option>
                {exams.map(e => <option key={e.examId} value={e.examId}>{e.name}</option>)}
              </select>
            </div>
            
            {activeExam && (
              <div className="form-group" style={{ flex: 1, minWidth: '150px' }}>
                <label className="form-label">Class</label>
                <select className="form-control" value={selectedClass} onChange={e => setSelectedClass(e.target.value)}>
                  <option value="">-- Select Class --</option>
                  {activeExam.classes?.map(c => <option key={c} value={c}>Class {c}</option>)}
                </select>
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1.5rem', marginBottom: '1.5rem' }}>
          <div className="card" style={{ flex: 1, border: '2px solid var(--primary-color)', textAlign: 'center', padding: '3rem' }}>
            <h3 style={{ color: 'var(--primary-color)' }}>RICOH Network Ingestion</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>Automatically ingest scans from network folder</p>
            <button 
              className="btn btn-primary" 
              onClick={startNetworkIngestion}
              disabled={!selectedExam || !selectedClass}
              style={{ width: '100%', maxWidth: '250px' }}
            >
              Start Auto-Ingestion
            </button>
            <p style={{ marginTop: '1rem', fontSize: '0.8rem', color: '#6b7280' }}>
              Drop files in: <code>OMR_SCAN/inbox/</code>
            </p>
          </div>

          <div className="card" style={{ flex: 1, border: '2px dashed var(--border-color)', textAlign: 'center', padding: '3rem' }}>
            <h3>Manual Upload (Fallback)</h3>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>Upload JPG, PNG, PDF directly</p>
            <input 
              type="file" 
              multiple 
              accept="image/*,application/pdf"
              onChange={handleFileUpload}
              style={{ display: 'none' }} 
              id="file-upload" 
            />
            <label htmlFor="file-upload" className="btn btn-accent" style={{ cursor: 'pointer', display: 'inline-block', width: '100%', maxWidth: '250px' }}>
              Select Files
            </label>
          </div>
        </div>

        {([...jobs, ...networkJobs].length > 0) && (
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3>Scan Queue ({[...jobs, ...networkJobs].length})</h3>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button 
                  className="btn btn-accent" 
                  onClick={processQueue} 
                  disabled={!selectedExam || !selectedClass || jobs.filter(j => j.status === 'pending').length === 0}
                >
                  Process Pending
                </button>
                <button
                  className="btn btn-primary"
                  onClick={evaluateQueue}
                  disabled={evaluating || [...jobs, ...networkJobs].filter(j => j.status === 'success' && !j.result?.evaluated).length === 0}
                >
                  {evaluating ? 'Evaluating...' : 'Evaluate Processed'}
                </button>
              </div>
            </div>
            
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '0.75rem 0' }}>Filename</th>
                  <th style={{ padding: '0.75rem 0' }}>Status</th>
                  <th style={{ padding: '0.75rem 0' }}>Details</th>
                  <th style={{ padding: '0.75rem 0' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {[...jobs, ...networkJobs].map(job => (
                  <tr key={job.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '1rem 0', fontWeight: 500 }}>{job.file?.name || job.fileName}</td>
                    <td style={{ padding: '1rem 0' }}>
                      <span style={{ 
                        padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600,
                        backgroundColor: getStatusBg(job.status), color: getStatusColor(job.status)
                      }}>
                        {job.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '1rem 0', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                      {job.error ? job.error : job.result ? (
                        job.result.evaluated 
                          ? <span style={{ color: '#166534', fontWeight: 600 }}>Score: {job.result.score.toFixed(2)}</span>
                          : `Detected: ${Object.keys(job.result).length} fields`
                      ) : '-'}
                    </td>
                    <td style={{ padding: '1rem 0' }}>
                      {job.status === 'review_required' && (
                        <button className="btn btn-outline" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }} onClick={() => setReviewingJob(job)}>Review</button>
                      )}
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

export default ScannerWorkspace;
