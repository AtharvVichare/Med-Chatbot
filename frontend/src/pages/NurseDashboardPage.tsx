import React, { useState, useEffect } from 'react';
import { 
  HeartPulse, 
  Bed as BedIcon, 
  Activity, 
  AlertCircle, 
  CheckCircle2, 
  RefreshCw, 
  Check, 
  Pill,
  ClipboardList,
  MessageSquare,
  Plus,
  X,
  AlertTriangle
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import type { 
  NurseOverviewData,
  NurseBedBoardItem,
  NursingTaskItem,
  MedicationAdministrationItem,
  ShiftHandoverItem
} from '../types';

export const NurseDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'overview' | 'bed_board' | 'mar' | 'tasks' | 'handover'>('overview');
  
  // Nurse Overview State
  const [overview, setOverview] = useState<NurseOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [selectedWard, setSelectedWard] = useState('All');

  // Bed Board State
  const [beds, setBeds] = useState<NurseBedBoardItem[]>([]);

  // Medication Administration Records (MAR) State
  const [marRecords, setMarRecords] = useState<MedicationAdministrationItem[]>([]);
  const [selectedMar, setSelectedMar] = useState<MedicationAdministrationItem | null>(null);
  const [marAction, setMarAction] = useState<'administered' | 'delayed' | 'refused' | 'missed'>('administered');
  const [marReason, setMarReason] = useState('');
  const [marNotes, setMarNotes] = useState('');
  const [showMarModal, setShowMarModal] = useState(false);

  // Nursing Tasks State
  const [tasks, setTasks] = useState<NursingTaskItem[]>([]);
  const [showTaskModal, setShowTaskModal] = useState(false);
  const [newTaskPatientId, setNewTaskPatientId] = useState('PAT-AARAV-001');
  const [newTaskWard, setNewTaskWard] = useState('Deluxe Private Ward');
  const [newTaskType, setNewTaskType] = useState('vitals');
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskPriority, setNewTaskPriority] = useState('routine');

  // Bedside Vitals Recording Modal with Threshold Alerts
  const [showVitalsModal, setShowVitalsModal] = useState(false);
  const [vitalsPatientId, setVitalsPatientId] = useState('PAT-AARAV-001');
  const [vitalsSystolic, setVitalsSystolic] = useState('122');
  const [vitalsDiastolic, setVitalsDiastolic] = useState('80');
  const [vitalsPulse, setVitalsPulse] = useState('74');
  const [vitalsSpo2, setVitalsSpo2] = useState('98');
  const [vitalsTemp, setVitalsTemp] = useState('36.8');
  const [vitalsNotes, setVitalsNotes] = useState('');
  const [vitalAlerts, setVitalAlerts] = useState<any[]>([]);

  // SBAR Shift Handover State
  const [handovers, setHandovers] = useState<ShiftHandoverItem[]>([]);
  const [showHandoverModal, setShowHandoverModal] = useState(false);
  const [sbarSituation, setSbarSituation] = useState('');
  const [sbarBackground, setSbarBackground] = useState('');
  const [sbarAssessment, setSbarAssessment] = useState('');
  const [sbarRecommendation, setSbarRecommendation] = useState('');
  const [sbarWard, setSbarWard] = useState('Deluxe Private Ward');

  // Bed Transfer & Discharge State
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [selectedBedForTransfer, setSelectedBedForTransfer] = useState<NurseBedBoardItem | null>(null);
  const [targetBedId, setTargetBedId] = useState('');

  const loadNurseData = async () => {
    setLoading(true);
    try {
      const [ov, bds, mrs, tsks, hnds] = await Promise.all([
        api.getNurseOverview(selectedWard === 'All' ? undefined : selectedWard),
        api.getNurseBedBoard(selectedWard === 'All' ? undefined : selectedWard),
        api.listMAR(),
        api.listNursingTasks(selectedWard === 'All' ? undefined : selectedWard),
        api.listShiftHandovers(selectedWard === 'All' ? undefined : selectedWard)
      ]);
      setOverview(ov);
      setBeds(bds);
      setMarRecords(mrs);
      setTasks(tsks);
      setHandovers(hnds);
    } catch (err) {
      console.error('Error loading nurse data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNurseData();
  }, [selectedWard]);

  const handleRecordVitals = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.recordNurseBedsideVitals({
        patient_id: vitalsPatientId,
        systolic_bp: parseFloat(vitalsSystolic),
        diastolic_bp: parseFloat(vitalsDiastolic),
        pulse: parseFloat(vitalsPulse),
        spo2: parseFloat(vitalsSpo2),
        temperature_c: parseFloat(vitalsTemp),
        notes: vitalsNotes
      });

      if (res.alert_triggered) {
        setVitalAlerts(res.threshold_alerts);
        setSuccessMessage('Vitals saved to EHR. CRITICAL THRESHOLD ALERT TRIGGERED!');
      } else {
        setSuccessMessage('Bedside vitals successfully recorded to patient EHR.');
        setShowVitalsModal(false);
      }
      loadNurseData();
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: any) {
      alert(`Failed to record vitals: ${err.message}`);
    }
  };

  const handleAdministerMAR = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMar) return;
    try {
      await api.administerMAR(selectedMar.mar_id, marAction, marReason, marNotes);
      setSuccessMessage(`Medication ${selectedMar.medication_name} marked as ${marAction.toUpperCase()}.`);
      setShowMarModal(false);
      setSelectedMar(null);
      setMarReason('');
      setMarNotes('');
      loadNurseData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`MAR recording failed: ${err.message}`);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createNursingTask({
        patient_id: newTaskPatientId,
        ward: newTaskWard,
        task_type: newTaskType,
        title: newTaskTitle,
        priority: newTaskPriority,
        scheduled_time: new Date(Date.now() + 60 * 60 * 1000).toISOString()
      });
      setSuccessMessage(`Nursing task "${newTaskTitle}" created.`);
      setShowTaskModal(false);
      setNewTaskTitle('');
      loadNurseData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`Task creation failed: ${err.message}`);
    }
  };

  const handleTaskStatusUpdate = async (taskId: string, newStatus: string) => {
    try {
      await api.updateNursingTask(taskId, {
        status: newStatus,
        completion_notes: 'Completed & confirmed during nursing rounds'
      });
      setSuccessMessage(`Task status updated to ${newStatus}.`);
      loadNurseData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`Task update failed: ${err.message}`);
    }
  };

  const handleSubmitHandover = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.submitShiftHandover({
        ward: sbarWard,
        shift_type: overview?.shift.shift_type || 'morning',
        outgoing_nurse_name: user?.full_name || 'Nurse Anjali Sharma',
        situation: sbarSituation,
        background: sbarBackground,
        assessment: sbarAssessment,
        recommendation: sbarRecommendation,
        critical_alerts: ['Clinical monitoring verified for all active ward inpatients.'],
        total_patients: overview?.stats.active_inpatients_count || 12
      });
      setSuccessMessage('SBAR shift handover note submitted successfully.');
      setShowHandoverModal(false);
      setSbarSituation('');
      setSbarBackground('');
      setSbarAssessment('');
      setSbarRecommendation('');
      loadNurseData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`Handover submission failed: ${err.message}`);
    }
  };

  const handleBedTransfer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBedForTransfer || !targetBedId) return;
    try {
      // Find active admission request for bed
      await api.transferBed(selectedBedForTransfer.bed_id, targetBedId);
      setSuccessMessage(`Patient successfully transferred to Bed ${targetBedId}.`);
      setShowTransferModal(false);
      loadNurseData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`Bed transfer failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
              {overview?.shift.label || 'Active Nursing Shift'}
            </span>
            <span className="text-xs text-slate-500">
              {overview?.hospital || 'Seth GS Medical College & KEM Hospital'}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <HeartPulse className="w-6 h-6 text-emerald-600" />
            <span>{user?.role === 'nurse' ? (user?.full_name || 'Nurse Anjali Sharma') : 'Nurse Anjali Sharma'} · Ward Nursing Station</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Ward Assignment: <span className="font-semibold text-slate-700">{selectedWard}</span> · 100-Bed Facility · Clinical Care & Handover Continuity
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => { setShowVitalsModal(true); setVitalAlerts([]); }}
            className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Record Bedside Vitals</span>
          </button>
          <button
            onClick={() => setShowHandoverModal(true)}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5"
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>SBAR Handover</span>
          </button>
          <button
            onClick={loadNurseData}
            className="p-2 border border-slate-200 rounded-xl hover:bg-slate-50 text-slate-600 transition"
            title="Refresh shift data"
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
              ? 'bg-emerald-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Shift Overview</span>
        </button>

        <button
          onClick={() => setActiveTab('bed_board')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            activeTab === 'bed_board'
              ? 'bg-emerald-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <BedIcon className="w-3.5 h-3.5" />
          <span>100-Bed Ward Board</span>
        </button>

        <button
          onClick={() => setActiveTab('mar')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            activeTab === 'mar'
              ? 'bg-emerald-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Pill className="w-3.5 h-3.5" />
          <span>Medication Administrations (MAR)</span>
        </button>

        <button
          onClick={() => setActiveTab('tasks')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            activeTab === 'tasks'
              ? 'bg-emerald-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <ClipboardList className="w-3.5 h-3.5" />
          <span>Nursing Tasks</span>
        </button>

        <button
          onClick={() => setActiveTab('handover')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            activeTab === 'handover'
              ? 'bg-emerald-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          <span>SBAR Shift Handover Notes</span>
        </button>
      </div>

      {loading && !overview && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-emerald-600 shrink-0" />
          <span>Loading nursing station records...</span>
        </div>
      )}

      {successMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* TAB 1: SHIFT OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
              <span className="text-xs text-slate-500 font-medium">Occupied Beds</span>
              <div className="text-2xl font-black text-slate-900 mt-2">
                {overview?.stats.occupied_beds || 0} / {overview?.stats.total_facility_beds || 100}
              </div>
              <span className="text-[10px] text-emerald-700 font-medium">
                {overview ? Math.round((overview.stats.occupied_beds / overview.stats.total_facility_beds) * 100) : 0}% Facility Occupancy
              </span>
            </div>

            <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
              <span className="text-xs text-slate-500 font-medium">Available Beds</span>
              <div className="text-2xl font-black text-slate-900 mt-2">
                {overview?.stats.available_beds || 0}
              </div>
              <span className="text-[10px] text-slate-500">Ready for admission</span>
            </div>

            <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
              <span className="text-xs text-slate-500 font-medium">Scheduled MAR Doses</span>
              <div className="text-2xl font-black text-slate-900 mt-2">
                {overview?.stats.pending_mar_count || 0}
              </div>
              <span className="text-[10px] text-blue-700 font-medium">Medication rounds</span>
            </div>

            <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-xs">
              <span className="text-xs text-slate-500 font-medium">Pending Tasks</span>
              <div className="text-2xl font-black text-slate-900 mt-2">
                {overview?.stats.pending_tasks_count || 0}
              </div>
              <span className="text-[10px] text-amber-700 font-medium">Vitals, samples, prep</span>
            </div>

            <div className="p-4 bg-white rounded-2xl border border-rose-200 bg-rose-50/40 shadow-xs">
              <span className="text-xs text-rose-700 font-medium">Immediate Attention</span>
              <div className="text-2xl font-black text-rose-900 mt-2">
                {overview?.stats.immediate_attention_count || 0}
              </div>
              <span className="text-[10px] text-rose-700 font-medium">Vital threshold alerts</span>
            </div>
          </div>

          {/* Immediate Attention Panel */}
          {overview?.immediate_attention && overview.immediate_attention.length > 0 && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-2xl space-y-2">
              <div className="flex items-center gap-2 text-rose-800 font-bold text-xs uppercase tracking-wider">
                <AlertCircle className="w-4 h-4 text-rose-600" />
                <span>Patients Requiring Immediate Attention (Threshold Breaches)</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {overview.immediate_attention.map((item, idx) => (
                  <div key={idx} className="p-3 bg-white rounded-xl border border-rose-200 text-xs flex items-center justify-between">
                    <div>
                      <span className="font-bold text-slate-900">{item.patient_name}</span> ({item.patient_id})
                      <p className="text-[11px] text-rose-700 font-medium mt-0.5">{item.message}</p>
                    </div>
                    <button
                      onClick={() => {
                        setVitalsPatientId(item.patient_id);
                        setShowVitalsModal(true);
                      }}
                      className="px-2.5 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-[10px] font-bold"
                    >
                      Re-Check Vitals
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Scheduled Medication Administrations & Pending Tasks Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Scheduled MAR Doses */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Pill className="w-5 h-5 text-blue-600" />
                  <span>Scheduled Medication Doses (MAR)</span>
                </h2>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                  {overview?.pending_mar_doses.length || 0} Due
                </span>
              </div>

              <div className="divide-y divide-slate-100 text-xs">
                {overview?.pending_mar_doses && overview.pending_mar_doses.length > 0 ? (
                  overview.pending_mar_doses.map((m) => (
                    <div key={m.mar_id} className="py-2.5 flex items-center justify-between hover:bg-slate-50/50 rounded-lg px-1 transition">
                      <div>
                        <div className="font-bold text-slate-900">{m.medication_name}</div>
                        <div className="text-[11px] text-slate-500">
                          {m.dosage} · Route: {m.route} · Patient: <strong>{m.patient_name}</strong>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-700">{m.scheduled_time}</span>
                        <button
                          onClick={() => {
                            setSelectedMar(m as any);
                            setShowMarModal(true);
                          }}
                          className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-[10px] font-bold"
                        >
                          Administer
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="py-6 text-center text-slate-400">All scheduled medications administered.</div>
                )}
              </div>
            </div>

            {/* Overdue & Pending Nursing Tasks */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <ClipboardList className="w-5 h-5 text-amber-500" />
                  <span>Nursing Tasks & Interventions</span>
                </h2>
                <button
                  onClick={() => setShowTaskModal(true)}
                  className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" />
                  <span>Add Task</span>
                </button>
              </div>

              <div className="divide-y divide-slate-100 text-xs">
                {overview?.nursing_tasks && overview.nursing_tasks.length > 0 ? (
                  overview.nursing_tasks.map((t) => (
                    <div key={t.task_id} className="py-2.5 flex items-center justify-between hover:bg-slate-50/50 rounded-lg px-1 transition">
                      <div>
                        <div className="font-bold text-slate-900 flex items-center gap-1.5">
                          <span>{t.title}</span>
                          {t.status === 'overdue' && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-black bg-rose-100 text-rose-700 uppercase">
                              Overdue
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {t.ward} ({t.bed_number || 'Bed'}) · Patient: <strong>{t.patient_name}</strong>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleTaskStatusUpdate(t.task_id, 'completed')}
                          className="p-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg"
                          title="Mark Complete"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="py-6 text-center text-slate-400">No active nursing tasks.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: 100-BED WARD BOARD */}
      {activeTab === 'bed_board' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <BedIcon className="w-5 h-5 text-emerald-600" />
                <span>100-Bed Real-Time Ward Board</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Live bed registry, occupancy status, attending physicians, admission tracking, and transfer workflows.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={selectedWard}
                onChange={(e) => setSelectedWard(e.target.value)}
                className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold focus:outline-none"
              >
                <option value="All">All Wards (100 Beds)</option>
                <option value="ICU">ICU (Intensive Care)</option>
                <option value="CCU">CCU (Coronary Care)</option>
                <option value="Emergency">Emergency Triage</option>
                <option value="Deluxe">Deluxe Private Wards</option>
                <option value="General">General Medical Wards</option>
                <option value="Surgical">Post-Op Surgical</option>
                <option value="Pediatric">Pediatrics</option>
                <option value="Maternity">Maternity</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-3 pt-2">
            {beds.map((b) => (
              <div
                key={b.bed_id}
                className={`p-3 rounded-xl border text-xs transition relative ${
                  b.is_occupied
                    ? 'bg-rose-50/50 border-rose-200 text-rose-950'
                    : b.status === 'cleaning'
                    ? 'bg-amber-50/50 border-amber-200 text-amber-950'
                    : 'bg-emerald-50/40 border-emerald-200 text-emerald-950 hover:bg-emerald-100/60'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm">{b.bed_number}</span>
                  <span className={`w-2 h-2 rounded-full ${b.is_occupied ? 'bg-rose-500' : 'bg-emerald-500'}`} />
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5 font-medium">{b.ward}</div>

                {b.is_occupied ? (
                  <div className="mt-2 pt-2 border-t border-rose-200/80 space-y-1">
                    <div className="font-bold truncate text-slate-900">{b.patient_name || 'Occupied'}</div>
                    <div className="text-[10px] text-slate-600">Attending: {b.attending_doctor || 'Dr. Deshmukh'}</div>
                    <button
                      onClick={() => {
                        setSelectedBedForTransfer(b);
                        setShowTransferModal(true);
                      }}
                      className="mt-1 w-full py-1 bg-white border border-rose-200 rounded text-[10px] font-bold text-rose-800 hover:bg-rose-50"
                    >
                      Transfer Bed
                    </button>
                  </div>
                ) : (
                  <div className="mt-2 pt-2 border-t border-emerald-200/80">
                    <span className="text-[10px] font-bold text-emerald-700">Available</span>
                    <span className="block text-[9px] text-slate-400 mt-0.5">₹{b.daily_charge}/day</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: MEDICATION ADMINISTRATION RECORD (MAR) */}
      {activeTab === 'mar' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Pill className="w-5 h-5 text-blue-600" />
                <span>Medication Administration Record (MAR)</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Verify prescribed drug, dose, scheduled time, and administer with nurse attribution and mandatory justification if omitted.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[11px] uppercase bg-slate-50 text-slate-500 font-semibold border-y border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Patient</th>
                  <th className="py-2.5 px-3">Medication Name & Dosage</th>
                  <th className="py-2.5 px-3">Route</th>
                  <th className="py-2.5 px-3">Scheduled Time</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Administered By</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {marRecords.map((m) => (
                  <tr key={m.mar_id} className="hover:bg-slate-50/60 transition">
                    <td className="py-3 px-3">
                      <span className="font-bold text-slate-900">{m.patient_name}</span>
                      <span className="block text-[10px] text-slate-400">{m.patient_id}</span>
                    </td>
                    <td className="py-3 px-3 font-semibold text-slate-800">{m.medication_name} ({m.dosage})</td>
                    <td className="py-3 px-3 capitalize text-slate-600">{m.route}</td>
                    <td className="py-3 px-3 font-bold text-slate-800">{new Date(m.scheduled_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        m.status === 'administered' ? 'bg-emerald-100 text-emerald-800' :
                        m.status === 'delayed' ? 'bg-amber-100 text-amber-800' :
                        m.status === 'refused' || m.status === 'missed' ? 'bg-rose-100 text-rose-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {m.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-500">{m.administered_by || '—'}</td>
                    <td className="py-3 px-3 text-right">
                      {m.status === 'scheduled' && (
                        <button
                          onClick={() => {
                            setSelectedMar(m);
                            setShowMarModal(true);
                          }}
                          className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-[10px] font-bold"
                        >
                          Record Action
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: NURSING TASKS */}
      {activeTab === 'tasks' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <ClipboardList className="w-5 h-5 text-amber-500" />
                <span>Nursing Task Management</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Vitals monitoring, lab collection, wound dressing, and clinical physician instructions.
              </p>
            </div>
            <button
              onClick={() => setShowTaskModal(true)}
              className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create Task</span>
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[11px] uppercase bg-slate-50 text-slate-500 font-semibold border-y border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Task Title</th>
                  <th className="py-2.5 px-3">Patient</th>
                  <th className="py-2.5 px-3">Ward / Bed</th>
                  <th className="py-2.5 px-3">Priority</th>
                  <th className="py-2.5 px-3">Scheduled Time</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tasks.map((t) => (
                  <tr key={t.task_id} className="hover:bg-slate-50/60 transition">
                    <td className="py-3 px-3 font-bold text-slate-900">{t.title}</td>
                    <td className="py-3 px-3 text-slate-700">{t.patient_name || t.patient_id}</td>
                    <td className="py-3 px-3 text-slate-600">{t.ward} ({t.bed_number || 'Bed'})</td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        t.priority === 'urgent' ? 'bg-amber-100 text-amber-800' :
                        t.priority === 'stat' ? 'bg-rose-100 text-rose-800' : 'bg-slate-100 text-slate-700'
                      }`}>
                        {t.priority.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-slate-600">{new Date(t.scheduled_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        t.status === 'completed' ? 'bg-emerald-100 text-emerald-800' :
                        t.status === 'overdue' ? 'bg-rose-100 text-rose-800' : 'bg-blue-100 text-blue-800'
                      }`}>
                        {t.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right">
                      {t.status !== 'completed' && (
                        <button
                          onClick={() => handleTaskStatusUpdate(t.task_id, 'completed')}
                          className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-[10px] font-bold"
                        >
                          Mark Complete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 5: SBAR SHIFT HANDOVER */}
      {activeTab === 'handover' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-indigo-600" />
                <span>Clinical Shift Handover (SBAR Format)</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Structured clinical communication: Situation, Background, Assessment, and Recommendation.
              </p>
            </div>
            <button
              onClick={() => setShowHandoverModal(true)}
              className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Submit SBAR Handover</span>
            </button>
          </div>

          <div className="space-y-4">
            {handovers.map((h) => (
              <div key={h.handover_id} className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-3">
                <div className="flex items-center justify-between border-b border-slate-200/80 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm text-slate-900">{h.ward}</span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-indigo-100 text-indigo-700">
                      {h.shift_type} Shift
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400">
                    Handover Date: {h.handover_date} · Outgoing: <strong>{h.outgoing_nurse_name}</strong>
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3 bg-white rounded-lg border border-slate-200/80">
                    <span className="font-bold text-indigo-700 block mb-1">Situation (S)</span>
                    <p className="text-slate-700">{h.situation}</p>
                  </div>
                  <div className="p-3 bg-white rounded-lg border border-slate-200/80">
                    <span className="font-bold text-indigo-700 block mb-1">Background (B)</span>
                    <p className="text-slate-700">{h.background}</p>
                  </div>
                  <div className="p-3 bg-white rounded-lg border border-slate-200/80">
                    <span className="font-bold text-indigo-700 block mb-1">Assessment (A)</span>
                    <p className="text-slate-700">{h.assessment}</p>
                  </div>
                  <div className="p-3 bg-white rounded-lg border border-slate-200/80">
                    <span className="font-bold text-indigo-700 block mb-1">Recommendation (R)</span>
                    <p className="text-slate-700">{h.recommendation}</p>
                  </div>
                </div>

                {h.critical_alerts && h.critical_alerts.length > 0 && (
                  <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-[11px]">
                    <strong>Critical Handoff Alerts:</strong> {h.critical_alerts.join('; ')}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* BEDSIDE VITALS MODAL WITH THRESHOLD ALERTING */}
      {showVitalsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl w-full max-w-md border border-slate-200 shadow-xl p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-600" />
                <span>Record Bedside Vitals</span>
              </h3>
              <button onClick={() => setShowVitalsModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleRecordVitals} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Patient</label>
                <select
                  value={vitalsPatientId}
                  onChange={(e) => setVitalsPatientId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-medium"
                >
                  <option value="PAT-AARAV-001">Aarav Mehta (PAT-AARAV-001) - Bed DELUXE-01</option>
                  <option value="PAT-PRIYA-002">Priya Mehta (PAT-PRIYA-002)</option>
                  <option value="PAT-SUNITA-004">Sunita Mehta (PAT-SUNITA-004)</option>
                  <option value="PAT-ROHAN-003">Rohan Mehta (PAT-ROHAN-003)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Systolic BP (mmHg)</label>
                  <input
                    type="number"
                    value={vitalsSystolic}
                    onChange={(e) => setVitalsSystolic(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Diastolic BP (mmHg)</label>
                  <input
                    type="number"
                    value={vitalsDiastolic}
                    onChange={(e) => setVitalsDiastolic(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Heart Rate</label>
                  <input
                    type="number"
                    value={vitalsPulse}
                    onChange={(e) => setVitalsPulse(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">SpO2 (%)</label>
                  <input
                    type="number"
                    value={vitalsSpo2}
                    onChange={(e) => setVitalsSpo2(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Temp (°C)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={vitalsTemp}
                    onChange={(e) => setVitalsTemp(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Clinical Observation Notes</label>
                <textarea
                  rows={2}
                  value={vitalsNotes}
                  onChange={(e) => setVitalsNotes(e.target.value)}
                  placeholder="Patient conscious, oriented, no acute distress..."
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              {vitalAlerts.length > 0 && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl space-y-1 text-[11px] text-rose-800">
                  <div className="font-bold flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                    <span>Clinical Threshold Breached:</span>
                  </div>
                  {vitalAlerts.map((a, i) => (
                    <div key={i}>• {a.parameter}: {a.alert}</div>
                  ))}
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowVitalsModal(false)}
                  className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold"
                >
                  Close
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold"
                >
                  Record to EHR
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MAR RECORD ACTION MODAL */}
      {showMarModal && selectedMar && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl w-full max-w-md border border-slate-200 shadow-xl p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Pill className="w-4 h-4 text-blue-600" />
                <span>Medication Administration Confirmation</span>
              </h3>
              <button onClick={() => setShowMarModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAdministerMAR} className="space-y-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                <div className="font-bold text-slate-900">{selectedMar.medication_name}</div>
                <div className="text-slate-600">{selectedMar.dosage} · Route: {selectedMar.route}</div>
                <div className="text-slate-500">Patient: <strong>{selectedMar.patient_name}</strong> ({selectedMar.patient_id})</div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Administration Status *</label>
                <select
                  value={marAction}
                  onChange={(e: any) => setMarAction(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-medium"
                >
                  <option value="administered">Administered as Prescribed</option>
                  <option value="delayed">Delayed (e.g. Patient off unit / sleeping)</option>
                  <option value="refused">Refused by Patient</option>
                  <option value="missed">Missed / Withheld</option>
                </select>
              </div>

              {marAction !== 'administered' && (
                <div>
                  <label className="block font-semibold text-rose-700 mb-1">Clinical Justification Reason *</label>
                  <input
                    type="text"
                    required
                    placeholder="Reason why dose was not given on schedule..."
                    value={marReason}
                    onChange={(e) => setMarReason(e.target.value)}
                    className="w-full px-3 py-2 bg-rose-50 border border-rose-200 rounded-xl text-xs"
                  />
                </div>
              )}

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Nurse Notes</label>
                <textarea
                  rows={2}
                  value={marNotes}
                  onChange={(e) => setMarNotes(e.target.value)}
                  placeholder="Patient identity verified by 2 identifiers..."
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowMarModal(false)}
                  className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold"
                >
                  Confirm Administration
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SBAR HANDOVER SUBMISSION MODAL */}
      {showHandoverModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl w-full max-w-lg border border-slate-200 shadow-xl p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-indigo-600" />
                <span>Submit Structured SBAR Handover Note</span>
              </h3>
              <button onClick={() => setShowHandoverModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmitHandover} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Ward *</label>
                <input
                  type="text"
                  value={sbarWard}
                  onChange={(e) => setSbarWard(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Situation (S) *</label>
                <textarea
                  rows={2}
                  required
                  placeholder="Current ward census, occupied beds, high-dependency patients..."
                  value={sbarSituation}
                  onChange={(e) => setSbarSituation(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Background (B) *</label>
                <textarea
                  rows={2}
                  required
                  placeholder="Key diagnoses, new admissions during shift, pending procedures..."
                  value={sbarBackground}
                  onChange={(e) => setSbarBackground(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Assessment (A) *</label>
                <textarea
                  rows={2}
                  required
                  placeholder="Overall clinical trajectory, stability of vitals, threshold alerts..."
                  value={sbarAssessment}
                  onChange={(e) => setSbarAssessment(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Recommendation (R) *</label>
                <textarea
                  rows={2}
                  required
                  placeholder="Pending medication doses, follow-up labs, upcoming rounds..."
                  value={sbarRecommendation}
                  onChange={(e) => setSbarRecommendation(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowHandoverModal(false)}
                  className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold"
                >
                  Sign & Submit Handover
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CREATE NURSING TASK MODAL */}
      {showTaskModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl w-full max-w-md border border-slate-200 shadow-xl p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <ClipboardList className="w-4 h-4 text-emerald-600" />
                <span>Add Nursing Task</span>
              </h3>
              <button onClick={() => setShowTaskModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Patient</label>
                <select
                  value={newTaskPatientId}
                  onChange={(e) => setNewTaskPatientId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                >
                  <option value="PAT-AARAV-001">Aarav Mehta (PAT-AARAV-001)</option>
                  <option value="PAT-PRIYA-002">Priya Mehta (PAT-PRIYA-002)</option>
                  <option value="PAT-SUNITA-004">Sunita Mehta (PAT-SUNITA-004)</option>
                  <option value="PAT-ROHAN-003">Rohan Mehta (PAT-ROHAN-003)</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Task Type</label>
                <select
                  value={newTaskType}
                  onChange={(e) => setNewTaskType(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                >
                  <option value="vitals">Vitals Recording Round</option>
                  <option value="medication">Medication Administration</option>
                  <option value="lab_collection">Laboratory Sample Collection</option>
                  <option value="wound_care">Wound Dressing / Care</option>
                  <option value="procedure_prep">Procedure Preparation</option>
                  <option value="doctor_order">Doctor Order Execution</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Ward</label>
                  <select
                    value={newTaskWard}
                    onChange={(e) => setNewTaskWard(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  >
                    <option value="Deluxe Private Ward">Deluxe Private Ward</option>
                    <option value="Semi-Private Ward A">Semi-Private Ward A</option>
                    <option value="General Medical Ward">General Medical Ward</option>
                    <option value="Intensive Care Unit">Intensive Care Unit</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Priority</label>
                  <select
                    value={newTaskPriority}
                    onChange={(e) => setNewTaskPriority(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  >
                    <option value="routine">Routine</option>
                    <option value="urgent">Urgent</option>
                    <option value="stat">STAT</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Task Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Draw fasting blood glucose & CBC sample"
                  value={newTaskTitle}
                  onChange={(e) => setNewTaskTitle(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowTaskModal(false)}
                  className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold"
                >
                  Create Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* BED TRANSFER MODAL */}
      {showTransferModal && selectedBedForTransfer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl w-full max-w-md border border-slate-200 shadow-xl p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <BedIcon className="w-4 h-4 text-rose-600" />
                <span>Transfer Bed · {selectedBedForTransfer.bed_id}</span>
              </h3>
              <button onClick={() => setShowTransferModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleBedTransfer} className="space-y-3 text-xs">
              <div>
                <span className="text-slate-500">Current Occupant:</span>
                <p className="font-bold text-slate-800 text-sm">{selectedBedForTransfer.patient_name || 'Assigned Patient'} ({selectedBedForTransfer.patient_id})</p>
                <p className="text-slate-500 text-[11px]">{selectedBedForTransfer.ward} · Bed {selectedBedForTransfer.bed_id}</p>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Target Bed (Available)</label>
                <select
                  value={targetBedId}
                  onChange={(e) => setTargetBedId(e.target.value)}
                  required
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                >
                  <option value="">Select Target Bed...</option>
                  {beds
                    .filter(b => !b.is_occupied)
                    .map(b => (
                      <option key={b.bed_id} value={b.bed_id}>
                        {b.bed_id} ({b.ward} - {b.bed_type})
                      </option>
                    ))}
                </select>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowTransferModal(false)}
                  className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!targetBedId}
                  className="flex-1 py-2 bg-rose-600 hover:bg-rose-700 disabled:bg-slate-300 text-white rounded-xl font-bold"
                >
                  Confirm Transfer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
