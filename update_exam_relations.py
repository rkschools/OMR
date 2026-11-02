import os
import re

def update_file(path, replacements):
    with open(path, 'r') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)

# 1. Update Types
update_file('frontend/src/types/index.ts', [
    ("  classes: string[];\n", "  classes: string[];\n  templateId?: string;\n  templateVersionId?: string;\n")
])

# 2. Update ExamDetail.tsx
exam_detail_fetch = """        // Fetch active template
        let templateId = examDoc.data().templateId;
        let currentVersionId = examDoc.data().templateVersionId;
        
        if (!templateId) {
            // Fallback for old records
            templateId = `template_${examId}`;
        }
        
        const templateDoc = await getDoc(doc(db, 'templates', templateId));
        if (templateDoc.exists()) {
          if (!currentVersionId) {
             currentVersionId = templateDoc.data().currentVersion;
          }
          if (currentVersionId) {
              const versionDoc = await getDoc(doc(db, `templates/${templateId}/versions`, currentVersionId));
              if (versionDoc.exists()) {
                const vData = versionDoc.data() as TemplateVersion;
                setTemplateVersion(vData);
                setConfigDraft(JSON.parse(JSON.stringify(vData.configuration))); // Deep copy for editing
              }
          }
        }"""

update_file('frontend/src/pages/ExamDetail.tsx', [
    ("""        // Fetch active template
        const templateId = `template_${examId}`;
        const templateDoc = await getDoc(doc(db, 'templates', templateId));
        if (templateDoc.exists()) {
          const currentVersionId = templateDoc.data().currentVersion;
          const versionDoc = await getDoc(doc(db, `templates/${templateId}/versions`, currentVersionId));
          if (versionDoc.exists()) {
            const vData = versionDoc.data() as TemplateVersion;
            setTemplateVersion(vData);
            setConfigDraft(JSON.parse(JSON.stringify(vData.configuration))); // Deep copy for editing
          }
        }""", exam_detail_fetch)
])

# 3. Update ScannerWorkspace.tsx
scanner_fetch = """    const examDoc = await getDoc(doc(db, 'exams', selectedExam));
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
      const vData = vDoc.data();"""

update_file('frontend/src/pages/ScannerWorkspace.tsx', [
    ("""    const tDoc = await getDocs(collection(db, 'templates'));
    const templateDoc = tDoc.docs.find(d => d.id === `template_${selectedExam}`);
    if (!templateDoc) {
      alert("Template not found for this exam.");
      return;
    }
    const currentVersionId = templateDoc.data().currentVersion;
    
    let configStr = '';
    try {
      const vDoc = await getDocs(collection(db, `templates/template_${selectedExam}/versions`));
      const vData = vDoc.docs.find(d => d.id === currentVersionId)?.data();""", scanner_fetch)
])

print("Updated relations!")
