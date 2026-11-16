// Shared TypeScript interfaces matching the FastAPI backend schemas

export type UserRole = 'patient' | 'doctor' | 'nurse' | 'hospital_admin' | 'admin' | 'public_health_analyst';

export interface User {
  username: string;
  role: UserRole;
  full_name: string;
  patient_id?: string;
  assigned_doctor_id?: string;
  gender?: string;
  date_of_birth?: string;
  facility?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
  username: string;
  full_name: string;
  patient_id?: string;
  gender?: string;
  date_of_birth?: string;
}

export interface Patient {
  patient_id: string;
  first_name: string;
  last_name: string;
  date_of_birth?: string;
  birth_date?: string;
  gender?: string;
  sex?: string;
  age?: number;
  phone_number?: string;
  contact_no?: string;
  email?: string;
  address_line1?: string;
  city?: string;
  district?: string;
  state?: string;
  postal_code?: string;
  blood_group?: string;
  blood_type?: string;
  is_smoker?: boolean;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  assigned_doctor_id?: string;
  created_at?: string;
  abha_number?: string;
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

export interface ContributingFactor {
  factor: string;
  metric?: string;
  impact?: string;
  detail?: string;
}

export interface ConditionRiskEvaluation {
  condition_name: string;
  icd10_code: string;
  category: string;
  status: string;
  risk_score?: number;
  risk_tier: string;
  contributing_factors: ContributingFactor[];
  clinical_recommendations: string[];
}

export interface DataCompletenessReport {
  completeness_percentage: number;
  readiness_level: string;
  vitals_recorded: boolean;
  glycemic_panel_recorded: boolean;
  lipid_panel_recorded: boolean;
  renal_panel_recorded: boolean;
  recorded_biomarkers: string[];
  missing_biomarkers: string[];
  recommended_screenings: string[];
}

export interface FamilyConditionSummary {
  relative_name?: string;
  relation_type: string;
  lineage?: string;
  is_deceased: boolean;
  condition_name: string;
  approximate_age_at_onset?: number;
  hereditary_risk_weight: string;
}

export interface FamilyHealthRiskReport {
  total_relatives_tracked: number;
  conditions_in_pedigree: string[];
  hereditary_predispositions: string[];
  family_members_summary: FamilyConditionSummary[];
  clinical_genetics_guidance: string;
}

export interface FutureRiskInsight {
  patient_id: string;
  patient_name?: string;
  patient_age?: number;
  patient_sex?: string;
  is_smoker?: boolean;
  target_condition: string;
  prediction_horizon: string;
  lookback_window: string;
  status: string;
  primary_risk_summary?: string;
  estimated_risk_score?: number;
  risk_category?: string;
  contributing_factors: ContributingFactor[];
  condition_evaluations?: ConditionRiskEvaluation[];
  data_completeness?: DataCompletenessReport;
  family_health_risk?: FamilyHealthRiskReport;
  historical_metrics_analyzed: Record<string, any>;
  clinical_disclaimer: string;
}

export type ComprehensiveFutureRiskResponse = FutureRiskInsight;

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

// ==========================================
// Hospital Management System & Multi-Agent Types
// ==========================================

export interface Bed {
  bed_id: string;
  bed_number: string;
  ward: string;
  bed_type: string;
  is_occupied: boolean;
  status: 'available' | 'occupied' | 'cleaning' | 'maintenance' | 'reserved';
  current_patient_id?: string;
  daily_charge: number;
  notes?: string;
}

export interface WardOverview {
  ward: string;
  total: number;
  occupied: number;
  available: number;
  beds: Bed[];
}

export interface BedOverview {
  total_beds: number;
  occupied_beds: number;
  available_beds: number;
  cleaning_beds: number;
  maintenance_beds: number;
  occupancy_rate: number;
  wards: WardOverview[];
}

export interface DoctorProfile {
  doctor_id: string;
  name: string;
  department: string;
  specialty: string;
  qualification: string;
  experience_years: number;
  consultation_fee: number;
  hospital_name?: string;
  is_available: boolean;
  available_slots: string[];
}

export interface AppointmentBooking {
  booking_id: string;
  token_number?: string;
  patient_id: string;
  patient_name?: string;
  doctor_id: string;
  doctor_name?: string;
  qualification?: string;
  department: string;
  hospital_name?: string;
  chamber_room?: string;
  booking_date: string;
  time_slot: string;
  status: 'confirmed' | 'checked_in' | 'completed' | 'cancelled' | 'no_show';
  chief_complaint?: string;
  consultation_fee?: number;
  fee?: number;
  booked_via: string;
  created_at?: string;
}

export interface AppointmentBookingTicket {
  booking_id: string;
  token_number: string;
  status: string;
  patient_id: string;
  patient_name: string;
  doctor_id: string;
  doctor_name: string;
  qualification?: string;
  department: string;
  specialty?: string;
  hospital_name: string;
  chamber_room: string;
  booking_date: string;
  time_slot: string;
  fee: number;
  consultation_fee?: number;
  chief_complaint?: string;
  booked_via?: string;
  created_at?: string;
}

export interface AdmissionRequest {
  request_id: string;
  patient_id: string;
  doctor_id?: string;
  department: string;
  recommended_ward: string;
  assigned_bed_id?: string;
  priority: 'routine' | 'urgent' | 'emergency';
  status: 'pending' | 'assigned' | 'admitted' | 'discharged' | 'cancelled';
  admission_notes?: string;
  created_at?: string;
  discharged_at?: string;
}

export interface ProcurementItem {
  item_id: string;
  name: string;
  category: string;
  current_stock: number;
  unit: string;
  reorder_threshold: number;
  reorder_quantity: number;
  unit_price: number;
  supplier_name: string;
  supplier_contact?: string;
  expiry_date?: string;
  batch_number?: string;
  status: 'in_stock' | 'low_stock' | 'critical' | 'expired';
}

export interface PurchaseOrder {
  po_id: string;
  item_id: string;
  item_name?: string;
  unit?: string;
  quantity: number;
  estimated_cost: number;
  supplier_name: string;
  generated_by: string;
  status: 'draft_pending_authorization' | 'approved' | 'ordered' | 'received' | 'rejected';
  approval_notes?: string;
  approved_by?: string;
  created_at?: string;
}

export interface PendingEHRUpdate {
  update_id: string;
  patient_id: string;
  patient_name?: string;
  update_type: 'condition' | 'medication' | 'observation' | 'allergy' | 'clinical_note';
  source: string;
  proposed_data: Record<string, any>;
  status: 'pending_verification' | 'approved' | 'rejected' | 'edited_and_approved';
  assigned_doctor_id?: string;
  reviewed_by?: string;
  review_notes?: string;
  created_at?: string;
  reviewed_at?: string;
}

export interface BillingInvoice {
  invoice_id: string;
  patient_id: string;
  patient_name?: string;
  invoice_date: string;
  total_amount: number;
  insurance_covered: number;
  patient_payable: number;
  payment_status: 'draft' | 'pending' | 'paid' | 'partially_paid' | 'cancelled';
  items: { description: string; category: string; amount: number }[];
  icd10_codes: { code: string; description: string; category?: string; clinical_rationale?: string }[];
  coded_by?: string;
  approved_by?: string;
  created_at?: string;
}

export interface AgentEvent {
  event_id: string;
  timestamp: string;
  source_agent: string;
  target_agent?: string;
  event_type: string;
  payload: Record<string, any>;
  status: string;
  requires_human_approval: boolean;
  approval_status?: string;
  resolution_notes?: string;
}

export interface BIQueryResult {
  query: string;
  domain: string;
  summary: string;
  chart?: {
    type: 'bar' | 'pie' | 'line';
    title: string;
    labels: string[];
    series?: { name: string; data: number[] }[];
    data?: number[];
  };
  metrics?: Record<string, any>;
}

// ============================================================================
// FAMILY ACCOUNTS & CONSENT-BASED ACCESS TYPES
// ============================================================================

export interface FamilySearchResult {
  patient_id: string;
  full_name: string;
  gender: string;
  age_bracket: string;
  masked_contact?: string;
  city_district?: string;
}

export interface FamilyLink {
  link_id: string;
  requester_patient_id: string;
  target_patient_id: string;
  requester_name?: string;
  target_name?: string;
  relationship_type: string;
  status: 'pending' | 'approved' | 'rejected' | 'revoked';
  permissions: string[];
  requested_at: string;
  responded_at?: string;
  notes?: string;
}

export interface ConnectedFamilyMember {
  link_id: string;
  patient_id: string;
  full_name: string;
  relationship_type: string;
  age: number;
  gender: string;
  blood_group?: string;
  permissions: string[];
  linked_since: string;
  can_manage_appointments: boolean;
  can_view_records: boolean;
  can_view_reports: boolean;
}

export interface PermittedFamilyEHR {
  patient_id: string;
  relationship_type: string;
  demographics: {
    patient_id: string;
    first_name: string;
    last_name: string;
    full_name: string;
    age: number;
    gender: string;
    date_of_birth: string;
    district: string;
    blood_group: string;
  };
  permitted_scopes: string[];
  allergies?: Allergy[];
  latest_daily_vitals?: DailyHealthLog[];
  conditions?: { diagnosis_name: string; code: string; status: string; onset_date?: string }[];
  medications?: { medication_name: string; dosage: string; status: string; prescribed_date?: string }[];
  encounters?: any[];
  observations?: { test_name: string; test_code: string; value_numeric: number; unit: string; date: string; interpretation: string; reference_range: string }[];
  documents?: PatientDocument[];
  can_manage_appointments?: boolean;
}

// ============================================================================
// DOCTOR CLINICAL WORKSPACE TYPES
// ============================================================================

export interface DoctorOverviewData {
  doctor_name: string;
  specialty: string;
  hospital: string;
  stats: {
    today_appointments_count: number;
    admitted_inpatients_count: number;
    pending_verifications_count: number;
    pending_orders_count: number;
    critical_alerts_count: number;
  };
  today_appointments: {
    booking_id: string;
    patient_id: string;
    patient_name: string;
    time_slot: string;
    department: string;
    hospital_name: string;
    status: string;
    chief_complaint?: string;
    booked_via: string;
  }[];
  admitted_inpatients: {
    request_id: string;
    patient_id: string;
    patient_name: string;
    department: string;
    ward: string;
    bed_number: string;
    priority: string;
    admission_notes?: string;
    admitted_since: string;
  }[];
  critical_alerts: {
    patient_id: string;
    patient_name: string;
    alert_type: string;
    severity: string;
    message: string;
    timestamp: string;
  }[];
  upcoming_rounds: {
    time: string;
    type: string;
    location: string;
  }[];
}

export interface DoctorPatientDirectoryItem {
  patient_id: string;
  full_name: string;
  age: number;
  gender: string;
  district: string;
  clinical_status: string;
  is_admitted: boolean;
  ward: string;
  bed_number: string;
  attending_doctor: string;
  department: string;
  active_diagnoses: string[];
  last_consultation: string;
  next_appointment: string;
  critical_alert: boolean;
}

export interface ClinicalNote {
  note_id: string;
  patient_id: string;
  patient_name?: string;
  encounter_id?: string;
  doctor_id: string;
  doctor_name: string;
  note_type: string;
  title: string;
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface ClinicalOrder {
  order_id: string;
  patient_id: string;
  patient_name?: string;
  encounter_id?: string;
  doctor_id: string;
  doctor_name: string;
  order_type: string;
  order_name: string;
  clinical_indication?: string;
  priority: string;
  status: string;
  result_summary?: string;
  ordered_at: string;
  completed_at?: string;
}

export interface DoctorFullEHR {
  patient_id: string;
  demographics: Record<string, any>;
  conditions: any[];
  medications: any[];
  allergies: any[];
  drug_interactions: {
    drug_a: string;
    drug_b: string;
    severity: string;
    clinical_effect: string;
    recommendation: string;
  }[];
  observations: any[];
  documents: PatientDocument[];
  imaging_scans: PatientDocument[];
  encounters: any[];
  daily_vitals_trends: DailyHealthLog[];
  family_history: any[];
  clinical_notes: ClinicalNote[];
  clinical_orders: ClinicalOrder[];
  admissions_history: any[];
  pending_verifications: any[];
}

export interface CopilotDraftNote {
  patient_id: string;
  patient_name: string;
  draft_status: string;
  generated_by: string;
  title: string;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  suggested_investigations: string[];
}

// ============================================================================
// NURSE NURSING WORKSPACE TYPES
// ============================================================================

export interface NurseOverviewData {
  nurse_name: string;
  shift: {
    shift_type: string;
    label: string;
    active: boolean;
  };
  assigned_ward: string;
  hospital: string;
  stats: {
    total_facility_beds: number;
    occupied_beds: number;
    available_beds: number;
    active_inpatients_count: number;
    pending_mar_count: number;
    pending_tasks_count: number;
    immediate_attention_count: number;
  };
  immediate_attention: {
    patient_id: string;
    patient_name: string;
    type: string;
    severity: string;
    message: string;
    recorded_at: string;
  }[];
  pending_mar_doses: {
    mar_id: string;
    patient_id: string;
    patient_name: string;
    medication_name: string;
    dosage: string;
    route: string;
    scheduled_time: string;
    status: string;
  }[];
  nursing_tasks: {
    task_id: string;
    patient_id: string;
    patient_name: string;
    ward: string;
    bed_number?: string;
    task_type: string;
    title: string;
    priority: string;
    scheduled_time: string;
    status: string;
  }[];
}

export interface NurseBedBoardItem {
  bed_id: string;
  bed_number: string;
  ward: string;
  bed_type: string;
  status: string;
  is_occupied: boolean;
  daily_charge: number;
  patient_id?: string;
  patient_name?: string;
  patient_age_sex?: string;
  attending_doctor?: string;
  assigned_nurse?: string;
  admission_date?: string;
  priority?: string;
  notes?: string;
}

export interface NursingTaskItem {
  task_id: string;
  patient_id: string;
  patient_name?: string;
  encounter_id?: string;
  ward: string;
  bed_number?: string;
  task_type: string;
  title: string;
  description?: string;
  priority: string;
  scheduled_time: string;
  status: string;
  assigned_nurse_id?: string;
  assigned_nurse_name?: string;
  completed_at?: string;
  completed_by?: string;
  completion_notes?: string;
  created_at: string;
}

export interface MedicationAdministrationItem {
  mar_id: string;
  patient_id: string;
  patient_name?: string;
  medication_id?: string;
  medication_name: string;
  dosage: string;
  route: string;
  scheduled_time: string;
  administered_time?: string;
  administered_by?: string;
  status: 'scheduled' | 'administered' | 'delayed' | 'refused' | 'missed';
  reason?: string;
  notes?: string;
  created_at: string;
}

export interface ShiftHandoverItem {
  handover_id: string;
  ward: string;
  shift_type: string;
  outgoing_nurse_id: string;
  outgoing_nurse_name: string;
  incoming_nurse_id?: string;
  incoming_nurse_name?: string;
  handover_date: string;
  situation: string;
  background: string;
  assessment: string;
  recommendation: string;
  critical_alerts: string[];
  total_patients: number;
  created_at: string;
}


