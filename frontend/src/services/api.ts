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
  TimelineResponse
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
  async getDiabetesRisk(patientId: string): Promise<FutureRiskInsight> {
    return this.request<FutureRiskInsight>(`/api/v1/insights/diabetes-risk/${patientId}`);
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
}

export const api = new ApiClient();
