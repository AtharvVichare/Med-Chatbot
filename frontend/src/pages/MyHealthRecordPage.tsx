import React, { useEffect, useState } from 'react';
import { 
  User, 
  Activity, 
  Pill, 
  AlertCircle, 
  FileText, 
  Clock, 
  Plus, 
  Trash2, 
  Upload, 
  X,
  FileCheck,
  TrendingUp,
  BarChart3,
  ExternalLink,
  Eye,
  Download,
  Calendar,
  Ticket,
  Building2,
  Printer
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { 
  Patient, 
  Condition, 
  Medication, 
  Allergy, 
  PatientDocument, 
  TimelineResponse,
  AppointmentBooking
} from '../types';
import { AppointmentTicketModal } from '../components/AppointmentTicketModal';

export const MyHealthRecordPage: React.FC = () => {
  const { user } = useAuth();
  const patientId = user?.patient_id || 'PAT-AARAV-001';

  const [activeTab, setActiveTab] = useState<'profile' | 'conditions' | 'medications' | 'allergies' | 'reports' | 'timeline' | 'trends' | 'appointments'>('profile');
  const [patient, setPatient] = useState<Patient | null>(null);
  const [conditions, setConditions] = useState<Condition[]>([]);
  const [medications, setMedications] = useState<Medication[]>([]);
  const [allergies, setAllergies] = useState<Allergy[]>([]);
  const [documents, setDocuments] = useState<PatientDocument[]>([]);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [appointments, setAppointments] = useState<AppointmentBooking[]>([]);
  const [activeTicket, setActiveTicket] = useState<AppointmentBooking | null>(null);
  const [loading, setLoading] = useState(true);

  // Longitudinal Trends State
  const [selectedMetric, setSelectedMetric] = useState<string>('blood_pressure');
  const [trendsData, setTrendsData] = useState<any | null>(null);
  const [trendsLoading, setTrendsLoading] = useState(false);

  // Modals state
  const [previewDoc, setPreviewDoc] = useState<PatientDocument | null>(null);
  const [showAddConditionModal, setShowAddConditionModal] = useState(false);
  const [newConditionName, setNewConditionName] = useState('');
  const [newConditionCode, setNewConditionCode] = useState('R69');
  const [newConditionDate, setNewConditionDate] = useState(new Date().toISOString().split('T')[0]);

  const [showAddMedModal, setShowAddMedModal] = useState(false);
  const [newMedName, setNewMedName] = useState('');
  const [newMedDosage, setNewMedDosage] = useState('');
  const [newMedFrequency, setNewMedFrequency] = useState('');
  const [newMedDoctor, setNewMedDoctor] = useState('');

  const [showAddAllergyModal, setShowAddAllergyModal] = useState(false);
  const [newAllergySubstance, setNewAllergySubstance] = useState('');
  const [newAllergyReaction, setNewAllergyReaction] = useState('');
  const [newAllergySeverity, setNewAllergySeverity] = useState('moderate');
  const [newAllergyCategory, setNewAllergyCategory] = useState('medication');

  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docType, setDocType] = useState('lab_report');
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadSuccessMsg, setUploadSuccessMsg] = useState<string | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    try {
      await api.downloadEhrPdf(patientId);
    } catch (err: any) {
      alert(err.message || 'Failed to download longitudinal EHR PDF');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const fetchRecordData = async () => {
    setLoading(true);
    try {
      const [pat, conds, meds, allgs, docs, time, appts] = await Promise.allSettled([
        api.getPatient(patientId),
        api.getPatientConditions(patientId),
        api.getPatientMedications(patientId),
        api.getPatientAllergies(patientId),
        api.getPatientDocuments(patientId),
        api.getPatientTimeline(patientId),
        api.listAppointments({ patient_id: patientId })
      ]);

      if (pat.status === 'fulfilled') setPatient(pat.value);
      if (conds.status === 'fulfilled') setConditions(conds.value);
      if (meds.status === 'fulfilled') setMedications(meds.value);
      if (allgs.status === 'fulfilled') setAllergies(allgs.value);
      if (docs.status === 'fulfilled') setDocuments(docs.value);
      if (time.status === 'fulfilled') setTimeline(time.value);
      if (appts.status === 'fulfilled') setAppointments(appts.value);
    } catch (e) {
      console.error('Error fetching health record:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelAppointment = async (bookingId: string) => {
    if (!window.confirm('Are you sure you want to cancel this scheduled consultation?')) return;
    try {
      await api.cancelAppointment(bookingId);
      fetchRecordData();
    } catch (err: any) {
      alert(`Failed to cancel: ${err.message}`);
    }
  };

  const fetchTrends = async (metricKey: string) => {
    setTrendsLoading(true);
    try {
      const data = await api.getLongitudinalTrends(patientId, metricKey);
      setTrendsData(data);
    } catch (err) {
      console.error('Failed to load trends:', err);
    } finally {
      setTrendsLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'trends') {
      fetchTrends(selectedMetric);
    }
  }, [activeTab, selectedMetric, patientId]);

  useEffect(() => {
    fetchRecordData();
  }, [patientId]);

  // Actions
  const handleAddCondition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newConditionName) return;
    try {
      await api.addPatientCondition(patientId, {
        condition_code: newConditionCode || 'R69',
        condition_name: newConditionName,
        onset_date: newConditionDate,
        category: 'patient_reported'
      });
      setShowAddConditionModal(false);
      setNewConditionName('');
      fetchRecordData();
    } catch (err: any) {
      alert(err.message || 'Failed to add condition');
    }
  };

  const handleAddMedication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMedName) return;
    try {
      await api.addPatientMedication(patientId, {
        medication_name: newMedName,
        dosage: newMedDosage,
        frequency: newMedFrequency,
        prescribing_doctor: newMedDoctor,
        start_date: new Date().toISOString().split('T')[0]
      });
      setShowAddMedModal(false);
      setNewMedName('');
      setNewMedDosage('');
      setNewMedFrequency('');
      setNewMedDoctor('');
      fetchRecordData();
    } catch (err: any) {
      alert(err.message || 'Failed to add medication');
    }
  };

  const handleDiscontinueMed = async (medId: string) => {
    if (!confirm('Are you sure you want to discontinue this active medication?')) return;
    try {
      await api.discontinuePatientMedication(patientId, medId);
      fetchRecordData();
    } catch (err: any) {
      alert(err.message || 'Failed to discontinue medication');
    }
  };

  const handleAddAllergy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAllergySubstance || !newAllergyReaction) return;
    try {
      await api.addPatientAllergy(patientId, {
        substance: newAllergySubstance,
        reaction: newAllergyReaction,
        severity: newAllergySeverity,
        category: newAllergyCategory
      });
      setShowAddAllergyModal(false);
      setNewAllergySubstance('');
      setNewAllergyReaction('');
      fetchRecordData();
    } catch (err: any) {
      alert(err.message || 'Failed to add allergy');
    }
  };

  const handleDeleteAllergy = async (allergyId: string) => {
    if (!confirm('Remove this allergy record?')) return;
    try {
      await api.deletePatientAllergy(patientId, allergyId);
      fetchRecordData();
    } catch (err: any) {
      alert(err.message || 'Failed to delete allergy');
    }
  };

  const handleUploadDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    setUploadLoading(true);
    setUploadSuccessMsg(null);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('document_type', docType);
      formData.append('patient_id', patientId);
      await api.uploadPatientDocument(formData);
      setUploadSuccessMsg(`Document uploaded successfully! Extracted data ready for review.`);
      setSelectedFile(null);
      fetchRecordData();
    } catch (err: any) {
      alert(err.message || 'Upload failed');
    } finally {
      setUploadLoading(false);
    }
  };

  const handleConfirmDocument = async (docId: string) => {
    try {
      const res = await api.confirmPatientDocument(docId);
      alert(`Success: ${res.message} (${res.observations_created} measurements recorded to vitals).`);
      fetchRecordData();
    } catch (err: any) {
      alert(err.message || 'Confirmation failed');
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">My Health Record</h1>
          <p className="text-xs text-slate-500 mt-1">
            Longitudinal electronic health history for Patient ID: <span className="font-semibold text-teal-700">{patientId}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-sm transition"
            title="Download full longitudinal health record as an organized clinical PDF report"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{downloadingPdf ? 'Exporting PDF...' : 'Download Complete EHR (PDF)'}</span>
          </button>
          <button
            onClick={() => setShowUploadModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-xl shadow-sm transition"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload Medical Report</span>
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex border-b border-slate-200 overflow-x-auto gap-1 text-xs font-medium">
        {[
          { id: 'profile', label: 'Clinical Profile', icon: User },
          { id: 'conditions', label: `Active Conditions (${conditions.length})`, icon: Activity },
          { id: 'medications', label: `Medications (${medications.length})`, icon: Pill },
          { id: 'allergies', label: `Allergies (${allergies.length})`, icon: AlertCircle },
          { id: 'reports', label: `Diagnostic Reports (${documents.length})`, icon: FileText },
          { id: 'timeline', label: 'Unified Timeline', icon: Clock },
          { id: 'trends', label: 'Longitudinal Trends & Charts', icon: TrendingUp },
          { id: 'appointments', label: `Appointments & History (${appointments.length})`, icon: Calendar },
        ].map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 font-semibold whitespace-nowrap transition-colors ${
                isActive
                  ? 'border-teal-600 text-teal-700 bg-teal-50/40'
                  : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-teal-600' : 'text-slate-400'}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {loading && (
        <div className="p-3 bg-teal-50 border border-teal-200 rounded-xl text-teal-800 text-xs font-medium">
          Synchronizing longitudinal health records...
        </div>
      )}

      {/* Tab 1: Clinical Profile */}
      {activeTab === 'profile' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <h2 className="text-base font-bold text-slate-900">Demographic & Patient Details</h2>
              <p className="text-xs text-slate-500">Official patient identification in Aarogya Drishti registry</p>
            </div>
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Active Record
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 text-sm">
            <div>
              <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Full Legal Name</span>
              <p className="mt-1 font-semibold text-slate-900">
                {patient ? `${patient.first_name} ${patient.last_name}` : (user?.full_name || 'Aarav Mehta')}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Date of Birth & Age</span>
              <p className="mt-1 font-semibold text-slate-900">
                {patient?.date_of_birth ? `${patient.date_of_birth}` : '1988-05-14'}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Biological Sex</span>
              <p className="mt-1 font-semibold text-slate-900 capitalize">
                {patient?.gender || 'Male'}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Blood Type</span>
              <p className="mt-1 font-semibold text-slate-900">
                {patient?.blood_type || 'O+'}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Residential District</span>
              <p className="mt-1 font-semibold text-slate-900">
                {patient?.district ? `${patient.district}, Maharashtra` : 'Mumbai, Maharashtra'}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Primary Phone</span>
              <p className="mt-1 font-semibold text-slate-900">
                {patient?.phone_number || '+91 98201 11223'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Conditions */}
      {activeTab === 'conditions' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <h2 className="text-base font-bold text-slate-900">Diagnosed & Reported Medical Conditions</h2>
              <p className="text-xs text-slate-500">Longitudinal chronic and acute conditions recorded in EHR</p>
            </div>
            <button
              onClick={() => setShowAddConditionModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-50 text-teal-700 hover:bg-teal-100 rounded-lg text-xs font-semibold transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Condition</span>
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {conditions.length === 0 ? (
              <p className="py-6 text-center text-xs text-slate-500">No medical conditions recorded.</p>
            ) : (
              conditions.map(c => (
                <div key={c.condition_id} className="py-3.5 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-900 text-sm">{c.condition_name || c.description}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-100 text-slate-600">
                        {c.condition_code || c.code}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Onset: {c.onset_date || 'Undated'} · Category: {c.category || 'General'}
                    </p>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-medium capitalize ${
                    c.clinical_status === 'active' ? 'bg-amber-50 text-amber-800' : 'bg-slate-100 text-slate-700'
                  }`}>
                    {c.clinical_status}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Medications */}
      {activeTab === 'medications' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <h2 className="text-base font-bold text-slate-900">Medication Regimen & Prescriptions</h2>
              <p className="text-xs text-slate-500">Active and discontinued prescriptions</p>
            </div>
            <button
              onClick={() => setShowAddMedModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-50 text-teal-700 hover:bg-teal-100 rounded-lg text-xs font-semibold transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Medication</span>
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {medications.length === 0 ? (
              <p className="py-6 text-center text-xs text-slate-500">No medications on record.</p>
            ) : (
              medications.map(m => (
                <div key={m.medication_id} className="py-3.5 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-900 text-sm">{m.medication_name}</span>
                      {m.dosage && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-teal-50 text-teal-700">
                          {m.dosage}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {m.frequency ? `Frequency: ${m.frequency}` : ''} · Prescribed by: {m.prescribing_doctor || 'Self-Reported'}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium capitalize ${
                      m.status === 'active' ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-100 text-slate-500 line-through'
                    }`}>
                      {m.status}
                    </span>
                    {m.status === 'active' && (
                      <button
                        onClick={() => handleDiscontinueMed(m.medication_id)}
                        className="text-xs text-rose-600 hover:text-rose-800 font-medium"
                      >
                        Discontinue
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Allergies */}
      {activeTab === 'allergies' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <h2 className="text-base font-bold text-slate-900">Allergies & Adverse Reactions</h2>
              <p className="text-xs text-slate-500">Critical drug, food, and environmental hypersensitivities</p>
            </div>
            <button
              onClick={() => setShowAddAllergyModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 text-rose-700 hover:bg-rose-100 rounded-lg text-xs font-semibold transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Allergy</span>
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {allergies.length === 0 ? (
              <p className="py-6 text-center text-xs text-slate-500">No known allergies recorded.</p>
            ) : (
              allergies.map(a => (
                <div key={a.allergy_id} className="py-3.5 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-900 text-sm">{a.substance}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-rose-50 text-rose-700">
                        {a.severity}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Reaction: <span className="font-medium text-slate-700">{a.reaction}</span> · Category: {a.category}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteAllergy(a.allergy_id)}
                    className="p-1.5 text-slate-400 hover:text-rose-600 rounded transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 5: Diagnostic Reports */}
      {activeTab === 'reports' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <h2 className="text-base font-bold text-slate-900">Uploaded Lab & Diagnostic Reports</h2>
              <p className="text-xs text-slate-500">Extracted clinical metrics and verified documentation</p>
            </div>
            <button
              onClick={() => setShowUploadModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-lg text-xs font-semibold transition"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Upload Document</span>
            </button>
          </div>

          <div className="space-y-4">
            {documents.length === 0 ? (
              <p className="py-6 text-center text-xs text-slate-500">No diagnostic reports uploaded yet.</p>
            ) : (
              documents.map(d => {
                let parsedMeta: any = {};
                try {
                  if (d.extracted_metadata) parsedMeta = JSON.parse(d.extracted_metadata);
                } catch {}

                return (
                  <div key={d.document_id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-lg bg-teal-100 text-teal-700 flex items-center justify-center font-bold">
                          <FileCheck className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="text-sm font-bold text-slate-900">{d.file_name}</p>
                          <p className="text-xs text-slate-500">
                            Uploaded on {new Date(d.created_at).toLocaleDateString()} · {(d.file_size_bytes / 1024).toFixed(1)} KB
                          </p>
                        </div>
                      </div>
                      <span className={`px-2.5 py-0.5 rounded text-xs font-semibold ${
                        d.confirmation_status === 'confirmed'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}>
                        {d.confirmation_status === 'confirmed' ? 'Verified in Record' : 'Pending Confirmation'}
                      </span>
                    </div>

                    {/* Extracted Lab Metrics preview */}
                    {parsedMeta.observations && parsedMeta.observations.length > 0 && (
                      <div className="bg-white p-3 rounded-lg border border-slate-200 text-xs">
                        <span className="font-semibold text-slate-700 block mb-1.5">Extracted Diagnostic Values:</span>
                        <div className="flex flex-wrap gap-2">
                          {parsedMeta.observations.map((obs: any, idx: number) => (
                            <span key={idx} className="px-2 py-1 rounded bg-teal-50 text-teal-800 font-medium">
                              {obs.name}: <strong>{obs.value}</strong> {obs.unit}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Actions & Preview Buttons */}
                    <div className="flex items-center justify-between pt-2 border-t border-slate-200/60">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setPreviewDoc(d)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-50 hover:bg-teal-100 text-teal-800 text-xs font-semibold transition"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View Scan / Document</span>
                        </button>
                        <a
                          href={api.getDocumentFileUrl(d.document_id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs transition"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Open in New Tab</span>
                        </a>
                      </div>

                      {d.confirmation_status === 'pending_review' && (
                        <button
                          onClick={() => handleConfirmDocument(d.document_id)}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
                        >
                          Confirm & Save Values to Health Record
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* Tab 6: Unified Timeline */}
      {activeTab === 'timeline' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm space-y-6">
          <div className="pb-4 border-b border-slate-100">
            <h2 className="text-base font-bold text-slate-900">Chronological Longitudinal Health Timeline</h2>
            <p className="text-xs text-slate-500">Integrated view of encounters, conditions, medications, and observations</p>
          </div>

          <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            {timeline?.events && timeline.events.length > 0 ? (
              timeline.events.slice(0, 30).map((evt, idx) => (
                <div key={idx} className="relative group">
                  <div className="absolute -left-6 top-1 w-3.5 h-3.5 rounded-full bg-teal-600 border-2 border-white shadow-sm"></div>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-teal-700 uppercase tracking-wide">
                        {evt.event_type}
                      </span>
                      <span className="text-xs text-slate-400">{evt.event_date}</span>
                    </div>
                    <div className="mt-1 text-xs text-slate-800 font-medium">
                      {evt.clinical_details.condition_name || 
                       evt.clinical_details.medication_name || 
                       evt.clinical_details.observation_name || 
                       evt.clinical_details.encounter_type || 
                       'Clinical Event'}
                      {evt.clinical_details.value_numeric && (
                        <span className="ml-1 text-teal-800 font-bold">
                          : {evt.clinical_details.value_numeric} {evt.clinical_details.unit}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-500 py-4">No events found in timeline.</p>
            )}
          </div>
        </div>
      )}

      {/* Tab 7: Longitudinal Trends & Charts */}
      {activeTab === 'trends' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-slate-100 gap-3">
            <div>
              <h2 className="text-base font-bold text-slate-900">Longitudinal Measurement Trends</h2>
              <p className="text-xs text-slate-500">Verified physiological trajectory across laboratory tests and daily patient logs</p>
            </div>

            {/* Metric Picker */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-600">Metric:</span>
              <select
                value={selectedMetric}
                onChange={e => setSelectedMetric(e.target.value)}
                className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-800"
              >
                <option value="blood_pressure">Systolic Blood Pressure (mmHg)</option>
                <option value="diastolic_bp">Diastolic Blood Pressure (mmHg)</option>
                <option value="glucose">Fasting Blood Glucose (mg/dL)</option>
                <option value="hba1c">HbA1c Glycated Hemoglobin (%)</option>
                <option value="oxygen_saturation">Oxygen Saturation SpO2 (%)</option>
                <option value="pulse">Resting Pulse (bpm)</option>
              </select>
            </div>
          </div>

          {trendsLoading ? (
            <div className="p-8 text-center text-xs text-slate-500">Loading longitudinal points...</div>
          ) : !trendsData || trendsData.points_count === 0 ? (
            <div className="p-12 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200 space-y-2">
              <BarChart3 className="w-8 h-8 text-slate-300 mx-auto" />
              <h4 className="text-sm font-bold text-slate-700">No Measurements Recorded Yet</h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                No verified records found for {selectedMetric.replace('_', ' ')}. Add entries under Daily Tracking or upload a lab report to view trends.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Summary Metric Stats Card */}
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-teal-50/60 border border-teal-200/60">
                  <span className="text-[11px] font-bold text-teal-800 uppercase tracking-wider">Latest Recorded</span>
                  <div className="mt-1 flex items-baseline gap-1.5">
                    <span className="text-2xl font-bold text-teal-950">{trendsData.latest_value}</span>
                    <span className="text-xs font-semibold text-teal-700">{trendsData.unit}</span>
                  </div>
                  <span className="text-[10px] text-teal-600">On {trendsData.latest_date}</span>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Previous Reading</span>
                  <div className="mt-1 flex items-baseline gap-1.5">
                    <span className="text-2xl font-bold text-slate-800">{trendsData.previous_value ?? '—'}</span>
                    <span className="text-xs font-semibold text-slate-500">{trendsData.unit}</span>
                  </div>
                  <span className="text-[10px] text-slate-400">Baseline comparison</span>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Change Magnitude</span>
                  <div className="mt-1 flex items-baseline gap-1.5">
                    <span className="text-2xl font-bold text-slate-800">
                      {trendsData.change_value ? (trendsData.change_value > 0 ? `+${trendsData.change_value}` : trendsData.change_value) : '0'}
                    </span>
                    <span className="text-xs font-semibold text-slate-500">{trendsData.unit}</span>
                  </div>
                  <span className={`text-[10px] font-semibold ${
                    trendsData.change_direction === 'increased' ? 'text-amber-600' :
                    trendsData.change_direction === 'decreased' ? 'text-emerald-600' : 'text-slate-500'
                  }`}>
                    {trendsData.change_direction ? trendsData.change_direction.toUpperCase() : 'STABLE'}
                  </span>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Total Readings</span>
                  <div className="mt-1 flex items-baseline gap-1.5">
                    <span className="text-2xl font-bold text-slate-800">{trendsData.points_count}</span>
                  </div>
                  <span className="text-[10px] text-slate-400">Chronological data points</span>
                </div>
              </div>

              {/* Visual SVG Timeline Bar/Chart */}
              <div className="p-5 rounded-xl border border-slate-200/80 bg-slate-50 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800">{trendsData.metric_name} History</span>
                  <span className="text-[11px] text-slate-400">Chronological trajectory</span>
                </div>

                <div className="h-44 flex items-end gap-3 pt-6 pb-2 px-2 border-b border-slate-200 overflow-x-auto">
                  {trendsData.data.map((p: any, idx: number) => {
                    const maxVal = Math.max(...trendsData.data.map((d: any) => d.value), 1);
                    const minVal = Math.min(...trendsData.data.map((d: any) => d.value), 0);
                    const range = maxVal - minVal || 1;
                    const heightPercent = Math.max(15, Math.min(100, Math.round(((p.value - minVal) / range) * 80) + 15));
                    return (
                      <div key={idx} className="flex-1 min-w-[55px] flex flex-col items-center gap-1.5 group">
                        <span className="text-[10px] font-bold text-slate-700 opacity-90 group-hover:text-teal-700">
                          {p.value}
                        </span>
                        <div 
                          style={{ height: `${heightPercent}%` }} 
                          className={`w-full max-w-[32px] rounded-t-lg transition-all ${
                            p.source_type === 'lab_observation' ? 'bg-teal-600 group-hover:bg-teal-700' : 'bg-emerald-500 group-hover:bg-emerald-600'
                          }`}
                        />
                        <span className="text-[9px] text-slate-400 truncate w-full text-center mt-1">
                          {p.date.slice(5)}
                        </span>
                      </div>
                    );
                  })}
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-teal-600"></span>
                      <span>Clinical Lab Test</span>
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                      <span>Daily Self-Log</span>
                    </span>
                  </div>
                  <span className="italic">{trendsData.disclaimer}</span>
                </div>
              </div>

              {/* Data Table */}
              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                    <tr>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3">Measurement</th>
                      <th className="py-2.5 px-3">Recorded Value</th>
                      <th className="py-2.5 px-3">Reference Range</th>
                      <th className="py-2.5 px-3">Source Type</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {trendsData.data.map((p: any, idx: number) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        <td className="py-2.5 px-3 font-medium text-slate-900">{p.date}</td>
                        <td className="py-2.5 px-3">{p.test_name}</td>
                        <td className="py-2.5 px-3 font-bold text-teal-850">
                          {p.value} {p.unit}
                        </td>
                        <td className="py-2.5 px-3 text-slate-500">{p.reference_range || '—'}</td>
                        <td className="py-2.5 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            p.source_type === 'lab_observation' ? 'bg-teal-50 text-teal-700' : 'bg-emerald-50 text-emerald-700'
                          }`}>
                            {p.source_type === 'lab_observation' ? 'Lab Observation' : 'Daily Home Log'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 8: Appointments & Consultation History */}
      {activeTab === 'appointments' && (
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-slate-100 gap-3">
            <div>
              <h2 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Ticket className="w-4 h-4 text-teal-600" />
                <span>Consultation Bookings & OPD History</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Verified hospital consultations booked through the AI Assistant or scheduling portal with real-time status.
              </p>
            </div>
            <span className="text-xs font-bold text-teal-800 bg-teal-50 px-3 py-1 rounded-full border border-teal-200 self-start sm:self-auto">
              {appointments.length} Total Bookings
            </span>
          </div>

          {appointments.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-xs">
              <Calendar className="w-10 h-10 mx-auto text-slate-300 mb-3" />
              <p className="font-medium">No appointment bookings on record.</p>
              <p className="text-[11px] text-slate-400 mt-1">
                You can book an OPD consultation anytime via your <strong>AI Health Assistant</strong>.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {appointments.map((a) => {
                const token = a.token_number || `TKT-${a.booking_date.replace(/-/g, '')}-${a.booking_id.slice(-4)}`;
                const chamber = a.chamber_room || 'Chamber 104, OPD Block B';
                const hosp = a.hospital_name || 'Seth GS Medical College & KEM Hospital';
                const fee = a.fee || a.consultation_fee || 800;
                const isConfirmed = a.status === 'confirmed';

                return (
                  <div 
                    key={a.booking_id} 
                    className="p-4 rounded-2xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:shadow-sm transition space-y-3"
                  >
                    <div className="flex items-start justify-between gap-2 border-b border-slate-200/70 pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-teal-900 bg-teal-50 px-2.5 py-0.5 rounded-md border border-teal-200 text-xs">
                            {token}
                          </span>
                          <span className="text-[10px] font-mono text-slate-400">Ref: {a.booking_id}</span>
                        </div>
                        <h4 className="font-bold text-slate-900 text-sm mt-1">{a.doctor_name || 'Specialist Doctor'}</h4>
                        <div className="text-[11px] text-slate-500 font-medium">{a.qualification || 'MBBS, MD'} &bull; {a.department}</div>
                      </div>

                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider shrink-0 ${
                        a.status === 'confirmed' ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' :
                        a.status === 'checked_in' ? 'bg-blue-100 text-blue-800 border border-blue-200' :
                        a.status === 'completed' ? 'bg-slate-100 text-slate-700' :
                        'bg-rose-100 text-rose-800'
                      }`}>
                        {a.status.replace('_', ' ')}
                      </span>
                    </div>

                    <div className="space-y-1.5 text-xs text-slate-600">
                      <div className="flex items-center gap-1.5 font-medium text-slate-800">
                        <Building2 className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                        <span className="truncate">{hosp}</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-slate-500 font-mono">OPD Chamber: <strong className="text-slate-700">{chamber}</strong></span>
                        <span className="font-semibold text-slate-900">Fee: ₹{fee}</span>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] bg-white p-2 rounded-lg border border-slate-200">
                        <span className="flex items-center gap-1 font-semibold text-slate-900">
                          <Calendar className="w-3.5 h-3.5 text-teal-600" />
                          {a.booking_date}
                        </span>
                        <span>&bull;</span>
                        <span className="font-bold text-teal-800">
                          {a.time_slot}
                        </span>
                      </div>
                      {a.chief_complaint && (
                        <div className="text-[11px] text-slate-500 italic truncate pt-1">
                          "{a.chief_complaint}"
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-200/70">
                      <button
                        onClick={() => setActiveTicket(a)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-semibold transition shadow-2xs"
                      >
                        <Printer className="w-3.5 h-3.5" />
                        <span>View / Print Slip</span>
                      </button>

                      {isConfirmed && (
                        <button
                          onClick={() => handleCancelAppointment(a.booking_id)}
                          className="px-3 py-1.5 bg-white hover:bg-rose-50 text-rose-600 border border-rose-200 rounded-xl text-xs font-semibold transition"
                        >
                          Cancel Booking
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Modal: Add Condition */}
      {showAddConditionModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">Add Medical Condition</h3>
              <button onClick={() => setShowAddConditionModal(false)}><X className="w-4 h-4 text-slate-400" /></button>
            </div>
            <form onSubmit={handleAddCondition} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Condition Name *</label>
                <input
                  type="text"
                  value={newConditionName}
                  onChange={e => setNewConditionName(e.target.value)}
                  placeholder="e.g. Hypertension, Migraine"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">ICD-10 Code</label>
                  <input
                    type="text"
                    value={newConditionCode}
                    onChange={e => setNewConditionCode(e.target.value)}
                    placeholder="e.g. I10"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Onset Date</label>
                  <input
                    type="date"
                    value={newConditionDate}
                    onChange={e => setNewConditionDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddConditionModal(false)}
                  className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-teal-600 text-white font-semibold rounded-lg"
                >
                  Save Condition
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Medication */}
      {showAddMedModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">Add Medication</h3>
              <button onClick={() => setShowAddMedModal(false)}><X className="w-4 h-4 text-slate-400" /></button>
            </div>
            <form onSubmit={handleAddMedication} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Medication Name *</label>
                <input
                  type="text"
                  value={newMedName}
                  onChange={e => setNewMedName(e.target.value)}
                  placeholder="e.g. Metformin, Amlodipine"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Dosage</label>
                  <input
                    type="text"
                    value={newMedDosage}
                    onChange={e => setNewMedDosage(e.target.value)}
                    placeholder="e.g. 500mg"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Frequency</label>
                  <input
                    type="text"
                    value={newMedFrequency}
                    onChange={e => setNewMedFrequency(e.target.value)}
                    placeholder="e.g. Twice daily"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Prescribing Doctor</label>
                <input
                  type="text"
                  value={newMedDoctor}
                  onChange={e => setNewMedDoctor(e.target.value)}
                  placeholder="e.g. Dr. Arvind Patel"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddMedModal(false)}
                  className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-teal-600 text-white font-semibold rounded-lg"
                >
                  Save Medication
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Allergy */}
      {showAddAllergyModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">Add Allergy / Adverse Reaction</h3>
              <button onClick={() => setShowAddAllergyModal(false)}><X className="w-4 h-4 text-slate-400" /></button>
            </div>
            <form onSubmit={handleAddAllergy} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Allergen / Substance *</label>
                <input
                  type="text"
                  value={newAllergySubstance}
                  onChange={e => setNewAllergySubstance(e.target.value)}
                  placeholder="e.g. Penicillin, Peanuts"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  required
                />
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Observed Reaction *</label>
                <input
                  type="text"
                  value={newAllergyReaction}
                  onChange={e => setNewAllergyReaction(e.target.value)}
                  placeholder="e.g. Skin rash, Hives, Anaphylaxis"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Severity</label>
                  <select
                    value={newAllergySeverity}
                    onChange={e => setNewAllergySeverity(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  >
                    <option value="mild">Mild</option>
                    <option value="moderate">Moderate</option>
                    <option value="severe">Severe / Anaphylactic</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Category</label>
                  <select
                    value={newAllergyCategory}
                    onChange={e => setNewAllergyCategory(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  >
                    <option value="medication">Medication</option>
                    <option value="food">Food</option>
                    <option value="environmental">Environmental</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddAllergyModal(false)}
                  className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-rose-600 text-white font-semibold rounded-lg"
                >
                  Save Allergy
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Upload Report */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">Upload Medical Report</h3>
              <button onClick={() => setShowUploadModal(false)}><X className="w-4 h-4 text-slate-400" /></button>
            </div>
            <form onSubmit={handleUploadDocument} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Document Type</label>
                <select
                  value={docType}
                  onChange={e => setDocType(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                >
                  <option value="lab_report">Laboratory Test Report (Blood, Urine, etc.)</option>
                  <option value="prescription">Prescription Slip</option>
                  <option value="discharge_summary">Discharge Summary</option>
                  <option value="radiology">Imaging / Radiology Report</option>
                </select>
              </div>
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Select File (PDF, PNG, JPG - max 15MB) *</label>
                <input
                  type="file"
                  accept=".pdf,image/png,image/jpeg"
                  onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-teal-50 file:text-teal-700 hover:file:bg-teal-100"
                  required
                />
              </div>

              {uploadSuccessMsg && (
                <div className="p-2.5 rounded bg-emerald-50 text-emerald-800 text-[11px] font-medium">
                  {uploadSuccessMsg}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={uploadLoading || !selectedFile}
                  className="px-4 py-1.5 bg-teal-600 hover:bg-teal-700 text-white font-semibold rounded-lg disabled:opacity-50"
                >
                  {uploadLoading ? 'Uploading & Parsing...' : 'Upload & Parse'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Document & Scan Modal Previewer */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden border border-slate-200">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-teal-600" />
                <div>
                  <h3 className="text-sm font-bold text-slate-900">{previewDoc.file_name}</h3>
                  <p className="text-[11px] text-slate-500 uppercase tracking-wider">
                    {previewDoc.document_type.replace('_', ' ')} · {(previewDoc.file_size_bytes / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={api.getDocumentFileUrl(previewDoc.document_id)}
                  download={previewDoc.file_name}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-xs"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download</span>
                </a>
                <button
                  type="button"
                  onClick={() => setPreviewDoc(null)}
                  className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-500 hover:text-slate-700"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body / Viewer */}
            <div className="flex-1 overflow-auto p-4 bg-slate-100 flex items-center justify-center min-h-[400px]">
              {['png', 'jpg', 'jpeg', 'webp', 'bmp'].includes(previewDoc.file_type.toLowerCase()) ? (
                <div className="max-w-full max-h-[70vh] flex items-center justify-center">
                  <img
                    src={api.getDocumentFileUrl(previewDoc.document_id)}
                    alt={previewDoc.file_name}
                    className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-md border border-slate-300 bg-black/90"
                  />
                </div>
              ) : previewDoc.file_type.toLowerCase() === 'pdf' ? (
                <iframe
                  src={api.getDocumentFileUrl(previewDoc.document_id)}
                  title={previewDoc.file_name}
                  className="w-full h-[70vh] rounded-lg border border-slate-300 bg-white shadow-sm"
                />
              ) : (
                <div className="p-8 text-center text-slate-500 space-y-3">
                  <p className="text-sm">Preview for this file format is not supported directly in the browser.</p>
                  <a
                    href={api.getDocumentFileUrl(previewDoc.document_id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-teal-600 text-white rounded-lg text-xs font-semibold shadow-sm"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span>Open / Download File</span>
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      {/* Appointment Ticket Modal */}
      {activeTicket && (
        <AppointmentTicketModal
          ticket={activeTicket}
          onClose={() => setActiveTicket(null)}
        />
      )}
    </div>
  );
};
