import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Search, 
  Calendar, 
  ArrowLeft, 
  Activity, 
  Pill, 
  AlertCircle,
  Clock,
  ChevronRight
} from 'lucide-react';
import { api } from '../services/api';
import type { Patient, Encounter, Condition, Observation, Medication } from '../types';
import { useAuth } from '../context/AuthContext';

export const PatientManagementPage: React.FC = () => {
  const { user } = useAuth();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(15);
  const [searchDistrict, setSearchDistrict] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Selected Patient state for details view
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [conditions, setConditions] = useState<Condition[]>([]);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [medications, setMedications] = useState<Medication[]>([]);

  useEffect(() => {
    // If logged in as patient, default directly to their assigned patient_id
    if (user?.role === 'patient' && user.patient_id) {
      loadPatientDetails(user.patient_id);
    } else if (user?.role === 'public_health_analyst') {
      setError('Public Health Analysts are restricted from viewing individual identified patient records.');
      setIsLoading(false);
    } else {
      loadPatientList(page, searchDistrict);
    }
  }, [page, user]);

  const loadPatientList = async (p: number, district?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getPatients(p, pageSize, district || undefined);
      setPatients(data.items);
      setTotalCount(data.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load patient directory.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadPatientList(1, searchDistrict);
  };

  const loadPatientDetails = async (patientId: string) => {
    setSelectedPatientId(patientId);
    try {
      const [pat, enc, cond, obs, med] = await Promise.all([
        api.getPatient(patientId),
        api.getPatientEncounters(patientId),
        api.getPatientConditions(patientId),
        api.getPatientObservations(patientId),
        api.getPatientMedications(patientId)
      ]);
      setSelectedPatient(pat);
      setEncounters(enc);
      setConditions(cond);
      setObservations(obs);
      setMedications(med);
    } catch (err: any) {
      setError(err.message || 'Failed to load patient clinical records.');
    }
  };

  const backToList = () => {
    setSelectedPatientId(null);
    setSelectedPatient(null);
  };

  // --- Patient Detail View ---
  if (selectedPatientId && selectedPatient) {
    return (
      <div className="space-y-6">
        {user?.role !== 'patient' && (
          <button
            onClick={backToList}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-700 hover:text-teal-900"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Patient Directory</span>
          </button>
        )}

        {/* Patient Demographic Card */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold text-lg">
                {selectedPatient.first_name[0]}{selectedPatient.last_name[0]}
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900">
                  {selectedPatient.first_name} {selectedPatient.last_name}
                </h2>
                <div className="flex flex-wrap gap-2 text-xs text-slate-500 mt-0.5">
                  <span>ID: {selectedPatient.patient_id}</span>
                  <span>•</span>
                  <span>DOB: {selectedPatient.date_of_birth}</span>
                  <span>•</span>
                  <span>Gender: {selectedPatient.gender}</span>
                  <span>•</span>
                  <span>Blood: {selectedPatient.blood_group || 'Unknown'}</span>
                </div>
              </div>
            </div>

            <div className="text-xs text-slate-500">
              <span className="font-semibold block text-slate-700">Location:</span>
              <span>{selectedPatient.city || selectedPatient.state || 'Registered District'}</span>
            </div>
          </div>
        </div>

        {/* Longitudinal Clinical Record Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Conditions Panel */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-teal-600" />
              <span>Active & Historical Conditions ({conditions.length})</span>
            </h3>
            {conditions.length === 0 ? (
              <p className="text-xs text-slate-400 py-3 italic">No recorded conditions</p>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {conditions.map((c) => (
                  <div key={c.condition_id} className="p-3 bg-slate-50 rounded-xl text-xs flex justify-between items-center">
                    <div>
                      <span className="font-semibold text-slate-900 block">{c.description}</span>
                      <span className="text-[11px] text-slate-500">ICD: {c.code} • Onset: {c.onset_date}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-800">
                      {c.clinical_status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Medications Panel */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Pill className="w-4 h-4 text-indigo-600" />
              <span>Medication Regimen ({medications.length})</span>
            </h3>
            {medications.length === 0 ? (
              <p className="text-xs text-slate-400 py-3 italic">No recorded medications</p>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {medications.map((m) => (
                  <div key={m.medication_id} className="p-3 bg-slate-50 rounded-xl text-xs flex justify-between items-center">
                    <div>
                      <span className="font-semibold text-slate-900 block">{m.medication_name}</span>
                      <span className="text-[11px] text-slate-500">{m.dosage} • {m.frequency}</span>
                    </div>
                    <span className="text-[11px] text-slate-500">{m.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Observations & Biomarkers */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Clock className="w-4 h-4 text-emerald-600" />
              <span>Clinical Observations & Vitals ({observations.length})</span>
            </h3>
            {observations.length === 0 ? (
              <p className="text-xs text-slate-400 py-3 italic">No recorded observations</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {observations.map((o) => (
                  <div key={o.observation_id} className="p-3 bg-slate-50 rounded-xl text-xs flex justify-between items-center">
                    <div>
                      <span className="font-semibold text-slate-900 block">{o.description}</span>
                      <span className="text-[11px] text-slate-500">{o.effective_date}</span>
                    </div>
                    <div className="text-right">
                      <span className="font-bold text-slate-900">
                        {o.value_numeric !== undefined ? `${o.value_numeric} ${o.unit || ''}` : o.value_string}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Encounters Panel */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs space-y-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Calendar className="w-4 h-4 text-purple-600" />
              <span>Clinical Encounters ({encounters.length})</span>
            </h3>
            {encounters.length === 0 ? (
              <p className="text-xs text-slate-400 py-3 italic">No recorded encounters</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {encounters.map((e) => (
                  <div key={e.encounter_id} className="p-3 bg-slate-50 rounded-xl text-xs flex justify-between items-center">
                    <div>
                      <span className="font-semibold text-slate-900 block">{e.encounter_type}</span>
                      <span className="text-[11px] text-slate-500">{e.start_date} • {e.facility_name || 'Primary Clinic'}</span>
                    </div>
                    <span className="text-[11px] text-slate-500 italic">{e.reason_description}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // --- Patient Directory List View ---
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Users className="w-5 h-5 text-teal-600" />
            <span>Patient Longitudinal Directory</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Access authorized patient demographic and longitudinal medical profiles ({totalCount.toLocaleString()} total registered).
          </p>
        </div>

        {/* District Search Filter */}
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchDistrict}
              onChange={(e) => setSearchDistrict(e.target.value)}
              placeholder="Filter by district..."
              className="pl-9 pr-3 py-1.5 bg-white border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/20"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-xl transition-colors"
          >
            Filter
          </button>
        </form>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Patients Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-xs text-slate-400">Loading patient cohort...</div>
        ) : patients.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400">No patient records found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-slate-50 border-b border-slate-100 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Patient Name</th>
                  <th className="py-3 px-4">Patient ID</th>
                  <th className="py-3 px-4">Gender / DOB</th>
                  <th className="py-3 px-4">City / State</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {patients.map((p) => (
                  <tr key={p.patient_id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-900">
                      {p.first_name} {p.last_name}
                    </td>
                    <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                      {p.patient_id}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {p.gender} • {p.date_of_birth}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {p.city || p.state || 'Registered District'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => loadPatientDetails(p.patient_id)}
                        className="px-3 py-1 bg-teal-50 hover:bg-teal-100 text-teal-800 font-semibold rounded-lg transition-colors inline-flex items-center gap-1"
                      >
                        <span>View EHR</span>
                        <ChevronRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        <div className="px-4 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
          <span>Page {page} of {Math.ceil(totalCount / pageSize) || 1}</span>
          <div className="flex gap-1.5">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              className="px-2.5 py-1 bg-white border border-slate-200 rounded-lg disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page * pageSize >= totalCount}
              className="px-2.5 py-1 bg-white border border-slate-200 rounded-lg disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
