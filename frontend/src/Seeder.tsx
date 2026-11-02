import React, { useState } from 'react';
import { doc, setDoc, serverTimestamp } from 'firebase/firestore';
import { db } from './firebase';
import templateConfig from './rise_omr_template.json';

export const Seeder: React.FC = () => {
  const [status, setStatus] = useState<string>('');
  
  const handleSeed = async () => {
    setStatus('Seeding...');
    try {
      const examId = "exam_rise_2027";
      const templateId = "template_exam_rise_2027";
      const versionId = "v1.0.0";

      // 1. Create Exam Document with explicit template references
      await setDoc(doc(db, 'exams', examId), {
          examId: examId,
          name: "RISE 2027",
          year: "2027",
          description: "Official RISE 2027 Scholarship Examination",
          status: "ACTIVE",
          classes: ["8"],
          templateId: templateId,
          templateVersionId: versionId,
          createdAt: serverTimestamp(),
          updatedAt: serverTimestamp()
      });

      // 2. Create Template Document
      await setDoc(doc(db, 'templates', templateId), {
          examId: examId,
          name: "RISE 2027 Official OMR",
          description: "Canonical 50-question OMR template for RISE 2027",
          currentVersion: versionId,
          status: "APPROVED",
          createdAt: serverTimestamp(),
          updatedAt: serverTimestamp()
      });

      // 3. Prepare Config
      const config: any = { ...templateConfig };
      config.marking_scheme = {
          correct: 1.0,
          wrong: -0.333333,
          blank: 0.0
      };

      // 4. Create Template Version Document (Immutable since APPROVED)
      await setDoc(doc(db, `templates/${templateId}/versions`, versionId), {
          version: versionId,
          status: "APPROVED",
          configuration: config,
          commitMessage: "Approved 50-question physical hardware template",
          createdAt: serverTimestamp(),
          updatedAt: serverTimestamp(),
          approvedAt: serverTimestamp()
      });

      // 5. Create a DEMO Answer Key for Class 8, Set A
      const demoKeys: any = {};
      const options = ['A', 'B', 'C', 'D'];
      for (let i = 1; i <= 50; i++) {
        demoKeys[i] = options[(i - 1) % 4];
      }
      await setDoc(doc(db, 'answerKeys', `${examId}_8_A`), {
          examId: examId,
          class: "8",
          paperSet: "A",
          keys: demoKeys,
          status: "PUBLISHED",
          updatedAt: new Date().toISOString()
      });
      
      setStatus('Success! Database seeded with RISE 2027.');
    } catch (err: any) {
      console.error(err);
      setStatus(`Error: ${err.message}`);
    }
  };

  return (
    <>
    <div className="card">
      <h3>Database Initialization</h3>
      <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>Click below to seed Firestore with the foundational RISE 2027 exam parameters.</p>
      <button className="btn btn-accent" onClick={handleSeed}>Seed RISE 2027 Exam</button>
      {status && <div style={{ marginTop: '1rem', fontWeight: 500 }}>{status}</div>}
    </div>
    <div className="card" style={{ marginTop: '1.5rem' }}>
      <h3>Test OMR Scans</h3>
      <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>Download pre-generated synthetic OMR scans for testing the Scanner Workspace.</p>
      <div style={{ display: 'flex', gap: '1rem' }}>
        <a href="/test_scans/RISE_2027_base.png" download className="btn btn-outline">Blank Sheet</a>
        <a href="/test_scans/test1_all_A.png" download className="btn btn-outline">All A's (Perfect)</a>
        <a href="/test_scans/test2_mixed.png" download className="btn btn-outline">Mixed (Multiple/Ambiguous)</a>
      </div>
    </div>
    </>
  );
};
