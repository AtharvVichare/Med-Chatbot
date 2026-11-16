// Centralized API Service for Aarogya Drishti 2.0 Frontend

import type {
  AuthResponse,
  PaginatedPatients,
  Patient,
  Encounter,
  Condition,
  Observation,
  Medication,
  PredictAndExplainResponse,
  SymptomPredictResponse,
  MedicalAskResponse,
  Allergy,
  FamilyMember,
  DailyHealthLog,
  PatientDocument,
  ChatConversation,
  ChatMessage,
  FutureRiskInsight,
  TimelineResponse,
  Bed,
  BedOverview,
  DoctorProfile,
  AppointmentBooking,
  AdmissionRequest,
  ProcurementItem,
  PurchaseOrder,
  PendingEHRUpdate,
  BillingInvoice,
  AgentEvent,
  BIQueryResult,
  FamilySearchResult,
  FamilyLink,
  ConnectedFamilyMember,
  PermittedFamilyEHR,
  DoctorOverviewData,
  DoctorPatientDirectoryItem,
  ClinicalNote,
  ClinicalOrder,
  DoctorFullEHR,
  CopilotDraftNote,
  NurseOverviewData,
  NurseBedBoardItem,
  NursingTaskItem,
  MedicationAdministrationItem,
  ShiftHandoverItem
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

class ApiClient {
  private getAuthHeader(): Record<string, string> {
    const token = localStorage.getItem('aarogya_jwt');
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
    return {};
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...this.getAuthHeader(),
      ...(options.headers || {})
    };

    const response = await fetch(url, {
      ...options,
      headers
    });

    if (response.status === 401) {
      const hadToken = !!localStorage.getItem('aarogya_jwt');
      localStorage.removeItem('aarogya_jwt');
      localStorage.removeItem('aarogya_user');
      if (hadToken) {
        window.dispatchEvent(new Event('auth_logout'));
        throw new Error('Authentication expired or invalid. Please sign in again.');
      }
      let errorMsg = 'Incorrect username or password.';
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errorMsg = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // fallback
      }
      throw new Error(errorMsg);
    }

    if (!response.ok) {
      let errorMsg = `Server error (${response.status})`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errorMsg = typeof errorJson.detail === 'string'
            ? errorJson.detail
            : JSON.stringify(errorJson.detail);
        }
      } catch {
        errorMsg = response.statusText || errorMsg;
      }
      throw new Error(errorMsg);
    }

    return response.json();
  }

  // --- Auth API ---
  async login(username: string, password: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
  }

  async googleLogin(idToken: string): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/v1/auth/google', {
      method: 'POST',
      body: JSON.stringify({ id_token: idToken })
    });
  }

  async signup(payload: {
    username: string;
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    gender: string;
    date_of_birth: string;
    phone?: string;
    district?: string;
    state?: string;
    is_smoker?: boolean;
    blood_group?: string;
  }): Promise<AuthResponse> {
    return this.request<AuthResponse>('/api/v1/auth/signup', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async getMyProfile(): Promise<Patient> {
    return this.request<Patient>('/api/v1/auth/me');
  }

  async forgotPassword(email: string): Promise<{ message: string }> {
    return this.request<{ message: string }>('/api/v1/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email })
    });
  }

  async resetPassword(payload: { token: string; new_password: string }): Promise<{ message: string }> {
    return this.request<{ message: string }>('/api/v1/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // --- Patients & EHR API ---
  async getPatients(page: number = 1, pageSize: number = 20, district?: string): Promise<PaginatedPatients> {
    let query = `?page=${page}&page_size=${pageSize}`;
    if (district) query += `&district=${encodeURIComponent(district)}`;
    return this.request<PaginatedPatients>(`/api/v1/patients${query}`);
  }

  async getPatient(patientId: string): Promise<Patient> {
    return this.request<Patient>(`/api/v1/patients/${patientId}`);
  }

  async updatePatient(patientId: string, data: Partial<Patient>): Promise<Patient> {
    return this.request<Patient>(`/api/v1/patients/${patientId}`, {
      method: 'PATCH',
      body: JSON.stringify(data)
    });
  }

  async getPatientEncounters(patientId: string): Promise<Encounter[]> {
    return this.request<Encounter[]>(`/api/v1/patients/${patientId}/encounters`);
  }

  async getPatientConditions(patientId: string): Promise<Condition[]> {
    return this.request<Condition[]>(`/api/v1/patients/${patientId}/conditions`);
  }

  async addPatientCondition(patientId: string, data: {
    condition_code: string;
    condition_name: string;
    onset_date?: string;
    category?: string;
  }): Promise<Condition> {
    return this.request<Condition>(`/api/v1/patients/${patientId}/conditions`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async getPatientObservations(patientId: string): Promise<Observation[]> {
    return this.request<Observation[]>(`/api/v1/patients/${patientId}/observations`);
  }

  async getPatientMedications(patientId: string): Promise<Medication[]> {
    return this.request<Medication[]>(`/api/v1/patients/${patientId}/medications`);
  }

  async addPatientMedication(patientId: string, data: {
    medication_name: string;
    dosage?: string;
    frequency?: string;
    start_date?: string;
    prescribing_doctor?: string;
  }): Promise<Medication> {
    return this.request<Medication>(`/api/v1/patients/${patientId}/medications`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async discontinuePatientMedication(patientId: string, medicationId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/patients/${patientId}/medications/${medicationId}/discontinue`, {
      method: 'PATCH'
    });
  }

  async getPatientTimeline(patientId: string): Promise<TimelineResponse> {
    return this.request<TimelineResponse>(`/api/v1/patients/${patientId}/timeline`);
  }

  // --- Allergies ---
  async getPatientAllergies(patientId: string): Promise<Allergy[]> {
    return this.request<Allergy[]>(`/api/v1/patients/${patientId}/allergies`);
  }

  async addPatientAllergy(patientId: string, data: {
    substance: string;
    reaction: string;
    severity?: string;
    category?: string;
    notes?: string;
  }): Promise<Allergy> {
    return this.request<Allergy>(`/api/v1/patients/${patientId}/allergies`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async deletePatientAllergy(patientId: string, allergyId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/patients/${patientId}/allergies/${allergyId}`, {
      method: 'DELETE'
    });
  }

  // --- Family History ---
  async getPatientFamilyHistory(patientId: string): Promise<FamilyMember[]> {
    return this.request<FamilyMember[]>(`/api/v1/patients/${patientId}/family-history`);
  }

  async addPatientFamilyMember(patientId: string, data: {
    relative_name?: string;
    relation_type: string;
    lineage?: string;
    is_deceased?: boolean;
    notes?: string;
    conditions?: { condition_name: string; approximate_age_at_onset?: number; notes?: string }[];
  }): Promise<FamilyMember> {
    return this.request<FamilyMember>(`/api/v1/patients/${patientId}/family-history`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async deletePatientFamilyMember(patientId: string, memberId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/patients/${patientId}/family-history/${memberId}`, {
      method: 'DELETE'
    });
  }

  // --- Daily Health Tracking ---
  async getPatientDailyTracking(patientId: string, limit: number = 30): Promise<DailyHealthLog[]> {
    return this.request<DailyHealthLog[]>(`/api/v1/patients/${patientId}/daily-tracking?limit=${limit}`);
  }

  async recordPatientDailyLog(patientId: string, data: Partial<DailyHealthLog>): Promise<DailyHealthLog> {
    return this.request<DailyHealthLog>(`/api/v1/patients/${patientId}/daily-tracking`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  // --- Patient Documents & Reports ---
  async getPatientDocuments(patientId: string): Promise<PatientDocument[]> {
    return this.request<PatientDocument[]>(`/api/v1/patients/${patientId}/documents`);
  }

  async uploadPatientDocument(formData: FormData): Promise<PatientDocument> {
    const url = `${API_BASE_URL}/api/v1/documents/upload`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        ...this.getAuthHeader()
      },
      body: formData
    });

    if (!response.ok) {
      let errorMsg = `Upload failed (${response.status})`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) errorMsg = errorJson.detail;
      } catch {}
      throw new Error(errorMsg);
    }
    return response.json();
  }

  async confirmPatientDocument(documentId: string): Promise<{ message: string; observations_created: number }> {
    return this.request<{ message: string; observations_created: number }>(`/api/v1/documents/${documentId}/confirm`, {
      method: 'POST'
    });
  }

  getDocumentFileUrl(documentId: string): string {
    const token = localStorage.getItem('aarogya_jwt');
    const base = `${API_BASE_URL}/api/v1/documents/${documentId}/file`;
    return token ? `${base}?token=${encodeURIComponent(token)}` : base;
  }

  async fetchDocumentBlob(documentId: string): Promise<Blob> {
    const url = `${API_BASE_URL}/api/v1/documents/${documentId}/file`;
    const response = await fetch(url, {
      headers: this.getAuthHeader()
    });
    if (!response.ok) {
      throw new Error(`Failed to load document (${response.status})`);
    }
    return response.blob();
  }

  // --- AI Health Assistant & Conversations ---
  async getConversations(): Promise<ChatConversation[]> {
    return this.request<ChatConversation[]>('/api/v1/assistant/conversations');
  }

  async createConversation(title?: string): Promise<ChatConversation> {
    return this.request<ChatConversation>('/api/v1/assistant/conversations', {
      method: 'POST',
      body: JSON.stringify({ title: title || 'New Health Consultation' })
    });
  }

  async getConversationMessages(conversationId: string): Promise<ChatMessage[]> {
    return this.request<ChatMessage[]>(`/api/v1/assistant/conversations/${conversationId}/messages`);
  }

  async sendMessage(conversationId: string, content: string): Promise<ChatMessage> {
    return this.request<ChatMessage>(`/api/v1/assistant/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content })
    });
  }

  async confirmAssistantAction(payload: {
    message_id: string;
    action_type: 'condition' | 'medication' | 'measurement';
    data: Record<string, any>;
  }): Promise<{ message: string; status: string }> {
    return this.request<{ message: string; status: string }>('/api/v1/assistant/confirm-action', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // --- Future Health Insights ---
  async getFutureRisk(patientId: string): Promise<FutureRiskInsight> {
    return this.request<FutureRiskInsight>(`/api/v1/insights/future-risk/${patientId}`);
  }

  async getDiabetesRisk(patientId: string): Promise<FutureRiskInsight> {
    return this.request<FutureRiskInsight>(`/api/v1/insights/future-risk/${patientId}`);
  }

  // --- Disease Prediction & Explanation API ---
  async getSymptomsList(): Promise<string[]> {
    return this.request<string[]>('/api/v1/disease/symptoms');
  }

  async predictOnly(payload: {
    symptoms: string[];
    duration?: string;
    severity?: string;
    progression?: string;
    has_fever?: boolean;
    breathing_difficulty?: boolean;
    chest_discomfort?: boolean;
    medical_history?: string[];
  }): Promise<SymptomPredictResponse> {
    return this.request<SymptomPredictResponse>('/api/v1/disease/predict', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async predictAndExplain(payload: {
    symptoms: string[];
    duration?: string;
    severity?: string;
    progression?: string;
    has_fever?: boolean;
    breathing_difficulty?: boolean;
    chest_discomfort?: boolean;
    medical_history?: string[];
  }): Promise<PredictAndExplainResponse> {
    return this.request<PredictAndExplainResponse>('/api/v1/disease/predict-and-explain', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // --- Medical Reference RAG API ---
  async askMedicalKnowledge(question: string, topK: number = 3): Promise<MedicalAskResponse> {
    return this.request<MedicalAskResponse>('/api/v1/medical/ask', {
      method: 'POST',
      body: JSON.stringify({ question, top_k: topK })
    });
  }

  // --- Longitudinal Trends API ---
  async getLongitudinalTrends(patientId: string, metric: string = 'blood_pressure'): Promise<any> {
    return this.request<any>(`/api/v1/patients/${patientId}/longitudinal-trends?metric=${metric}`);
  }

  // --- Bed Management & Admissions API ---
  async getBedOverview(): Promise<BedOverview> {
    return this.request<BedOverview>('/api/v1/beds/overview');
  }

  async listBeds(params?: { ward?: string; status_filter?: string; is_occupied?: boolean }): Promise<Bed[]> {
    const query = new URLSearchParams();
    if (params?.ward) query.append('ward', params.ward);
    if (params?.status_filter) query.append('status_filter', params.status_filter);
    if (params?.is_occupied !== undefined) query.append('is_occupied', String(params.is_occupied));
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<Bed[]>(`/api/v1/beds/list${qs}`);
  }

  async listAdmissions(params?: { status_filter?: string; patient_id?: string }): Promise<AdmissionRequest[]> {
    const query = new URLSearchParams();
    if (params?.status_filter) query.append('status_filter', params.status_filter);
    if (params?.patient_id) query.append('patient_id', params.patient_id);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<AdmissionRequest[]>(`/api/v1/beds/admissions${qs}`);
  }

  async admitPatient(payload: {
    patient_id: string;
    department: string;
    recommended_ward: string;
    priority?: string;
    admission_notes?: string;
    doctor_id?: string;
  }): Promise<any> {
    return this.request<any>('/api/v1/beds/admission', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async transferBed(requestId: string, newBedId: string): Promise<any> {
    return this.request<any>('/api/v1/beds/transfer', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId, new_bed_id: newBedId })
    });
  }

  async dischargePatient(requestId: string): Promise<any> {
    return this.request<any>('/api/v1/beds/discharge', {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId })
    });
  }

  // --- Procurement & Pharmacy Inventory API ---
  async listInventory(params?: { category?: string; status_filter?: string }): Promise<ProcurementItem[]> {
    const query = new URLSearchParams();
    if (params?.category) query.append('category', params.category);
    if (params?.status_filter) query.append('status_filter', params.status_filter);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<ProcurementItem[]>(`/api/v1/inventory/items${qs}`);
  }

  async auditInventory(): Promise<any> {
    return this.request<any>('/api/v1/inventory/audit');
  }

  async listPurchaseOrders(statusFilter?: string): Promise<PurchaseOrder[]> {
    const qs = statusFilter ? `?status_filter=${statusFilter}` : '';
    return this.request<PurchaseOrder[]>(`/api/v1/inventory/purchase-orders${qs}`);
  }

  async authorizePurchaseOrder(poId: string, action: 'approve' | 'reject', notes?: string): Promise<any> {
    return this.request<any>(`/api/v1/inventory/purchase-orders/${poId}/authorize`, {
      method: 'POST',
      body: JSON.stringify({ action, notes })
    });
  }

  // --- Doctor Directory & Booking API ---
  async getDoctors(department?: string): Promise<DoctorProfile[]> {
    const qs = department ? `?department=${department}` : '';
    return this.request<DoctorProfile[]>(`/api/v1/directory/doctors${qs}`);
  }

  async getHospitals(): Promise<any[]> {
    return this.request<any[]>('/api/v1/directory/hospitals');
  }

  async listAppointments(params?: { doctor_id?: string; patient_id?: string; status_filter?: string }): Promise<AppointmentBooking[]> {
    const query = new URLSearchParams();
    if (params?.doctor_id) query.append('doctor_id', params.doctor_id);
    if (params?.patient_id) query.append('patient_id', params.patient_id);
    if (params?.status_filter) query.append('status_filter', params.status_filter);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<AppointmentBooking[]>(`/api/v1/directory/appointments${qs}`);
  }

  async bookAppointment(payload: {
    doctor_id: string;
    booking_date: string;
    time_slot: string;
    chief_complaint?: string;
    patient_id?: string;
  }): Promise<any> {
    return this.request<any>('/api/v1/directory/book-appointment', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async cancelAppointment(bookingId: string): Promise<any> {
    return this.request<any>(`/api/v1/directory/appointments/${bookingId}`, {
      method: 'DELETE'
    });
  }

  async updateAppointmentStatus(bookingId: string, status: string): Promise<any> {
    return this.request<any>(`/api/v1/directory/appointments/${bookingId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    });
  }

  // --- Doctor Verification Workflow API ---
  async listPendingVerifications(params?: { doctor_id?: string; patient_id?: string; status_filter?: string }): Promise<PendingEHRUpdate[]> {
    const query = new URLSearchParams();
    if (params?.doctor_id) query.append('doctor_id', params.doctor_id);
    if (params?.patient_id) query.append('patient_id', params.patient_id);
    if (params?.status_filter) query.append('status_filter', params.status_filter);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<PendingEHRUpdate[]>(`/api/v1/doctor-verification/pending${qs}`);
  }

  async reviewPendingVerification(updateId: string, action: 'approve' | 'reject' | 'edit_and_approve', reviewNotes?: string, editedData?: any): Promise<any> {
    return this.request<any>(`/api/v1/doctor-verification/${updateId}/review`, {
      method: 'POST',
      body: JSON.stringify({ action, review_notes: reviewNotes, edited_data: editedData })
    });
  }

  async doctorDirectEntry(payload: { patient_id: string; entry_type: string; data: any }): Promise<any> {
    return this.request<any>('/api/v1/doctor-verification/direct-entry', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // --- Billing & RCM API ---
  async listInvoices(params?: { patient_id?: string; payment_status?: string }): Promise<BillingInvoice[]> {
    const query = new URLSearchParams();
    if (params?.patient_id) query.append('patient_id', params.patient_id);
    if (params?.payment_status) query.append('payment_status', params.payment_status);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return this.request<BillingInvoice[]>(`/api/v1/billing/invoices${qs}`);
  }

  async getRevenueSummary(): Promise<any> {
    return this.request<any>('/api/v1/billing/summary');
  }

  async generateInvoice(payload: { patient_id: string; items: any[]; insurance_percentage?: number; clinical_context?: string }): Promise<any> {
    return this.request<any>('/api/v1/billing/generate', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async payInvoice(invoiceId: string, paymentMethod: string = 'online_upi'): Promise<any> {
    return this.request<any>(`/api/v1/billing/${invoiceId}/pay`, {
      method: 'POST',
      body: JSON.stringify({ payment_method: paymentMethod })
    });
  }

  // --- Multi-Agent Event Bus & AI Operations API ---
  async listAgentEvents(limit: number = 30): Promise<AgentEvent[]> {
    return this.request<AgentEvent[]>(`/api/v1/agents/events?limit=${limit}`);
  }

  async resolveEscalation(eventId: string, action: 'approve' | 'reject', resolutionNotes: string): Promise<any> {
    return this.request<any>(`/api/v1/agents/escalations/${eventId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ action, resolution_notes: resolutionNotes })
    });
  }

  async triageIntake(message: string, patientId?: string): Promise<any> {
    return this.request<any>('/api/v1/agents/triage-intake', {
      method: 'POST',
      body: JSON.stringify({ message, patient_id: patientId })
    });
  }

  async checkDrugSafety(patientId: string, proposedMedication: string): Promise<any> {
    return this.request<any>('/api/v1/agents/safety-check', {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId, proposed_medication: proposedMedication })
    });
  }

  // --- Conversational BI API ---
  async runConversationalBI(query: string): Promise<BIQueryResult> {
    return this.request<BIQueryResult>('/api/v1/conversational-bi/query', {
      method: 'POST',
      body: JSON.stringify({ query })
    });
  }

  // --- EHR PDF Export ---
  getEhrPdfDownloadUrl(patientId: string): string {
    return `${API_BASE_URL}/api/v1/patients/${patientId}/pdf-export`;
  }

  async downloadEhrPdf(patientId: string): Promise<Blob> {
    const url = this.getEhrPdfDownloadUrl(patientId);
    const headers = {
      ...this.getAuthHeader()
    };
    const response = await fetch(url, { headers });
    if (!response.ok) {
      throw new Error(`Failed to download EHR PDF (${response.status})`);
    }
    return response.blob();
  }
  // --- Family Accounts & Permissions API ---
  async searchFamilyMembers(q: string): Promise<FamilySearchResult[]> {
    return this.request<FamilySearchResult[]>(`/api/v1/family/search?q=${encodeURIComponent(q)}`);
  }

  async sendFamilyLinkRequest(payload: {
    target_patient_id: string;
    relationship_type: string;
    permissions: string[];
    notes?: string;
  }): Promise<FamilyLink> {
    return this.request<FamilyLink>('/api/v1/family/requests', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async listFamilyLinkRequests(direction: string = 'all', statusFilter?: string): Promise<FamilyLink[]> {
    const params = new URLSearchParams({ direction });
    if (statusFilter) params.append('status_filter', statusFilter);
    return this.request<FamilyLink[]>(`/api/v1/family/requests?${params.toString()}`);
  }

  async respondFamilyLinkRequest(
    linkId: string,
    action: 'approve' | 'reject',
    permissions?: string[],
    notes?: string
  ): Promise<FamilyLink> {
    return this.request<FamilyLink>(`/api/v1/family/requests/${linkId}/respond`, {
      method: 'POST',
      body: JSON.stringify({ action, permissions, notes })
    });
  }

  async updateFamilyLinkPermissions(linkId: string, permissions: string[]): Promise<FamilyLink> {
    return this.request<FamilyLink>(`/api/v1/family/links/${linkId}/permissions`, {
      method: 'PATCH',
      body: JSON.stringify({ permissions })
    });
  }

  async revokeFamilyLink(linkId: string): Promise<{ message: string; link_id: string }> {
    return this.request<{ message: string; link_id: string }>(`/api/v1/family/links/${linkId}`, {
      method: 'DELETE'
    });
  }

  async listConnectedFamilyMembers(): Promise<ConnectedFamilyMember[]> {
    return this.request<ConnectedFamilyMember[]>('/api/v1/family/members');
  }

  async getFamilyMemberPermittedEhr(familyPatientId: string): Promise<PermittedFamilyEHR> {
    return this.request<PermittedFamilyEHR>(`/api/v1/family/members/${familyPatientId}/ehr`);
  }

  // --- Doctor Clinical Workspace API ---
  async getDoctorOverview(): Promise<DoctorOverviewData> {
    return this.request<DoctorOverviewData>('/api/v1/doctor/overview');
  }

  async getDoctorPatients(statusFilter: string = 'all', search?: string): Promise<DoctorPatientDirectoryItem[]> {
    const params = new URLSearchParams({ status_filter: statusFilter });
    if (search) params.append('search', search);
    return this.request<DoctorPatientDirectoryItem[]>(`/api/v1/doctor/patients?${params.toString()}`);
  }

  async getDoctorPatientFullEhr(patientId: string): Promise<DoctorFullEHR> {
    return this.request<DoctorFullEHR>(`/api/v1/doctor/patients/${patientId}/full-ehr`);
  }

  async createClinicalNote(payload: {
    patient_id: string;
    encounter_id?: string;
    note_type: string;
    title: string;
    subjective?: string;
    objective?: string;
    assessment?: string;
    plan?: string;
    content: string;
  }): Promise<ClinicalNote> {
    return this.request<ClinicalNote>('/api/v1/doctor/clinical-notes', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async createClinicalOrder(payload: {
    patient_id: string;
    encounter_id?: string;
    order_type: string;
    order_name: string;
    clinical_indication?: string;
    priority?: string;
  }): Promise<ClinicalOrder> {
    return this.request<ClinicalOrder>('/api/v1/doctor/orders', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async generateCopilotDraftNote(payload: {
    patient_id: string;
    note_type?: string;
    clinical_focus?: string;
  }): Promise<CopilotDraftNote> {
    return this.request<CopilotDraftNote>('/api/v1/doctor/copilot/draft-note', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  // --- Nurse Nursing Workspace API ---
  async getNurseOverview(wardFilter?: string): Promise<NurseOverviewData> {
    const params = wardFilter ? `?ward_filter=${encodeURIComponent(wardFilter)}` : '';
    return this.request<NurseOverviewData>(`/api/v1/nurse/overview${params}`);
  }

  async getNurseBedBoard(ward?: string): Promise<NurseBedBoardItem[]> {
    const params = ward ? `?ward=${encodeURIComponent(ward)}` : '';
    return this.request<NurseBedBoardItem[]>(`/api/v1/nurse/bed-board${params}`);
  }

  async listNursingTasks(ward?: string, statusFilter?: string, priority?: string): Promise<NursingTaskItem[]> {
    const params = new URLSearchParams();
    if (ward) params.append('ward', ward);
    if (statusFilter) params.append('status_filter', statusFilter);
    if (priority) params.append('priority', priority);
    return this.request<NursingTaskItem[]>(`/api/v1/nurse/tasks?${params.toString()}`);
  }

  async createNursingTask(payload: {
    patient_id: string;
    encounter_id?: string;
    ward: string;
    bed_number?: string;
    task_type: string;
    title: string;
    description?: string;
    priority?: string;
    scheduled_time: string;
    assigned_nurse_id?: string;
    assigned_nurse_name?: string;
  }): Promise<NursingTaskItem> {
    return this.request<NursingTaskItem>('/api/v1/nurse/tasks', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async updateNursingTask(taskId: string, payload: {
    status?: string;
    completion_notes?: string;
    assigned_nurse_id?: string;
    assigned_nurse_name?: string;
  }): Promise<NursingTaskItem> {
    return this.request<NursingTaskItem>(`/api/v1/nurse/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    });
  }

  async listMAR(patientId?: string, statusFilter?: string): Promise<MedicationAdministrationItem[]> {
    const params = new URLSearchParams();
    if (patientId) params.append('patient_id', patientId);
    if (statusFilter) params.append('status_filter', statusFilter);
    return this.request<MedicationAdministrationItem[]>(`/api/v1/nurse/mar?${params.toString()}`);
  }

  async administerMAR(
    marId: string,
    status: 'administered' | 'delayed' | 'refused' | 'missed',
    reason?: string,
    notes?: string
  ): Promise<MedicationAdministrationItem> {
    return this.request<MedicationAdministrationItem>(`/api/v1/nurse/mar/${marId}/administer`, {
      method: 'POST',
      body: JSON.stringify({ status, reason, notes })
    });
  }

  async recordNurseBedsideVitals(payload: {
    patient_id: string;
    systolic_bp?: number;
    diastolic_bp?: number;
    pulse?: number;
    spo2?: number;
    temperature_c?: number;
    fasting_glucose?: number;
    notes?: string;
  }): Promise<any> {
    return this.request<any>('/api/v1/nurse/vitals', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async listShiftHandovers(ward?: string): Promise<ShiftHandoverItem[]> {
    const params = ward ? `?ward=${encodeURIComponent(ward)}` : '';
    return this.request<ShiftHandoverItem[]>(`/api/v1/nurse/handovers${params}`);
  }

  async submitShiftHandover(payload: {
    ward: string;
    shift_type: string;
    outgoing_nurse_name: string;
    incoming_nurse_id?: string;
    incoming_nurse_name?: string;
    situation: string;
    background: string;
    assessment: string;
    recommendation: string;
    critical_alerts?: string[];
    total_patients?: number;
  }): Promise<ShiftHandoverItem> {
    return this.request<ShiftHandoverItem>('/api/v1/nurse/handovers', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }
}

export const api = new ApiClient();
