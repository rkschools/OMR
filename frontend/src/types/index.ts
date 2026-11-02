export interface Exam {
  examId: string;
  name: string;
  year: string;
  description: string;
  status: 'ACTIVE' | 'ARCHIVED' | 'DRAFT';
  classes: string[];
  templateId?: string;
  templateVersionId?: string;
  createdAt: any;
  updatedAt: any;
}

export interface Section {
  section_id: string;
  name: string;
  order: number;
  allocated_marks: number;
  question_count: number;
  marks_per_question: number;
  option_count: number;
  question_numbering: {
    start: number;
    end: number;
  };
}

export interface StudentField {
  field_id: string;
  label: string;
  order: number;
  input_type: string;
  required: boolean;
  enabled: boolean;
}

export interface TemplateConfiguration {
  marking_scheme: {
    correct: number;
    wrong: number;
    blank: number;
  };
  sections: Section[];
  student_fields: StudentField[];
  classesConfig?: {
    [className: string]: {
      sections: Section[];
    }
  };
}

export interface TemplateVersion {
  version: string;
  status: 'APPROVED' | 'ACTIVE' | 'DRAFT' | 'ARCHIVED';
  configuration: TemplateConfiguration;
  createdAt: any;
  updatedAt: any;
  approvedAt?: any;
}

export interface Template {
  examId: string;
  name: string;
  currentVersion: string;
  status: 'APPROVED' | 'ACTIVE' | 'DRAFT' | 'ARCHIVED';
  createdAt: any;
  updatedAt: any;
}
