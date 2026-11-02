import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { doc, getDoc, setDoc, serverTimestamp, collection, getDocs } from 'firebase/firestore';
import { db, auth } from '../firebase';
import type { Template, TemplateVersion } from '../types';

const TemplateWorkspace: React.FC = () => {
  const { templateId } = useParams();
  const [template, setTemplate] = useState<Template | null>(null);
  const [activeVersion, setActiveVersion] = useState<TemplateVersion | null>(null);
  const [allVersions, setAllVersions] = useState<TemplateVersion[]>([]);
  const [configDraft, setConfigDraft] = useState<any>(null);
  
  const [activeTab, setActiveTab] = useState<'overview' | 'designer' | 'preview' | 'versions'>('overview');
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const fetchTemplate = async () => {
      try {
        if (!templateId) return;
        const tDoc = await getDoc(doc(db, 'templates', templateId));
        if (tDoc.exists()) {
          const tData = tDoc.data() as Template;
          setTemplate(tData);
          
          // Fetch all versions
          const versionsSnap = await getDocs(collection(db, `templates/${templateId}/versions`));
          const versionsList = versionsSnap.docs.map(d => d.data() as TemplateVersion).sort((a, b) => b.version.localeCompare(a.version));
          setAllVersions(versionsList);
          
          if (tData.currentVersion) {
            const vDoc = await getDoc(doc(db, `templates/${templateId}/versions`, tData.currentVersion));
            if (vDoc.exists()) {
              const vData = vDoc.data() as TemplateVersion;
              setActiveVersion(vData);
              setConfigDraft(JSON.parse(JSON.stringify(vData.configuration)));
            }
          }
        } else {
          setError('Template not found');
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchTemplate();
  }, [templateId]);

  const handleSaveDraft = async () => {
    if (!templateId || !configDraft || !activeVersion) return;
    if (activeVersion.status === 'APPROVED' || activeVersion.status === 'ACTIVE') {
      setError("This template version is immutable. Create a new draft version.");
      return;
    }
    setSaving(true);
    setError('');
    try {
      await setDoc(doc(db, `templates/${templateId}/versions`, activeVersion.version), {
        ...activeVersion,
        configuration: configDraft,
        updatedAt: serverTimestamp()
      });
      setActiveVersion({...activeVersion, configuration: configDraft});
      // Mock refresh persistence
      setTimeout(() => setSaving(false), 500);
    } catch (err: any) {
      setError(err.message);
      setSaving(false);
    }
  };

  const handleCreateNewVersion = async () => {
    if (!template || !activeVersion || !templateId) return;
    try {
      const newVersionNum = (parseFloat(activeVersion.version.replace('v', '')) + 0.1).toFixed(1);
      const newVersionId = `v${newVersionNum}`;
      
      const newVersion: TemplateVersion = {
        version: newVersionId,
        status: 'DRAFT',
        configuration: JSON.parse(JSON.stringify(activeVersion.configuration)),
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      
      await setDoc(doc(db, `templates/${templateId}/versions`, newVersionId), newVersion);
      await setDoc(doc(db, 'templates', templateId), {
        ...template,
        currentVersion: newVersionId,
        status: 'DRAFT',
        updatedAt: serverTimestamp()
      });
      
      window.location.reload();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleValidateTemplate = async () => {
    if (!configDraft) return;
    setValidating(true);
    setError('');
    setSuccess('');
    try {
      const response = await fetch('http://localhost:8000/api/templates/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_config: configDraft })
      });
      const data = await response.json();
      if (data.valid) {
        setSuccess('Template validation passed: Geometry fits canonical 300 DPI A4 page with 50 questions.');
      } else {
        setError(`Validation failed: ${data.error}`);
      }
    } catch (err: any) {
      setError(`Validation error: ${err.message}`);
    } finally {
      setValidating(false);
    }
  };

  const handlePublishVersion = async () => {
    if (!templateId || !activeVersion || !configDraft) return;
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const valRes = await fetch('http://localhost:8000/api/templates/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ template_config: configDraft })
      });
      const valData = await valRes.json();
      if (!valData.valid) {
        throw new Error(`Cannot publish: Template validation failed (${valData.error})`);
      }

      await setDoc(doc(db, `templates/${templateId}/versions`, activeVersion.version), {
        ...activeVersion,
        configuration: configDraft,
        status: 'APPROVED',
        approvedAt: serverTimestamp(),
        updatedAt: serverTimestamp()
      });

      await setDoc(doc(db, 'templates', templateId), {
        currentVersion: activeVersion.version,
        status: 'APPROVED',
        updatedAt: serverTimestamp()
      }, { merge: true });

      setActiveVersion({ ...activeVersion, status: 'APPROVED', configuration: configDraft });
      setSuccess(`Version ${activeVersion.version} successfully validated and published!`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleAssignToExam = async () => {
    if (!template || !templateId || !activeVersion) return;
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const targetExamId = template.examId || 'exam_rise_2027';
      await setDoc(doc(db, 'exams', targetExamId), {
        templateId: templateId,
        templateVersionId: activeVersion.version,
        updatedAt: serverTimestamp()
      }, { merge: true });
      setSuccess(`Assigned ${template.name} (${activeVersion.version}) to Exam ${targetExamId}!`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const generatePreview = async () => {
    if (!configDraft) return;
    setGenerating(true);
    setError('');
    try {
      const token = await auth.currentUser?.getIdToken();
      const response = await fetch('http://localhost:8000/api/templates/generate-preview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ template_config: configDraft })
      });
      
      const data = await response.json();
      if (response.ok) {
        setPdfUrl(`http://localhost:8000${data.url}`);
      } else {
        throw new Error(data.detail || data.error || 'Failed to generate PDF');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <div className="card">Loading template workspace...</div>;
  if (!template) return <div className="card">Template Error: {error}</div>;

  const totalQuestions = configDraft?.sections?.reduce((sum: number, s: any) => sum + (s.question_count || 0), 0) || 0;
  const totalMarks = configDraft?.sections?.reduce((sum: number, s: any) => sum + (s.allocated_marks || 0), 0) || 0;
  
  const isReadOnly = activeVersion?.status === 'APPROVED' || activeVersion?.status === 'ACTIVE';

  return (
    <div className="template-workspace">
      <div style={{ marginBottom: '1.5rem' }}>
        <Link to="/templates" style={{ textDecoration: 'none', color: 'var(--text-secondary)' }}>&larr; Templates</Link>
      </div>

      <header className="page-header" style={{ borderBottom: 'none', paddingBottom: 0 }}>
        <h2>{template.name}</h2>
        <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
          <span>Template ID: {templateId}</span>
          <span>Version {activeVersion?.version || 'None'}</span>
          <span style={{ color: activeVersion?.status === 'APPROVED' ? '#166534' : 'inherit', fontWeight: 600 }}>{activeVersion?.status || 'No active version'}</span>
        </div>
      </header>

      <div style={{ display: 'flex', gap: '1rem', borderBottom: '1px solid var(--border-color)', marginBottom: '2rem' }}>
        <button className={`nav-tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')} style={{ padding: '0.75rem 1rem', background: 'none', border: 'none', borderBottom: activeTab === 'overview' ? '2px solid var(--primary-color)' : 'none', cursor: 'pointer', fontWeight: activeTab === 'overview' ? 600 : 400 }}>Overview</button>
        <button className={`nav-tab ${activeTab === 'designer' ? 'active' : ''}`} onClick={() => setActiveTab('designer')} style={{ padding: '0.75rem 1rem', background: 'none', border: 'none', borderBottom: activeTab === 'designer' ? '2px solid var(--primary-color)' : 'none', cursor: 'pointer', fontWeight: activeTab === 'designer' ? 600 : 400 }}>Designer</button>
        <button className={`nav-tab ${activeTab === 'preview' ? 'active' : ''}`} onClick={() => setActiveTab('preview')} style={{ padding: '0.75rem 1rem', background: 'none', border: 'none', borderBottom: activeTab === 'preview' ? '2px solid var(--primary-color)' : 'none', cursor: 'pointer', fontWeight: activeTab === 'preview' ? 600 : 400 }}>Preview</button>
        <button className={`nav-tab ${activeTab === 'versions' ? 'active' : ''}`} onClick={() => setActiveTab('versions')} style={{ padding: '0.75rem 1rem', background: 'none', border: 'none', borderBottom: activeTab === 'versions' ? '2px solid var(--primary-color)' : 'none', cursor: 'pointer', fontWeight: activeTab === 'versions' ? 600 : 400 }}>Versions</button>
      </div>

      {error && <div style={{ color: '#991b1b', backgroundColor: '#fee2e2', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem' }}>{error}</div>}
      {success && <div style={{ color: '#166534', backgroundColor: '#dcfce7', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem' }}>{success}</div>}

      {activeTab === 'overview' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0 }}>Template Overview</h3>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button className="btn btn-outline" onClick={handleValidateTemplate} disabled={validating}>
                {validating ? 'Validating...' : 'Validate Geometry'}
              </button>
              {activeVersion?.status !== 'APPROVED' ? (
                <button className="btn btn-accent" onClick={handlePublishVersion} disabled={saving}>
                  Publish Version ({activeVersion?.version})
                </button>
              ) : (
                <span className="btn btn-outline" style={{ pointerEvents: 'none', color: '#166534' }}>
                  ✓ Published & Immutable
                </span>
              )}
              <button className="btn btn-primary" onClick={handleAssignToExam} disabled={saving}>
                Assign to Exam ({template.examId || 'RISE 2027'})
              </button>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1rem' }}>
            <div><strong>Template Name:</strong> {template.name}</div>
            <div><strong>Template ID:</strong> {templateId}</div>
            <div><strong>Exam:</strong> {template.examId}</div>
            <div><strong>Version:</strong> {activeVersion?.version}</div>
            <div><strong>Status:</strong> {activeVersion?.status}</div>
            <div><strong>Paper Size:</strong> {configDraft?.page?.size || 'A4'} {configDraft?.page?.orientation || 'Portrait'}</div>
            <div><strong>Total Questions:</strong> {totalQuestions}</div>
            <div><strong>Total Marks:</strong> {totalMarks}</div>
            <div><strong>Global Options:</strong> {configDraft?.sections?.[0]?.option_count || 4}</div>
            <div><strong>QR Status:</strong> {configDraft?.qr?.enabled ? 'Enabled' : 'Disabled'}</div>
            <div><strong>Columns:</strong> {configDraft?.layout?.columns || 3} Columns</div>
          </div>
        </div>
      )}

      {activeTab === 'designer' && configDraft && (
        <div style={{ display: 'flex', gap: '1.5rem', height: 'calc(100vh - 200px)' }}>
          {/* LEFT / MAIN CONFIGURATION */}
          <div style={{ width: '400px', flexShrink: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {isReadOnly && (
              <div style={{ backgroundColor: '#fffbeb', color: '#b45309', padding: '1rem', borderRadius: '8px', fontSize: '0.875rem' }}>
                <strong>Immutable:</strong> This template version is immutable. 
                <button className="btn btn-outline" style={{ marginTop: '0.5rem', display: 'block', width: '100%' }} onClick={handleCreateNewVersion}>Create New Draft Version</button>
              </div>
            )}
            
            <div className="card">
              <h3 style={{ marginBottom: '1rem' }}>Header & Branding</h3>
              <div className="form-group">
                <label className="form-label">School Name</label>
                <input type="text" className="form-control" disabled={isReadOnly} value={configDraft.header?.school_name || ''} onChange={e => setConfigDraft({...configDraft, header: {...configDraft.header, school_name: e.target.value}})} />
              </div>
              <div className="form-group">
                <label className="form-label">Exam Name</label>
                <input type="text" className="form-control" disabled={isReadOnly} value={configDraft.header?.exam_name || ''} onChange={e => setConfigDraft({...configDraft, header: {...configDraft.header, exam_name: e.target.value}})} />
              </div>
              <div className="form-group">
                <label className="form-label">Subtitle</label>
                <input type="text" className="form-control" disabled={isReadOnly} value={configDraft.header?.subtitle || ''} onChange={e => setConfigDraft({...configDraft, header: {...configDraft.header, subtitle: e.target.value}})} />
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label">Primary Color</label>
                  <input type="color" className="form-control" disabled={isReadOnly} value={configDraft.brand_colors?.primary || '#123E7C'} onChange={e => setConfigDraft({...configDraft, brand_colors: {...configDraft.brand_colors, primary: e.target.value}})} style={{ padding: '0.25rem', height: '40px' }} />
                </div>
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label">Accent Color</label>
                  <input type="color" className="form-control" disabled={isReadOnly} value={configDraft.brand_colors?.accent || '#E8720C'} onChange={e => setConfigDraft({...configDraft, brand_colors: {...configDraft.brand_colors, accent: e.target.value}})} style={{ padding: '0.25rem', height: '40px' }} />
                </div>
              </div>
            </div>

            <div className="card">
              <h3 style={{ marginBottom: '1rem' }}>Page & Layout Settings</h3>
              <div className="form-group">
                <label className="form-label">Paper Size</label>
                <select className="form-control" disabled={isReadOnly} value={configDraft.page?.size || 'A4'} onChange={e => setConfigDraft({...configDraft, page: {...configDraft.page, size: e.target.value}})}>
                  <option value="A4">A4</option>
                  <option value="Letter">Letter</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Global Option Count</label>
                <select className="form-control" disabled={isReadOnly} value={configDraft.sections?.[0]?.option_count || 4} onChange={e => {
                  const count = parseInt(e.target.value);
                  const newSections = configDraft.sections?.map((s: any) => ({...s, option_count: count}));
                  setConfigDraft({...configDraft, sections: newSections});
                }}>
                  <option value="3">3 Options (A/B/C)</option>
                  <option value="4">4 Options (A/B/C/D)</option>
                  <option value="5">5 Options (A/B/C/D/E)</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">QR Code</label>
                <select className="form-control" disabled={isReadOnly} value={configDraft.qr?.enabled ? 'true' : 'false'} onChange={e => setConfigDraft({...configDraft, qr: {...configDraft.qr, enabled: e.target.value === 'true'}})}>
                  <option value="true">Enabled</option>
                  <option value="false">Disabled</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginTop: 'auto', paddingBottom: '2rem' }}>
              {!isReadOnly && (
                <button className="btn btn-primary" onClick={handleSaveDraft} disabled={saving} style={{ flex: 1 }}>
                  {saving ? 'Saving...' : 'Save Draft'}
                </button>
              )}
              <button className="btn btn-accent" onClick={generatePreview} disabled={generating} style={{ flex: 1 }}>
                {generating ? 'Generating...' : 'Preview PDF'}
              </button>
            </div>
          </div>

          {/* RIGHT SIDE - LIVE PREVIEW */}
          <div style={{ flex: 1, backgroundColor: '#f1f5f9', borderRadius: '8px', border: '1px solid var(--border-color)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '0.75rem 1rem', borderBottom: '1px solid var(--border-color)', backgroundColor: '#fff', fontWeight: 600, display: 'flex', justifyContent: 'space-between' }}>
              <span>Live Generated PDF</span>
              {generating && <span style={{ color: 'var(--primary-color)' }}>Generating via Python Engine...</span>}
            </div>
            <div style={{ flex: 1, position: 'relative' }}>
              {pdfUrl ? (
                <iframe src={pdfUrl} width="100%" height="100%" style={{ border: 'none' }} title="PDF Preview" />
              ) : (
                <div style={{ display: 'flex', height: '100%', justifyContent: 'center', alignItems: 'center', color: 'var(--text-secondary)' }}>
                  Click "Preview PDF" to generate the OMR layout using the Python engine.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'preview' && (
        <div style={{ height: 'calc(100vh - 200px)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ marginBottom: '1rem' }}>
            <button className="btn btn-primary" onClick={generatePreview} disabled={generating}>
              {generating ? 'Generating Full Preview...' : 'Generate Full Preview PDF'}
            </button>
          </div>
          <div style={{ flex: 1, backgroundColor: '#e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
            {pdfUrl ? (
              <iframe src={pdfUrl} width="100%" height="100%" style={{ border: 'none' }} title="PDF Full Preview" />
            ) : (
              <div style={{ display: 'flex', height: '100%', justifyContent: 'center', alignItems: 'center', color: 'var(--text-secondary)' }}>
                No preview generated yet.
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'versions' && (
        <div className="card">
          <h3>Version History</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                <th style={{ padding: '0.75rem' }}>Version</th>
                <th style={{ padding: '0.75rem' }}>Status</th>
                <th style={{ padding: '0.75rem' }}>Questions</th>
                <th style={{ padding: '0.75rem' }}>Created</th>
              </tr>
            </thead>
            <tbody>
              {allVersions.map(v => (
                <tr key={v.version} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '0.75rem', fontWeight: 500 }}>{v.version} {v.version === activeVersion?.version && '(Active)'}</td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ 
                      padding: '0.25rem 0.5rem', 
                      borderRadius: '9999px', 
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      backgroundColor: v.status === 'APPROVED' ? '#dcfce7' : '#f1f5f9',
                      color: v.status === 'APPROVED' ? '#166534' : '#475569'
                    }}>
                      {v.status}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>
                    {v.configuration?.sections?.reduce((sum: number, s: any) => sum + (s.question_count || 0), 0) || 0}
                  </td>
                  <td style={{ padding: '0.75rem', color: 'var(--text-secondary)' }}>
                    {v.createdAt ? new Date(v.createdAt).toLocaleDateString() : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default TemplateWorkspace;
