import React, { useState, useEffect } from 'react';
import { 
  Stethoscope, 
  Calendar, 
  FileCheck2, 
  AlertCircle, 
  Plus, 
  CheckCircle2, 
  ShieldAlert, 
  Activity, 
  RefreshCw, 
  Building2, 
  Search, 
  FileText, 
  Sparkles, 
  ClipboardList, 
  Eye, 
  Microscope, 
  ImageIcon, 
  Send, 
  X, 
  Check,
  FolderHeart 
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { 
  PendingEHRUpdate, 
  AppointmentBooking, 
  DoctorOverviewData, 
  DoctorPatientDirectoryItem, 
  DoctorFullEHR, 
  CopilotDraftNote 
} from '../types';
import { AppointmentTicketModal } from '../components/AppointmentTicketModal';

export const DoctorDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'overview' | 'directory' | 'documentation' | 'copilot'>('overview');
  
  // Doctor Overview State
  const [overview, setOverview] = useState<DoctorOverviewData | null>(null);
  const [pendingUpdates, setPendingUpdates] = useState<PendingEHRUpdate[]>([]);
  const [loading, setLoading] = useState(true);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [activeTicket, setActiveTicket] = useState<AppointmentBooking | null>(null);

  // Patient Directory State
  const [directoryPatients, setDirectoryPatients] = useState<DoctorPatientDirectoryItem[]>([]);
  const [directoryFilter, setDirectoryFilter] = useState('all');
  const [directorySearch, setDirectorySearch] = useState('');
  const [directoryLoading, setDirectoryLoading] = useState(false);

  // Dedicated Longitudinal EHR Modal State
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [patientEHR, setPatientEHR] = useState<DoctorFullEHR | null>(null);
  const [ehrLoading, setEhrLoading] = useState(false);

  // Clinical Documentation State
  const [docPatientId, setDocPatientId] = useState('PAT-AARAV-001');
  const [noteType, setNoteType] = useState('consultation');
  const [noteTitle, setNoteTitle] = useState('');
  const [soapSubjective, setSoapSubjective] = useState('');
  const [soapObjective, setSoapObjective] = useState('');
  const [soapAssessment, setSoapAssessment] = useState('');
  const [soapPlan, setSoapPlan] = useState('');
  const [noteContent, setNoteContent] = useState('');
  const [isSubmittingNote, setIsSubmittingNote] = useState(false);

  // Order State
  const [orderType, setOrderType] = useState<'lab' | 'imaging' | 'procedure'>('lab');
  const [orderName, setOrderName] = useState('Complete Blood Count (CBC) with Differential');
  const [orderIndication, setOrderIndication] = useState('');
  const [orderPriority, setOrderPriority] = useState('routine');
  const [isSubmittingOrder, setIsSubmittingOrder] = useState(false);

  // Direct Entry & Prescription Safety State
  const [showDirectEntryModal, setShowDirectEntryModal] = useState(false);
  const [entryType, setEntryType] = useState<'diagnosis' | 'prescription'>('prescription');
  const [diagnosisName, setDiagnosisName] = useState('');
  const [diagnosisCode, setDiagnosisCode] = useState('I10');
  const [medicationName, setMedicationName] = useState('');
  const [medicationDosage, setMedicationDosage] = useState('1 tablet daily after food');
  const [safetyCheckResult, setSafetyCheckResult] = useState<any>(null);
  const [isSafetyChecking, setIsSafetyChecking] = useState(false);

  // AI Copilot State
  const [copilotFocus, setCopilotFocus] = useState('Hypertension & Asthma Maintenance');
  const [copilotDraft, setCopilotDraft] = useState<CopilotDraftNote | null>(null);
  const [isGeneratingCopilot, setIsGeneratingCopilot] = useState(false);

  const loadDoctorData = async () => {
    setLoading(true);
    try {
      const [ov, pending] = await Promise.all([
        api.getDoctorOverview(),
        api.listPendingVerifications()
      ]);
      setOverview(ov);
      setPendingUpdates(pending);
    } catch (err) {
      console.error('Error loading doctor overview:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadDirectory = async () => {
    setDirectoryLoading(true);
    try {
      const pats = await api.getDoctorPatients(directoryFilter, directorySearch);
      setDirectoryPatients(pats);
    } catch (err) {
      console.error('Error loading patient directory:', err);
    } finally {
      setDirectoryLoading(false);
    }
  };

  useEffect(() => {
    loadDoctorData();
  }, []);

  useEffect(() => {
    if (activeTab === 'directory') {
      loadDirectory();
    }
  }, [activeTab, directoryFilter]);

  const handleOpenEHR = async (patientId: string) => {
    setSelectedPatientId(patientId);
    setEhrLoading(true);
    try {
      const ehr = await api.getDoctorPatientFullEhr(patientId);
      setPatientEHR(ehr);
    } catch (err) {
      console.error('Error loading complete patient EHR:', err);
      alert('Failed to load patient longitudinal EHR.');
    } finally {
      setEhrLoading(false);
    }
  };

  const handleReviewAction = async (updateId: string, action: 'approve' | 'reject') => {
    try {
      await api.reviewPendingVerification(updateId, action, 'Verified by attending physician during clinical review');
      setSuccessMessage(`Update ${updateId} ${action === 'approve' ? 'Approved & Added to Verified EHR' : 'Rejected'}.`);
      const updated = await api.listPendingVerifications();
      setPendingUpdates(updated);
      loadDoctorData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`Review action failed: ${err.message}`);
    }
  };

  const handleUpdateApptStatus = async (bookingId: string, newStatus: string) => {
    try {
      await api.updateAppointmentStatus(bookingId, newStatus);
      setSuccessMessage(`Appointment status updated to ${newStatus}.`);
      loadDoctorData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  const handleRunSafetyCheck = async () => {
    if (!medicationName.trim()) return;
    setIsSafetyChecking(true);
    try {
      const res = await api.checkDrugSafety(docPatientId, medicationName);
      setSafetyCheckResult(res);
    } catch (err: any) {
      console.error('Safety check failed:', err);
    } finally {
      setIsSafetyChecking(false);
    }
  };

  const handleDirectEntrySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (entryType === 'prescription') {
        await api.doctorDirectEntry({
          patient_id: docPatientId,
          entry_type: 'prescription',
          data: {
            medication_name: medicationName,
            dosage: medicationDosage,
            frequency: 'Once Daily',
            route: 'oral',
            start_date: new Date().toISOString().split('T')[0],
            status: 'active'
          }
        });
      } else {
        await api.doctorDirectEntry({
          patient_id: docPatientId,
          entry_type: 'diagnosis',
          data: {
            diagnosis_name: diagnosisName,
            diagnosis_code: diagnosisCode,
            clinical_status: 'active',
            onset_date: new Date().toISOString().split('T')[0]
          }
        });
      }
      setSuccessMessage(`Clinical entry successfully recorded to patient ${docPatientId} EHR.`);
      setShowDirectEntryModal(false);
      setMedicationName('');
      setDiagnosisName('');
      setSafetyCheckResult(null);
      loadDoctorData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`Entry submission failed: ${err.message}`);
    }
  };

  const handleCreateClinicalNote = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingNote(true);
    try {
      await api.createClinicalNote({
        patient_id: docPatientId,
        note_type: noteType,
        title: noteTitle || `${noteType.toUpperCase()} Note`,
        subjective: soapSubjective,
        objective: soapObjective,
        assessment: soapAssessment,
        plan: soapPlan,
        content: noteContent || `${soapSubjective}\n${soapObjective}\n${soapAssessment}\n${soapPlan}`
      });
      setSuccessMessage(`Clinical ${noteType} note successfully signed & stored in EHR.`);
      setNoteTitle('');
      setSoapSubjective('');
      setSoapObjective('');
      setSoapAssessment('');
      setSoapPlan('');
      setNoteContent('');
      if (selectedPatientId) handleOpenEHR(selectedPatientId);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`Failed to save clinical note: ${err.message}`);
    } finally {
      setIsSubmittingNote(false);
    }
  };

  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingOrder(true);
    try {
      await api.createClinicalOrder({
        patient_id: docPatientId,
        order_type: orderType,
        order_name: orderName,
        clinical_indication: orderIndication,
        priority: orderPriority
      });
      setSuccessMessage(`Diagnostic order for "${orderName}" submitted.`);
      setOrderIndication('');
      if (selectedPatientId) handleOpenEHR(selectedPatientId);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`Failed to submit clinical order: ${err.message}`);
    } finally {
      setIsSubmittingOrder(false);
    }
  };

  const handleGenerateCopilotDraft = async () => {
    setIsGeneratingCopilot(true);
    try {
      const draft = await api.generateCopilotDraftNote({
        patient_id: docPatientId,
        clinical_focus: copilotFocus
      });
      setCopilotDraft(draft);
      // Auto-fill form fields
      setNoteTitle(draft.title);
      setSoapSubjective(draft.subjective);
      setSoapObjective(draft.objective);
      setSoapAssessment(draft.assessment);
      setSoapPlan(draft.plan);
    } catch (err: any) {
      alert(`AI Copilot error: ${err.message}`);
    } finally {
      setIsGeneratingCopilot(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-700">
              Physician Workspace
            </span>
            <span className="text-xs text-slate-500">
              {overview?.hospital || (user as any)?.facility || 'Seth GS Medical College & KEM Hospital'}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <Stethoscope className="w-6 h-6 text-blue-600" />
            <span>{user?.role === 'doctor' ? (user?.full_name || 'Dr. Priya Deshmukh') : 'Dr. Priya Deshmukh'} · Clinical Station</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Department: <span className="font-semibold text-slate-700">{overview?.specialty || 'Cardiology & Internal Medicine'}</span> · OP Chamber 104 · Verified Longitudinal EHR Authority
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => { setShowDirectEntryModal(true); setSafetyCheckResult(null); }}
            className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Prescription / Diagnosis</span>
          </button>
          <button
            onClick={() => { loadDoctorData(); if (activeTab === 'directory') loadDirectory(); }}
            className="p-2 border border-slate-200 rounded-xl hover:bg-slate-50 text-slate-600 transition"
            title="Refresh clinical data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            activeTab === 'overview'
              ? 'bg-blue-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Clinical Overview</span>
        </button>

        <button
          onClick={() => setActiveTab('directory')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            activeTab === 'directory'
              ? 'bg-blue-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <FolderHeart className="w-3.5 h-3.5" />
          <span>Patient Directory</span>
        </button>

        <button
          onClick={() => setActiveTab('documentation')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            activeTab === 'documentation'
              ? 'bg-blue-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <ClipboardList className="w-3.5 h-3.5" />
          <span>Clinical Documentation & Orders</span>
        </button>

        <button
          onClick={() => setActiveTab('copilot')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            activeTab === 'copilot'
              ? 'bg-blue-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-300" />
          <span>AI Clinical Copilot</span>
        </button>
      </div>

      {loading && !overview && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-700 flex items-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-blue-600 shrink-0" />
          <span>Loading physician workspace data...</span>
        </div>
      )}

      {successMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* TAB 1: CLINICAL OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 font-medium">Pending Verifications</span>
                <span className="p-1.5 bg-amber-50 text-amber-600 rounded-lg"><FileCheck2 className="w-4 h-4" /></span>
              </div>
              <div className="text-2xl font-black text-slate-900 mt-2">{pendingUpdates.length}</div>
              <span className="text-[10px] text-amber-700 font-medium">Patient chat actions</span>
            </div>

            <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 font-medium">Today's OPD Queue</span>
                <span className="p-1.5 bg-blue-50 text-blue-600 rounded-lg"><Calendar className="w-4 h-4" /></span>
              </div>
              <div className="text-2xl font-black text-slate-900 mt-2">{overview?.stats.today_appointments_count || 0}</div>
              <span className="text-[10px] text-blue-700 font-medium">Confirmed slots</span>
            </div>

            <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 font-medium">Admitted Inpatients</span>
                <span className="p-1.5 bg-indigo-50 text-indigo-600 rounded-lg"><Building2 className="w-4 h-4" /></span>
              </div>
              <div className="text-2xl font-black text-slate-900 mt-2">{overview?.stats.admitted_inpatients_count || 0}</div>
              <span className="text-[10px] text-indigo-700 font-medium">Under care</span>
            </div>

            <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 font-medium">Diagnostic Orders</span>
                <span className="p-1.5 bg-purple-50 text-purple-600 rounded-lg"><Microscope className="w-4 h-4" /></span>
              </div>
              <div className="text-2xl font-black text-slate-900 mt-2">{overview?.stats.pending_orders_count || 0}</div>
              <span className="text-[10px] text-purple-700 font-medium">Lab / Scan tracking</span>
            </div>

            <div className="p-4 bg-white rounded-2xl border border-rose-200 bg-rose-50/30 shadow-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs text-rose-700 font-medium">Critical Alerts</span>
                <span className="p-1.5 bg-rose-100 text-rose-600 rounded-lg"><ShieldAlert className="w-4 h-4" /></span>
              </div>
              <div className="text-2xl font-black text-rose-900 mt-2">{overview?.stats.critical_alerts_count || 0}</div>
              <span className="text-[10px] text-rose-700 font-medium">Immediate attention</span>
            </div>
          </div>

          {/* Critical Alerts Banner */}
          {overview?.critical_alerts && overview.critical_alerts.length > 0 && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl space-y-2">
              <div className="flex items-center gap-2 text-rose-800 font-bold text-xs uppercase tracking-wide">
                <AlertCircle className="w-4 h-4 text-rose-600" />
                <span>Critical Clinical Alerts Triggered</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {overview.critical_alerts.map((al, idx) => (
                  <div key={idx} className="p-2.5 bg-white rounded-xl border border-rose-200/80 text-xs flex items-center justify-between">
                    <div>
                      <span className="font-bold text-slate-900">{al.patient_name}</span> ({al.patient_id})
                      <p className="text-[11px] text-rose-700 font-medium mt-0.5">{al.message}</p>
                    </div>
                    <button
                      onClick={() => handleOpenEHR(al.patient_id)}
                      className="px-2 py-1 bg-rose-100 hover:bg-rose-200 text-rose-800 rounded-lg text-[10px] font-bold"
                    >
                      View EHR
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Pending EHR Verification Queue */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <FileCheck2 className="w-5 h-5 text-amber-500" />
                  <span>Pending Patient EHR Verifications</span>
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Information shared by patients via AI Chat or file uploads awaiting physician verification before being appended to the verified longitudinal record.
                </p>
              </div>
              <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800">
                {pendingUpdates.length} Pending
              </span>
            </div>

            {pendingUpdates.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-xs">
                <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-emerald-400" />
                <span>All patient-submitted EHR entries have been verified and processed.</span>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {pendingUpdates.map((item) => {
                  let parsedProposed: any = {};
                  try {
                    parsedProposed = typeof item.proposed_data === 'string' ? JSON.parse(item.proposed_data) : item.proposed_data;
                  } catch {
                    parsedProposed = { summary: String(item.proposed_data) };
                  }

                  return (
                    <div key={item.update_id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:border-blue-200 transition space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider bg-indigo-100 text-indigo-700">
                          {item.update_type}
                        </span>
                        <span className="text-[11px] text-slate-400">
                          Source: {item.source}
                        </span>
                      </div>

                      <div>
                        <div className="text-xs font-bold text-slate-900">
                          Patient: {item.patient_name || item.patient_id}
                        </div>
                        <div className="text-[11px] text-slate-500 mt-1 bg-white p-2.5 rounded-lg border border-slate-200/80">
                          {Object.entries(parsedProposed).map(([k, v]: [string, any]) => (
                            <div key={k} className="flex justify-between py-0.5 border-b border-slate-100 last:border-0">
                              <span className="capitalize font-medium text-slate-600">{k.replace(/_/g, ' ')}:</span>
                              <span className="font-semibold text-slate-900">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 pt-1">
                        <button
                          onClick={() => handleReviewAction(item.update_id, 'approve')}
                          className="flex-1 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition flex items-center justify-center gap-1"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Approve to EHR</span>
                        </button>
                        <button
                          onClick={() => handleReviewAction(item.update_id, 'reject')}
                          className="px-3 py-1.5 bg-rose-100 hover:bg-rose-200 text-rose-700 rounded-lg text-xs font-bold transition"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Consultation Schedule (OPD Queue) */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-blue-600" />
                  <span>Today's Consultation Schedule & Inpatient Roster</span>
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Real-time OPD queue with check-in verification, electronic prescription slips, and longitudinal record review.
                </p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[11px] uppercase bg-slate-50 text-slate-500 font-semibold border-y border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3">Slot Time</th>
                    <th className="py-2.5 px-3">Patient</th>
                    <th className="py-2.5 px-3">Hospital & Department</th>
                    <th className="py-2.5 px-3">Chief Complaint</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {overview?.today_appointments && overview.today_appointments.length > 0 ? (
                    overview.today_appointments.map((appt) => (
                      <tr key={appt.booking_id} className="hover:bg-slate-50/60 transition">
                        <td className="py-3 px-3 font-bold text-slate-900">{appt.time_slot}</td>
                        <td className="py-3 px-3">
                          <button
                            onClick={() => handleOpenEHR(appt.patient_id)}
                            className="font-bold text-blue-700 hover:underline text-left"
                          >
                            {appt.patient_name}
                          </button>
                          <span className="block text-[10px] text-slate-400">{appt.patient_id}</span>
                        </td>
                        <td className="py-3 px-3">
                          <span className="font-medium text-slate-700">{appt.hospital_name}</span>
                          <span className="block text-[10px] text-slate-400">{appt.department}</span>
                        </td>
                        <td className="py-3 px-3 text-slate-600 max-w-xs truncate">{appt.chief_complaint || 'General Consultation'}</td>
                        <td className="py-3 px-3">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            appt.status === 'confirmed' ? 'bg-blue-100 text-blue-700' :
                            appt.status === 'checked_in' ? 'bg-amber-100 text-amber-700' :
                            appt.status === 'completed' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'
                          }`}>
                            {appt.status.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right space-x-1.5">
                          {appt.status === 'confirmed' && (
                            <button
                              onClick={() => handleUpdateApptStatus(appt.booking_id, 'checked_in')}
                              className="px-2.5 py-1 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-[10px] font-bold"
                            >
                              Check In
                            </button>
                          )}
                          {appt.status === 'checked_in' && (
                            <button
                              onClick={() => handleUpdateApptStatus(appt.booking_id, 'completed')}
                              className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-[10px] font-bold"
                            >
                              Complete
                            </button>
                          )}
                          <button
                            onClick={() => handleOpenEHR(appt.patient_id)}
                            className="px-2.5 py-1 border border-slate-200 hover:bg-slate-100 text-slate-700 rounded-lg text-[10px] font-bold"
                          >
                            Open EHR
                          </button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-slate-400">
                        No appointments booked for today.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: PATIENT DIRECTORY */}
      {activeTab === 'directory' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <FolderHeart className="w-5 h-5 text-blue-600" />
                <span>Authorized Clinical Patient Directory</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Comprehensive directory of patients assigned to your clinical care, inpatient wards, and outpatient clinics.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Search by name or ID..."
                  value={directorySearch}
                  onChange={(e) => setDirectorySearch(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loadDirectory()}
                  className="pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <select
                value={directoryFilter}
                onChange={(e) => setDirectoryFilter(e.target.value)}
                className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium focus:outline-none"
              >
                <option value="all">All Patients</option>
                <option value="admitted">Admitted Inpatients</option>
                <option value="outpatient">Outpatients</option>
                <option value="critical">Critical Cases</option>
              </select>
            </div>
          </div>

          {directoryLoading ? (
            <div className="text-center py-12 text-slate-400 text-xs">Loading patient directory...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[11px] uppercase bg-slate-50 text-slate-500 font-semibold border-y border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3">Patient Name & ID</th>
                    <th className="py-2.5 px-3">Demographics</th>
                    <th className="py-2.5 px-3">Ward / Bed</th>
                    <th className="py-2.5 px-3">Active Diagnoses</th>
                    <th className="py-2.5 px-3">Last Consult</th>
                    <th className="py-2.5 px-3">Next Appt</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {directoryPatients.map((p) => (
                    <tr key={p.patient_id} className="hover:bg-slate-50/60 transition">
                      <td className="py-3 px-3">
                        <div className="font-bold text-slate-900 flex items-center gap-1.5">
                          <span>{p.full_name}</span>
                          {p.critical_alert && (
                            <span className="w-2 h-2 rounded-full bg-rose-500" title="Critical Clinical Alert Active" />
                          )}
                        </div>
                        <span className="text-[10px] text-slate-400">{p.patient_id} · {p.clinical_status}</span>
                      </td>
                      <td className="py-3 px-3 text-slate-600">
                        {p.age}y / {p.gender} · {p.district}
                      </td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${
                          p.is_admitted ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'
                        }`}>
                          {p.is_admitted ? `${p.ward} (${p.bed_number})` : 'Ambulatory'}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex flex-wrap gap-1">
                          {p.active_diagnoses.map((diag, i) => (
                            <span key={i} className="px-1.5 py-0.5 bg-slate-100 rounded text-[10px] text-slate-700">
                              {diag}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-slate-600">{p.last_consultation}</td>
                      <td className="py-3 px-3 text-slate-600">{p.next_appointment}</td>
                      <td className="py-3 px-3 text-right space-x-1.5">
                        <button
                          onClick={() => handleOpenEHR(p.patient_id)}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition inline-flex items-center gap-1"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View Complete EHR</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: CLINICAL DOCUMENTATION & ORDERS */}
      {activeTab === 'documentation' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Note Editor */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-600" />
                <span>Physician Clinical Documentation</span>
              </h2>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">SOAP / Progress Note</span>
            </div>

            <form onSubmit={handleCreateClinicalNote} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Target Patient *</label>
                  <select
                    value={docPatientId}
                    onChange={(e) => setDocPatientId(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  >
                    <option value="PAT-AARAV-001">Aarav Mehta (PAT-AARAV-001)</option>
                    <option value="PAT-PRIYA-002">Priya Mehta (PAT-PRIYA-002)</option>
                    <option value="PAT-SUNITA-004">Sunita Mehta (PAT-SUNITA-004)</option>
                    <option value="PAT-ROHAN-003">Rohan Mehta (PAT-ROHAN-003)</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Documentation Type</label>
                  <select
                    value={noteType}
                    onChange={(e) => setNoteType(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  >
                    <option value="consultation">OPD Consultation Note</option>
                    <option value="progress_note">Inpatient Progress Note</option>
                    <option value="soap_note">SOAP Structured Note</option>
                    <option value="discharge_summary">Discharge Summary</option>
                    <option value="treatment_plan">Treatment Plan</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Note Title</label>
                <input
                  type="text"
                  placeholder="e.g. Follow-Up: Asthma Control & Hypertension Review"
                  value={noteTitle}
                  onChange={(e) => setNoteTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Subjective (S)</label>
                <textarea
                  rows={2}
                  placeholder="Patient symptoms, interval history, adherence, complaints..."
                  value={soapSubjective}
                  onChange={(e) => setSoapSubjective(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Objective (O)</label>
                <textarea
                  rows={2}
                  placeholder="Physical findings, current vitals, chest auscultation, labs..."
                  value={soapObjective}
                  onChange={(e) => setSoapObjective(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Assessment (A)</label>
                <textarea
                  rows={2}
                  placeholder="Diagnostic impression, stability, disease severity..."
                  value={soapAssessment}
                  onChange={(e) => setSoapAssessment(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Plan (P)</label>
                <textarea
                  rows={2}
                  placeholder="Medications, dosing, investigations ordered, follow-up..."
                  value={soapPlan}
                  onChange={(e) => setSoapPlan(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmittingNote}
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold transition flex items-center justify-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Sign & Save Clinical Note to EHR</span>
              </button>
            </form>
          </div>

          {/* Diagnostic Orders Form */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Microscope className="w-5 h-5 text-purple-600" />
                <span>Diagnostic & Imaging Orders</span>
              </h2>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Lab / Radiology</span>
            </div>

            <form onSubmit={handleCreateOrder} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Patient</label>
                <select
                  value={docPatientId}
                  onChange={(e) => setDocPatientId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                >
                  <option value="PAT-AARAV-001">Aarav Mehta (PAT-AARAV-001)</option>
                  <option value="PAT-PRIYA-002">Priya Mehta (PAT-PRIYA-002)</option>
                  <option value="PAT-SUNITA-004">Sunita Mehta (PAT-SUNITA-004)</option>
                  <option value="PAT-ROHAN-003">Rohan Mehta (PAT-ROHAN-003)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Order Category</label>
                  <select
                    value={orderType}
                    onChange={(e: any) => setOrderType(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  >
                    <option value="lab">Laboratory Investigation</option>
                    <option value="imaging">Radiology / Imaging (X-Ray/MRI/CT)</option>
                    <option value="procedure">Clinical Procedure</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Priority</label>
                  <select
                    value={orderPriority}
                    onChange={(e) => setOrderPriority(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  >
                    <option value="routine">Routine</option>
                    <option value="urgent">Urgent</option>
                    <option value="stat">STAT / Immediate</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Investigation Name</label>
                <input
                  type="text"
                  placeholder="e.g. Chest X-Ray PA View, High-Resolution CT, Lipid Panel"
                  value={orderName}
                  onChange={(e) => setOrderName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Clinical Indication & Instructions</label>
                <textarea
                  rows={3}
                  placeholder="Reason for ordering test, suspected diagnosis, specific views..."
                  value={orderIndication}
                  onChange={(e) => setOrderIndication(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmittingOrder}
                className="w-full py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-bold transition flex items-center justify-center gap-1.5"
              >
                <Microscope className="w-3.5 h-3.5" />
                <span>Submit Diagnostic Order</span>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* TAB 4: AI CLINICAL COPILOT */}
      {activeTab === 'copilot' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-500" />
                <span>AI Clinical Copilot & Longitudinal History Synthesizer</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Assists physicians by synthesizing patient medical history, highlighting drug-allergy interactions, and generating draft consultation notes for review.
              </p>
            </div>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex flex-col md:flex-row md:items-center gap-3">
            <div className="flex-1">
              <label className="block text-xs font-semibold text-slate-700 mb-1">Select Patient</label>
              <select
                value={docPatientId}
                onChange={(e) => setDocPatientId(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-xs"
              >
                <option value="PAT-AARAV-001">Aarav Mehta (PAT-AARAV-001) - Asthma & Hypertension</option>
                <option value="PAT-PRIYA-002">Priya Mehta (PAT-PRIYA-002)</option>
                <option value="PAT-SUNITA-004">Sunita Mehta (PAT-SUNITA-004) - T2D & HTN</option>
                <option value="PAT-ROHAN-003">Rohan Mehta (PAT-ROHAN-003)</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-xs font-semibold text-slate-700 mb-1">Clinical Focus</label>
              <input
                type="text"
                value={copilotFocus}
                onChange={(e) => setCopilotFocus(e.target.value)}
                placeholder="e.g. Asthma control and cardiovascular risk"
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl text-xs"
              />
            </div>
            <div className="self-end">
              <button
                onClick={handleGenerateCopilotDraft}
                disabled={isGeneratingCopilot}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                <span>{isGeneratingCopilot ? 'Synthesizing...' : 'Generate Draft SOAP Note'}</span>
              </button>
            </div>
          </div>

          {copilotDraft && (
            <div className="p-4 bg-blue-50/50 border border-blue-200 rounded-2xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                  {copilotDraft.draft_status}
                </span>
                <span className="text-[11px] text-slate-400">
                  Generated by: {copilotDraft.generated_by}
                </span>
              </div>

              <h3 className="font-bold text-slate-900 text-sm">{copilotDraft.title}</h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-white rounded-xl border border-slate-200">
                  <span className="font-bold text-blue-700 block mb-1">Subjective (S)</span>
                  <p className="text-slate-700 leading-relaxed">{copilotDraft.subjective}</p>
                </div>
                <div className="p-3 bg-white rounded-xl border border-slate-200">
                  <span className="font-bold text-blue-700 block mb-1">Objective (O)</span>
                  <p className="text-slate-700 leading-relaxed">{copilotDraft.objective}</p>
                </div>
                <div className="p-3 bg-white rounded-xl border border-slate-200">
                  <span className="font-bold text-blue-700 block mb-1">Assessment (A)</span>
                  <p className="text-slate-700 leading-relaxed whitespace-pre-line">{copilotDraft.assessment}</p>
                </div>
                <div className="p-3 bg-white rounded-xl border border-slate-200">
                  <span className="font-bold text-blue-700 block mb-1">Plan (P)</span>
                  <p className="text-slate-700 leading-relaxed whitespace-pre-line">{copilotDraft.plan}</p>
                </div>
              </div>

              {copilotDraft.suggested_investigations && copilotDraft.suggested_investigations.length > 0 && (
                <div className="p-3 bg-white rounded-xl border border-slate-200 text-xs">
                  <span className="font-bold text-purple-700 block mb-1">Suggested Investigations:</span>
                  <ul className="list-disc pl-4 space-y-0.5 text-slate-600">
                    {copilotDraft.suggested_investigations.map((inv, idx) => (
                      <li key={idx}>{inv}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => {
                    setActiveTab('documentation');
                  }}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition"
                >
                  Edit & Sign in Clinical Documentation
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* DEDICATED LONGITUDINAL EHR MODAL */}
      {ehrLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl p-6 shadow-xl flex items-center gap-3">
            <RefreshCw className="w-5 h-5 animate-spin text-blue-600" />
            <span className="text-sm font-medium text-slate-700">Loading complete longitudinal EHR...</span>
          </div>
        </div>
      )}

      {selectedPatientId && patientEHR && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs overflow-y-auto">
          <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto border border-slate-200 shadow-2xl p-6 space-y-6 animate-in fade-in zoom-in-95">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-200 pb-4">
              <div>
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px] font-bold uppercase">
                  Longitudinal Health Record
                </span>
                <h2 className="text-xl font-bold text-slate-900 mt-1">
                  {patientEHR.demographics.first_name} {patientEHR.demographics.last_name} ({patientEHR.patient_id})
                </h2>
                <p className="text-xs text-slate-500">
                  {patientEHR.demographics.age}yo {patientEHR.demographics.gender} · Blood Group: {patientEHR.demographics.blood_group} · {patientEHR.demographics.district}
                </p>
              </div>
              <button
                onClick={() => { setSelectedPatientId(null); setPatientEHR(null); }}
                className="p-2 hover:bg-slate-100 rounded-xl text-slate-500"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Allergies & Drug Interactions Alerts */}
            {patientEHR.allergies && patientEHR.allergies.length > 0 && (
              <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl space-y-1.5">
                <span className="text-xs font-bold text-rose-800 uppercase flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-rose-600" />
                  Verified Drug & Substance Allergies
                </span>
                <div className="flex flex-wrap gap-2">
                  {patientEHR.allergies.map((alg: any) => (
                    <span key={alg.allergy_id} className="px-2 py-1 bg-white border border-rose-200 rounded-lg text-xs font-medium text-rose-900">
                      <strong>{alg.substance}:</strong> {alg.reaction} ({alg.severity})
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Diagnoses & Active Medications */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                <span className="font-bold text-slate-900 block text-xs uppercase tracking-wider">
                  Active & Historical Diagnoses
                </span>
                <div className="space-y-1.5">
                  {patientEHR.conditions.map((c: any, i: number) => (
                    <div key={i} className="p-2 bg-white rounded-lg border border-slate-200/80 flex items-center justify-between">
                      <span className="font-semibold text-slate-800">{c.diagnosis_name}</span>
                      <span className="text-[10px] text-slate-400">{c.code} · {c.status}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                <span className="font-bold text-slate-900 block text-xs uppercase tracking-wider">
                  Current Medications & Dosage
                </span>
                <div className="space-y-1.5">
                  {patientEHR.medications.map((m: any, i: number) => (
                    <div key={i} className="p-2 bg-white rounded-lg border border-slate-200/80 flex items-center justify-between">
                      <span className="font-semibold text-slate-800">{m.medication_name}</span>
                      <span className="text-[10px] text-blue-700 font-medium">{m.dosage}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Medical Imaging & Radiologic Scans */}
            <div className="space-y-2">
              <span className="font-bold text-slate-900 block text-xs uppercase tracking-wider flex items-center gap-1.5">
                <ImageIcon className="w-4 h-4 text-blue-600" />
                Radiological Imaging & Medical Scans (X-Ray, HRCT, MRI)
              </span>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {patientEHR.imaging_scans && patientEHR.imaging_scans.length > 0 ? (
                  patientEHR.imaging_scans.map((scan: any) => (
                    <div key={scan.document_id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 truncate">{scan.file_name.replace(/_/g, ' ')}</span>
                      </div>
                      <span className="text-[10px] text-slate-400 block">Report Date: {scan.report_date}</span>
                      <p className="text-[11px] text-slate-600 line-clamp-3 bg-white p-2 rounded border border-slate-200/80">
                        {scan.extracted_text}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="col-span-3 text-center py-4 text-slate-400 text-xs">No radiology scans on file.</div>
                )}
              </div>
            </div>

            {/* Laboratory Observations */}
            <div className="space-y-2">
              <span className="font-bold text-slate-900 block text-xs uppercase tracking-wider flex items-center gap-1.5">
                <Microscope className="w-4 h-4 text-purple-600" />
                Laboratory Test Results
              </span>
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-slate-50 text-slate-500 font-semibold border-y border-slate-200">
                    <tr>
                      <th className="py-2 px-2.5">Test Name</th>
                      <th className="py-2 px-2.5">Result</th>
                      <th className="py-2 px-2.5">Reference Range</th>
                      <th className="py-2 px-2.5">Interpretation</th>
                      <th className="py-2 px-2.5">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {patientEHR.observations.map((obs: any, i: number) => (
                      <tr key={i} className="hover:bg-slate-50/50">
                        <td className="py-2 px-2.5 font-medium text-slate-800">{obs.test_name}</td>
                        <td className="py-2 px-2.5 font-bold text-slate-900">{obs.value_numeric} {obs.unit}</td>
                        <td className="py-2 px-2.5 text-slate-500">{obs.reference_range}</td>
                        <td className="py-2 px-2.5">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            obs.interpretation === 'NORMAL' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                          }`}>
                            {obs.interpretation}
                          </span>
                        </td>
                        <td className="py-2 px-2.5 text-slate-500">{obs.date}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Clinical Notes Written by Doctors */}
            <div className="space-y-2">
              <span className="font-bold text-slate-900 block text-xs uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-blue-600" />
                Clinical Notes & Discharge Summaries
              </span>
              <div className="space-y-2">
                {patientEHR.clinical_notes && patientEHR.clinical_notes.length > 0 ? (
                  patientEHR.clinical_notes.map((n: any) => (
                    <div key={n.note_id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900">{n.title}</span>
                        <span className="text-[10px] text-slate-400">{n.created_at} · by {n.doctor_name}</span>
                      </div>
                      <p className="text-slate-700 leading-relaxed">{n.content}</p>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-4 text-slate-400 text-xs">No clinical notes recorded yet.</div>
                )}
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex justify-end gap-2 pt-4 border-t border-slate-200">
              <button
                onClick={() => {
                  setDocPatientId(selectedPatientId);
                  setSelectedPatientId(null);
                  setActiveTab('documentation');
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition"
              >
                Document Consultation Note
              </button>
              <button
                onClick={() => { setSelectedPatientId(null); setPatientEHR(null); }}
                className="px-4 py-2 border border-slate-200 hover:bg-slate-100 rounded-xl text-xs font-semibold text-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* DIRECT CLINICAL ENTRY MODAL */}
      {showDirectEntryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl w-full max-w-lg border border-slate-200 shadow-xl p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Stethoscope className="w-4 h-4 text-blue-600" />
                <span>Physician Direct Clinical Entry</span>
              </h3>
              <button onClick={() => setShowDirectEntryModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleDirectEntrySubmit} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Select Patient *</label>
                <select
                  value={docPatientId}
                  onChange={(e) => setDocPatientId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-medium"
                >
                  <option value="PAT-AARAV-001">Aarav Mehta (PAT-AARAV-001)</option>
                  <option value="PAT-PRIYA-002">Priya Mehta (PAT-PRIYA-002)</option>
                  <option value="PAT-SUNITA-004">Sunita Mehta (PAT-SUNITA-004)</option>
                  <option value="PAT-ROHAN-003">Rohan Mehta (PAT-ROHAN-003)</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Order Type</label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setEntryType('prescription')}
                    className={`flex-1 py-1.5 rounded-lg border font-bold ${
                      entryType === 'prescription' ? 'bg-blue-50 border-blue-600 text-blue-700' : 'bg-slate-50 border-slate-200 text-slate-600'
                    }`}
                  >
                    Prescribe Medication
                  </button>
                  <button
                    type="button"
                    onClick={() => setEntryType('diagnosis')}
                    className={`flex-1 py-1.5 rounded-lg border font-bold ${
                      entryType === 'diagnosis' ? 'bg-blue-50 border-blue-600 text-blue-700' : 'bg-slate-50 border-slate-200 text-slate-600'
                    }`}
                  >
                    Add Diagnosis
                  </button>
                </div>
              </div>

              {entryType === 'prescription' ? (
                <>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Medication Name *</label>
                    <input
                      type="text"
                      placeholder="e.g. Budesonide Inhaler, Amlodipine 5mg"
                      value={medicationName}
                      onChange={(e) => setMedicationName(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                      required
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Dosage & Instructions</label>
                    <input
                      type="text"
                      value={medicationDosage}
                      onChange={(e) => setMedicationDosage(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                      required
                    />
                  </div>

                  <button
                    type="button"
                    onClick={handleRunSafetyCheck}
                    disabled={isSafetyChecking || !medicationName.trim()}
                    className="w-full py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-bold flex items-center justify-center gap-1.5"
                  >
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
                    <span>{isSafetyChecking ? 'Checking interactions...' : 'Run Drug-Drug & Allergy Safety Check'}</span>
                  </button>

                  {safetyCheckResult && (
                    <div className={`p-2.5 rounded-lg border text-[11px] ${
                      safetyCheckResult.safe ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-amber-50 border-amber-200 text-amber-800'
                    }`}>
                      <span className="font-bold block">{safetyCheckResult.safe ? 'Safe to Prescribe' : 'Potential Warning'}</span>
                      <p>{safetyCheckResult.message || safetyCheckResult.reason || 'No clinical contraindications found.'}</p>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Diagnosis Name *</label>
                    <input
                      type="text"
                      placeholder="e.g. Bronchial Asthma, Type 2 Diabetes"
                      value={diagnosisName}
                      onChange={(e) => setDiagnosisName(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                      required
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">ICD-10 Code</label>
                    <input
                      type="text"
                      value={diagnosisCode}
                      onChange={(e) => setDiagnosisCode(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                      required
                    />
                  </div>
                </>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowDirectEntryModal(false)}
                  className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold"
                >
                  Record to Verified EHR
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Printable Consultation Ticket */}
      {activeTicket && (
        <AppointmentTicketModal
          ticket={activeTicket as any}
          onClose={() => setActiveTicket(null)}
        />
      )}
    </div>
  );
};
