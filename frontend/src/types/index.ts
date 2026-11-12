// Shared TypeScript interfaces matching the FastAPI backend schemas

export type UserRole = 'patient' | 'doctor' | 'admin' | 'public_health_analyst';

export interface User {
  username: string;
  role: UserRole;
  full_name: string;
  patient_id?: string;
  assigned_doctor_id?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  username: string;
  full_name: string;
  patient_id?: string;
}

export interface Patient {
  patient_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone_number?: string;
  email?: string;
  address_line1?: string;
  city?: string;
  district?: string;
  state?: string;
  postal_code?: string;
  blood_group?: string;
  blood_type?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  assigned_doctor_id?: string;
  created_at: string;
}

export interface PaginatedPatients {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: Patient[];
}

export interface Encounter {
  encounter_id: string;
  patient_id: string;
  encounter_type: string;
  start_date: string;
  end_date?: string;
  reason_code?: string;
  reason_description?: string;
  provider_id?: string;
  facility_name?: string;
}

export interface Condition {
  condition_id: string;
  patient_id: string;
  encounter_id?: string;
  code: string;
  description: string;
  condition_code?: string;
  condition_name?: string;
  category?: string;
  onset_date: string;
  clinical_status: string;
}

export interface Observation {
  observation_id: string;
  patient_id: string;
  encounter_id?: string;
  code: string;
  description: string;
  value_numeric?: number;
  value_string?: string;
  unit?: string;
  effective_date: string;
  interpretation?: string;
}

export interface Medication {
  medication_id: string;
  patient_id: string;
  encounter_id?: string;
  medication_name: string;
  dosage: string;
  frequency: string;
  prescribing_doctor?: string;
  route?: string;
  start_date: string;
  end_date?: string;
  status: string;
}

export interface MedicalAskResponse {
  answer: string;
  citations: CitationItem[];
  rejected_citations?: any[];
  evidence_status?: string;
  emergency_directive?: any;
  retrieval_latency_ms: number;
  generation_latency_ms: number;
  total_latency_ms: number;
  model_id: string;
  disclaimer: string;
}

export interface RiskAssessment {
  assessment_id: string;
  patient_id: string;
  assessment_date: string;
  risk_category: string;
  score_numeric: number;
  model_name: string;
}

export interface DiseasePredictionItem {
  rank: number;
  disease_category: string;
  experimental_model_score: number;
}

export interface CitationItem {
  document_id?: string;
  chunk_id?: string;
  title?: string;
  source_organization?: string;
  source_url?: string;
  page_number?: number;
  section_heading?: string;
  verification_status?: string;
  claim_supported?: boolean | string;
}

export interface SafetyWarning {
  level: 'EMERGENCY' | 'URGENT' | 'ROUTINE' | 'INFORMATIONAL';
  title: string;
  message: string;
  emergency_action_recommended: boolean;
  triggers: string[];
}

export interface SymptomPredictResponse {
  predictions: DiseasePredictionItem[];
  evidence_status: string;
  abstention_reason?: string;
  top_model_score: number;
  score_margin: number;
  symptoms_supplied_count: number;
  safety_warnings: SafetyWarning[];
  model_identifier: string;
  disclaimer: string;
}

export interface PredictAndExplainResponse {
  original_predictions: DiseasePredictionItem[];
  explanation: string;
  citations: CitationItem[];
  rejected_citations: any[];
  evidence_status: string;
  safety_warnings?: SafetyWarning[];
  disclaimer: string;
  model_identifier: string;
  retrieval_latency_ms: number;
  generation_latency_ms: number;
  total_latency_ms: number;
}

export interface Allergy {
  allergy_id: string;
  patient_id: string;
  substance: string;
  reaction: string;
  severity: string;
  category: string;
  verification_status: string;
  recorded_date: string;
  notes?: string;
  created_at: string;
}

export interface FamilyCondition {
  id: string;
  family_member_id: string;
  condition_name: string;
  approximate_age_at_onset?: number;
  notes?: string;
}

export interface FamilyMember {
  id: string;
  patient_id: string;
  relative_name?: string;
  relation_type: string;
  lineage?: string;
  is_deceased: boolean;
  notes?: string;
  created_at: string;
  conditions: FamilyCondition[];
}

export interface DailyHealthLog {
  id: string;
  patient_id: string;
  log_date: string;
  systolic_bp?: number;
  diastolic_bp?: number;
  pulse?: number;
  fasting_glucose?: number;
  post_meal_glucose?: number;
  weight_kg?: number;
  temperature_c?: number;
  spo2?: number;
  sleep_hours?: number;
  mood?: string;
  steps_count?: number;
  source: string;
  notes?: string;
  created_at: string;
}

export interface PatientDocument {
  document_id: string;
  patient_id: string;
  file_name: string;
  file_type: string;
  document_type: string;
  report_date?: string;
  file_size_bytes: number;
  extracted_text?: string;
  extracted_metadata?: string;
  confirmation_status: string;
  created_at: string;
}

export interface ChatMessage {
  message_id: string;
  conversation_id: string;
  sender: 'user' | 'assistant';
  content: string;
  proposed_ehr_actions?: string;
  is_confirmed_to_ehr: boolean;
  created_at: string;
}

export interface ChatConversation {
  conversation_id: string;
  patient_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: ChatMessage[];
}

export interface FutureRiskInsight {
  patient_id: string;
  target_condition: string;
  prediction_horizon: string;
  lookback_window: string;
  status: string;
  estimated_risk_score?: number;
  risk_category?: string;
  contributing_factors: { factor: string; metric?: string; impact?: string; detail?: string }[];
  historical_metrics_analyzed: Record<string, any>;
  clinical_disclaimer: string;
}

export interface TimelineEvent {
  event_id: string;
  event_type: 'encounter' | 'condition' | 'observation' | 'medication';
  patient_id: string;
  encounter_id?: string;
  event_date: string;
  clinical_details: Record<string, any>;
  source_table: string;
}

export interface TimelineResponse {
  patient_id: string;
  total_events: number;
  events: TimelineEvent[];
}
