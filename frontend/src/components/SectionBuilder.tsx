import React, { useState } from 'react';
import type { Section } from '../types';

interface SectionBuilderProps {
  sections: Section[];
  onChange: (sections: Section[]) => void;
  readOnly?: boolean;
}

const generateRandomId = () => Math.random().toString(36).substring(2, 9);

export const SectionBuilder: React.FC<SectionBuilderProps> = ({ sections, onChange, readOnly = false }) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<Section>>({});
  const [error, setError] = useState<string>('');

  const recalculateRanges = (sects: Section[]): Section[] => {
    let currentStart = 1;
    return sects.map(s => {
      const qCount = s.question_count || 0;
      const end = currentStart + qCount - 1;
      const updated = {
        ...s,
        question_numbering: {
          start: qCount > 0 ? currentStart : 0,
          end: qCount > 0 ? end : 0
        }
      };
      if (qCount > 0) currentStart = end + 1;
      return updated;
    });
  };

  const handleMove = (index: number, direction: 'up' | 'down') => {
    if (readOnly) return;
    const newSections = [...sections];
    if (direction === 'up' && index > 0) {
      [newSections[index - 1], newSections[index]] = [newSections[index], newSections[index - 1]];
    } else if (direction === 'down' && index < newSections.length - 1) {
      [newSections[index + 1], newSections[index]] = [newSections[index], newSections[index + 1]];
    }
    // Update order property and ranges
    newSections.forEach((s, i) => s.order = i + 1);
    onChange(recalculateRanges(newSections));
  };

  const handleDelete = (id: string) => {
    if (readOnly) return;
    const newSections = sections.filter(s => s.section_id !== id);
    newSections.forEach((s, i) => s.order = i + 1);
    onChange(recalculateRanges(newSections));
  };

  const handleStartEdit = (section: Section) => {
    if (readOnly) return;
    setEditingId(section.section_id);
    setEditForm({ ...section });
    setError('');
  };

  const handleSaveEdit = () => {
    if (!editForm.section_id?.trim() || !editForm.name?.trim()) {
      setError("Section ID and Name are required.");
      return;
    }
    if ((editForm.question_count ?? 0) < 0 || (editForm.allocated_marks ?? 0) < 0) {
      setError("Counts and marks cannot be negative.");
      return;
    }
    // Check dupe ID
    if (sections.some(s => s.section_id === editForm.section_id && s.section_id !== editingId)) {
      setError("Section ID must be unique.");
      return;
    }

    const newSections = sections.map(s => s.section_id === editingId ? { ...s, ...editForm } as Section : s);
    setEditingId(null);
    onChange(recalculateRanges(newSections));
  };

  const handleAdd = () => {
    if (readOnly) return;
    const newId = `section_${generateRandomId()}`;
    const newSection: Section = {
      section_id: newId,
      name: 'New Section',
      order: sections.length + 1,
      allocated_marks: 10,
      question_count: 10,
      marks_per_question: 1,
      option_count: 4,
      question_numbering: { start: 0, end: 0 }
    };
    onChange(recalculateRanges([...sections, newSection]));
    setEditingId(newId);
    setEditForm(newSection);
  };

  const totalQuestions = sections.reduce((sum, s) => sum + (s.question_count || 0), 0);
  const totalMarks = sections.reduce((sum, s) => sum + (s.allocated_marks || 0), 0);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3>Sections Configuration</h3>
        {!readOnly && <button type="button" className="btn btn-primary" onClick={handleAdd}>+ Add Section</button>}
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ padding: '0.75rem', backgroundColor: '#f1f5f9', borderRadius: '8px', flex: 1, textAlign: 'center' }}>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Total Questions</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--primary-color)' }}>{totalQuestions}</div>
        </div>
        <div style={{ padding: '0.75rem', backgroundColor: '#f1f5f9', borderRadius: '8px', flex: 1, textAlign: 'center' }}>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Total Marks</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--primary-color)' }}>{totalMarks}</div>
        </div>
      </div>

      <div className="table-responsive">
        <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid var(--border-color)' }}>
          <thead style={{ backgroundColor: '#f8fafc' }}>
            <tr>
              {!readOnly && <th style={{ padding: '0.75rem', width: '80px' }}>Order</th>}
              <th style={{ padding: '0.75rem', textAlign: 'left' }}>Section Name (ID)</th>
              <th style={{ padding: '0.75rem', textAlign: 'center' }}>Questions</th>
              <th style={{ padding: '0.75rem', textAlign: 'center' }}>Marks</th>
              <th style={{ padding: '0.75rem', textAlign: 'center' }}>Range</th>
              {!readOnly && <th style={{ padding: '0.75rem', textAlign: 'right' }}>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {sections.length === 0 && (
              <tr><td colSpan={6} style={{ padding: '1rem', textAlign: 'center' }}>No sections configured.</td></tr>
            )}
            {sections.map((section, idx) => (
              editingId === section.section_id ? (
                <tr key="editing" style={{ backgroundColor: '#fffbeb' }}>
                  <td colSpan={6} style={{ padding: '1rem' }}>
                    {error && <div style={{ color: 'red', fontSize: '0.875rem', marginBottom: '0.5rem' }}>{error}</div>}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                      <div className="form-group">
                        <label className="form-label">Section ID</label>
                        <input type="text" className="form-control" value={editForm.section_id || ''} onChange={e => setEditForm({...editForm, section_id: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Display Name</label>
                        <input type="text" className="form-control" value={editForm.name || ''} onChange={e => setEditForm({...editForm, name: e.target.value})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Questions Count</label>
                        <input type="number" className="form-control" value={editForm.question_count || 0} onChange={e => setEditForm({...editForm, question_count: parseInt(e.target.value) || 0})} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Allocated Marks</label>
                        <input type="number" step="0.5" className="form-control" value={editForm.allocated_marks || 0} onChange={e => setEditForm({...editForm, allocated_marks: parseFloat(e.target.value) || 0})} />
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                      <button type="button" className="btn btn-primary" onClick={handleSaveEdit}>Save</button>
                      <button type="button" className="btn btn-outline" onClick={() => { setEditingId(null); setError(''); }}>Cancel</button>
                    </div>
                  </td>
                </tr>
              ) : (
                <tr key={section.section_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  {!readOnly && (
                    <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                      <button type="button" onClick={() => handleMove(idx, 'up')} disabled={idx === 0} style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '0.25rem' }}>▲</button>
                      <button type="button" onClick={() => handleMove(idx, 'down')} disabled={idx === sections.length - 1} style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '0.25rem' }}>▼</button>
                    </td>
                  )}
                  <td style={{ padding: '0.75rem' }}>
                    <div style={{ fontWeight: 500 }}>{section.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{section.section_id}</div>
                  </td>
                  <td style={{ padding: '0.75rem', textAlign: 'center' }}>{section.question_count}</td>
                  <td style={{ padding: '0.75rem', textAlign: 'center' }}>{section.allocated_marks}</td>
                  <td style={{ padding: '0.75rem', textAlign: 'center', fontFamily: 'monospace' }}>
                    {section.question_count > 0 ? `Q${section.question_numbering.start} - Q${section.question_numbering.end}` : '-'}
                  </td>
                  {!readOnly && (
                    <td style={{ padding: '0.75rem', textAlign: 'right' }}>
                      <button type="button" className="btn btn-outline" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', marginRight: '0.5rem' }} onClick={() => handleStartEdit(section)}>Edit</button>
                      <button type="button" className="btn btn-outline" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', color: 'red', borderColor: 'red' }} onClick={() => handleDelete(section.section_id)}>Delete</button>
                    </td>
                  )}
                </tr>
              )
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
