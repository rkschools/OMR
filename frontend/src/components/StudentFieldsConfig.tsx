import React from 'react';
import type { StudentField } from '../types';

interface StudentFieldsConfigProps {
  fields: StudentField[];
  onChange: (fields: StudentField[]) => void;
  readOnly?: boolean;
}

export const StudentFieldsConfig: React.FC<StudentFieldsConfigProps> = ({ fields, onChange, readOnly = false }) => {
  const handleToggle = (fieldId: string, key: 'enabled' | 'required') => {
    if (readOnly) return;
    const newFields = fields.map(f => f.field_id === fieldId ? { ...f, [key]: !f[key] } : f);
    onChange(newFields);
  };

  const handleMove = (index: number, direction: 'up' | 'down') => {
    if (readOnly) return;
    const newFields = [...fields];
    if (direction === 'up' && index > 0) {
      [newFields[index - 1], newFields[index]] = [newFields[index], newFields[index - 1]];
    } else if (direction === 'down' && index < newFields.length - 1) {
      [newFields[index + 1], newFields[index]] = [newFields[index], newFields[index + 1]];
    }
    // Update order
    newFields.forEach((f, i) => f.order = i + 1);
    onChange(newFields);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3>Student Information Fields</h3>
        <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Note: Registration Number is fixed to 6 handwritten boxes.</span>
      </div>

      <div className="table-responsive">
        <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid var(--border-color)' }}>
          <thead style={{ backgroundColor: '#f8fafc' }}>
            <tr>
              {!readOnly && <th style={{ padding: '0.75rem', width: '80px' }}>Order</th>}
              <th style={{ padding: '0.75rem', textAlign: 'left' }}>Field Name</th>
              <th style={{ padding: '0.75rem', textAlign: 'left' }}>Input Type</th>
              <th style={{ padding: '0.75rem', textAlign: 'center' }}>Required</th>
              <th style={{ padding: '0.75rem', textAlign: 'center' }}>Enabled</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((field, idx) => (
              <tr key={field.field_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                {!readOnly && (
                  <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                    <button type="button" onClick={() => handleMove(idx, 'up')} disabled={idx === 0} style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '0.25rem' }}>▲</button>
                    <button type="button" onClick={() => handleMove(idx, 'down')} disabled={idx === fields.length - 1} style={{ border: 'none', background: 'none', cursor: 'pointer', padding: '0.25rem' }}>▼</button>
                  </td>
                )}
                <td style={{ padding: '0.75rem' }}>
                  <div style={{ fontWeight: 500 }}>{field.label}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{field.field_id}</div>
                </td>
                <td style={{ padding: '0.75rem' }}>
                  <span style={{ fontSize: '0.875rem', padding: '0.25rem 0.5rem', backgroundColor: '#e2e8f0', borderRadius: '4px' }}>
                    {field.input_type}
                  </span>
                  {field.field_id === 'reg_no' && <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: '#b45309' }}>6 boxes</span>}
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                  <input type="checkbox" checked={field.required} onChange={() => handleToggle(field.field_id, 'required')} disabled={readOnly} />
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                  <input type="checkbox" checked={field.enabled} onChange={() => handleToggle(field.field_id, 'enabled')} disabled={readOnly} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
