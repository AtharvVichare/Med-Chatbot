import React, { useEffect, useState } from 'react';
import { 
  Users, 
  Plus, 
  Trash2, 
  Dna, 
  X, 
  Search,
  CheckCircle2,
  ShieldAlert,
  Eye,
  UserCheck,
  RefreshCw
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { 
  FamilyMember, 
  FamilySearchResult, 
  FamilyLink, 
  ConnectedFamilyMember, 
  PermittedFamilyEHR 
} from '../types';

const PERMISSION_OPTIONS = [
  { key: 'view_basic_health', label: 'View Basic Health (Vitals & Allergies)', desc: 'Ambulatory blood pressure, heart rate, SpO2, and known allergies' },
  { key: 'view_medical_history', label: 'View Medical History', desc: 'Diagnoses, conditions, active medications, and hospital encounters' },
  { key: 'view_reports', label: 'View Diagnostic Reports', desc: 'Laboratory results, blood tests, and medical documents' },
  { key: 'manage_appointments', label: 'Manage Appointments', desc: 'Book, reschedule, or cancel consultations and hospital visits' },
  { key: 'receive_reminders', label: 'Receive Reminders', desc: 'Medication alerts, follow-up dates, and clinical notices' },
  { key: 'assist_admissions', label: 'Assist Hospital Admissions', desc: 'Coordinate bed allocation and admission intake workflows' }
];

export const FamilyHistoryPage: React.FC = () => {
  const { user } = useAuth();
  const patientId = user?.patient_id || 'PAT-AARAV-001';

  const [mainTab, setMainTab] = useState<'connected_accounts' | 'hereditary_pedigree'>('connected_accounts');
  const [loading, setLoading] = useState(true);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Connected Family Accounts State
  const [connectedMembers, setConnectedMembers] = useState<ConnectedFamilyMember[]>([]);
  const [linkRequests, setLinkRequests] = useState<FamilyLink[]>([]);
  const [selectedFamilyMemberId, setSelectedFamilyMemberId] = useState<string | null>(null);
  const [permittedEHR, setPermittedEHR] = useState<PermittedFamilyEHR | null>(null);
  const [ehrLoading, setEhrLoading] = useState(false);

  // Search & Link Request Modal State
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<FamilySearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedPersonForLink, setSelectedPersonForLink] = useState<FamilySearchResult | null>(null);
  const [linkRelationship, setLinkRelationship] = useState('spouse');
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([
    'view_basic_health',
    'view_medical_history',
    'view_reports',
    'manage_appointments',
    'receive_reminders'
  ]);
  const [linkNotes, setLinkNotes] = useState('');
  const [isSubmittingLink, setIsSubmittingLink] = useState(false);

  // Hereditary Pedigree State
  const [pedigreeMembers, setPedigreeMembers] = useState<FamilyMember[]>([]);
  const [showAddPedigreeModal, setShowAddPedigreeModal] = useState(false);
  const [pedigreeRelationType, setPedigreeRelationType] = useState('mother');
  const [pedigreeRelativeName, setPedigreeRelativeName] = useState('');
  const [pedigreeIsDeceased, setPedigreeIsDeceased] = useState(false);
  const [pedigreeConditionName, setPedigreeConditionName] = useState('Type 2 Diabetes Mellitus');
  const [pedigreeOnsetAge, setPedigreeOnsetAge] = useState<number | undefined>(52);
  const [pedigreeNotes, setPedigreeNotes] = useState('');

  const loadFamilyData = async () => {
    setLoading(true);
    try {
      const [members, requests, pedigree] = await Promise.all([
        api.listConnectedFamilyMembers(),
        api.listFamilyLinkRequests('all'),
        api.getPatientFamilyHistory(patientId)
      ]);
      setConnectedMembers(members);
      setLinkRequests(requests);
      setPedigreeMembers(pedigree);

      // Auto-select first connected member if none selected
      if (members.length > 0 && !selectedFamilyMemberId) {
        handleSelectFamilyMember(members[0].patient_id);
      }
    } catch (err) {
      console.error('Failed to load family data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFamilyData();
  }, [patientId]);

  const handleSelectFamilyMember = async (targetPatientId: string) => {
    setSelectedFamilyMemberId(targetPatientId);
    setEhrLoading(true);
    try {
      const ehr = await api.getFamilyMemberPermittedEhr(targetPatientId);
      setPermittedEHR(ehr);
    } catch (err: any) {
      console.error('Failed to load permitted family EHR:', err);
      alert('Unable to load family member record. Consent check failed.');
    } finally {
      setEhrLoading(false);
    }
  };

  const handleSearchFamily = async (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim().length < 2) return;
    setIsSearching(true);
    try {
      const results = await api.searchFamilyMembers(searchQuery.trim());
      setSearchResults(results);
    } catch (err: any) {
      alert(`Search failed: ${err.message}`);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSendLinkRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPersonForLink) return;
    setIsSubmittingLink(true);
    try {
      await api.sendFamilyLinkRequest({
        target_patient_id: selectedPersonForLink.patient_id,
        relationship_type: linkRelationship,
        permissions: selectedPermissions,
        notes: linkNotes
      });
      setSuccessMessage(`Family connection request sent to ${selectedPersonForLink.full_name}. Awaiting their in-app approval.`);
      setShowSearchModal(false);
      setSelectedPersonForLink(null);
      setSearchResults([]);
      setSearchQuery('');
      loadFamilyData();
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: any) {
      alert(`Failed to send link request: ${err.message}`);
    } finally {
      setIsSubmittingLink(false);
    }
  };

  const handleRespondRequest = async (linkId: string, action: 'approve' | 'reject') => {
    try {
      await api.respondFamilyLinkRequest(linkId, action);
      setSuccessMessage(`Connection request ${action === 'approve' ? 'Approved & Linked' : 'Rejected'}.`);
      loadFamilyData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`Response action failed: ${err.message}`);
    }
  };

  const handleRevokeLink = async (linkId: string, name: string) => {
    if (!confirm(`Revoke family access connection with ${name}? They will no longer be able to view permitted health records.`)) return;
    try {
      await api.revokeFamilyLink(linkId);
      setSuccessMessage(`Family link with ${name} revoked.`);
      if (selectedFamilyMemberId === name) {
        setSelectedFamilyMemberId(null);
        setPermittedEHR(null);
      }
      loadFamilyData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(`Failed to revoke link: ${err.message}`);
    }
  };

  const handleAddPedigreeMember = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.addPatientFamilyMember(patientId, {
        relation_type: pedigreeRelationType,
        relative_name: pedigreeRelativeName.trim() || undefined,
        is_deceased: pedigreeIsDeceased,
        notes: pedigreeNotes.trim() || undefined,
        conditions: pedigreeConditionName ? [{
          condition_name: pedigreeConditionName,
          approximate_age_at_onset: pedigreeOnsetAge ? Number(pedigreeOnsetAge) : undefined
        }] : []
      });
      setSuccessMessage('Relative added to hereditary pedigree.');
      setShowAddPedigreeModal(false);
      setPedigreeRelativeName('');
      setPedigreeNotes('');
      loadFamilyData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to add relative to pedigree');
    }
  };

  const togglePermission = (key: string) => {
    if (selectedPermissions.includes(key)) {
      setSelectedPermissions(selectedPermissions.filter(k => k !== key));
    } else {
      setSelectedPermissions([...selectedPermissions, key]);
    }
  };

  const incomingRequests = linkRequests.filter(r => r.target_patient_id === patientId && r.status === 'pending');
  const outgoingRequests = linkRequests.filter(r => r.requester_patient_id === patientId && r.status === 'pending');

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-100 text-teal-800">
              Consent-Based Proxy Care
            </span>
            <span className="text-xs text-slate-500">
              Zero Medical Record Merging · Independent Isolation
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <Users className="w-6 h-6 text-teal-600" />
            <span>Family Accounts & Health Network</span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Connect registered family members to coordinate care, track follow-ups, and share permitted records under verified consent.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => {
              setShowSearchModal(true);
              setSearchResults([]);
              setSelectedPersonForLink(null);
            }}
            className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5 shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Connect Family Member</span>
          </button>
          <button
            onClick={loadFamilyData}
            className="p-2 border border-slate-200 rounded-xl hover:bg-slate-50 text-slate-600 transition"
            title="Refresh family network"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Mode Toggle Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setMainTab('connected_accounts')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            mainTab === 'connected_accounts'
              ? 'bg-teal-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>Connected Family Accounts & Proxy Care ({connectedMembers.length})</span>
        </button>

        <button
          onClick={() => setMainTab('hereditary_pedigree')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
            mainTab === 'hereditary_pedigree'
              ? 'bg-teal-600 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Dna className="w-3.5 h-3.5" />
          <span>Hereditary Pedigree & Genetic Risk</span>
        </button>
      </div>

      {loading && connectedMembers.length === 0 && (
        <div className="p-4 bg-teal-50 border border-teal-200 rounded-xl text-xs text-teal-800 flex items-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-teal-600 shrink-0" />
          <span>Loading connected family records...</span>
        </div>
      )}

      {ehrLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl p-6 shadow-xl flex items-center gap-3">
            <RefreshCw className="w-5 h-5 animate-spin text-teal-600" />
            <span className="text-sm font-medium text-slate-700">Loading permitted family health records...</span>
          </div>
        </div>
      )}

      {successMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* TAB 1: CONNECTED FAMILY ACCOUNTS & PROXY CARE */}
      {mainTab === 'connected_accounts' && (
        <div className="space-y-6">
          {/* Incoming Approval Requests Banner */}
          {incomingRequests.length > 0 && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl space-y-3">
              <div className="flex items-center gap-2 text-amber-900 font-bold text-xs uppercase tracking-wider">
                <ShieldAlert className="w-4 h-4 text-amber-600" />
                <span>Pending Family Link Requests Requiring Your Approval ({incomingRequests.length})</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {incomingRequests.map((req) => (
                  <div key={req.link_id} className="p-3 bg-white rounded-xl border border-amber-200 text-xs space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-slate-900">{req.requester_name || req.requester_patient_id}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 capitalize">
                        Relationship: {req.relationship_type}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Requests permission to coordinate care and access permitted EHR sections.
                    </p>
                    <div className="flex gap-2 pt-1">
                      <button
                        onClick={() => handleRespondRequest(req.link_id, 'approve')}
                        className="flex-1 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition flex items-center justify-center gap-1"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Approve Connection</span>
                      </button>
                      <button
                        onClick={() => handleRespondRequest(req.link_id, 'reject')}
                        className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition"
                      >
                        Decline
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Outgoing Pending Requests */}
          {outgoingRequests.length > 0 && (
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-2">
              <span className="text-xs font-bold text-slate-700">Sent Link Requests Awaiting Approval ({outgoingRequests.length})</span>
              <div className="flex flex-wrap gap-2">
                {outgoingRequests.map(r => (
                  <span key={r.link_id} className="px-3 py-1 bg-white border border-slate-200 rounded-lg text-xs text-slate-600">
                    To: <strong className="text-slate-800">{r.target_patient_id}</strong> ({r.relationship_type}) · Status: Pending Approval
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Profile Switcher & Connected Members */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <UserCheck className="w-5 h-5 text-teal-600" />
                  <span>Linked Family Members & Proxy Profiles</span>
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Select a family member to switch perspective and review their permitted longitudinal health record.
                </p>
              </div>
            </div>

            {connectedMembers.length === 0 ? (
              <div className="text-center py-10 text-slate-400 text-xs space-y-2">
                <Users className="w-10 h-10 mx-auto text-slate-300" />
                <p>No family accounts connected yet.</p>
                <button
                  onClick={() => setShowSearchModal(true)}
                  className="px-3.5 py-1.5 bg-teal-600 text-white rounded-xl text-xs font-bold"
                >
                  Connect Your First Family Member
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {connectedMembers.map((member) => {
                  const isSelected = selectedFamilyMemberId === member.patient_id;
                  return (
                    <div
                      key={member.link_id}
                      onClick={() => handleSelectFamilyMember(member.patient_id)}
                      className={`p-4 rounded-xl border text-xs cursor-pointer transition relative ${
                        isSelected
                          ? 'border-teal-500 bg-teal-50/50 shadow-xs'
                          : 'border-slate-200 bg-slate-50/50 hover:bg-white hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm text-slate-900">{member.full_name}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 capitalize">
                          {member.relationship_type}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 mt-1">
                        {member.age}yo · {member.gender} · ID: {member.patient_id}
                      </div>

                      <div className="flex flex-wrap gap-1 mt-2.5">
                        {member.can_view_records && (
                          <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-800 rounded text-[9px] font-bold">
                            EHR View
                          </span>
                        )}
                        {member.can_manage_appointments && (
                          <span className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded text-[9px] font-bold">
                            Appointments
                          </span>
                        )}
                        {member.can_view_reports && (
                          <span className="px-1.5 py-0.5 bg-purple-100 text-purple-800 rounded text-[9px] font-bold">
                            Reports
                          </span>
                        )}
                      </div>

                      <div className="mt-3 pt-2.5 border-t border-slate-200/80 flex items-center justify-between text-[11px]">
                        <span className="text-teal-700 font-bold flex items-center gap-1">
                          <Eye className="w-3.5 h-3.5" />
                          <span>{isSelected ? 'Currently Viewing' : 'View Health Record'}</span>
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRevokeLink(member.link_id, member.full_name);
                          }}
                          className="text-slate-400 hover:text-rose-600 transition"
                          title="Revoke connection"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* PERMITTED LONGITUDINAL EHR VIEWER FOR SELECTED FAMILY MEMBER */}
          {selectedFamilyMemberId && permittedEHR && (
            <div className="bg-white rounded-2xl p-6 border border-teal-200 shadow-xs space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-teal-100 text-teal-800 uppercase">
                      Permitted Family Health Record
                    </span>
                    <span className="text-xs text-slate-400">
                      Relation: <strong>{permittedEHR.relationship_type}</strong>
                    </span>
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mt-1">
                    {permittedEHR.demographics.first_name} {permittedEHR.demographics.last_name} ({permittedEHR.patient_id})
                  </h3>
                  <p className="text-xs text-slate-500">
                    Age: {permittedEHR.demographics.age} · Gender: {permittedEHR.demographics.gender} · Blood Group: {permittedEHR.demographics.blood_group} · District: {permittedEHR.demographics.district}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 font-medium">Permitted Scopes:</span>
                  <div className="flex flex-wrap gap-1">
                    {permittedEHR.permitted_scopes.map((scope, idx) => (
                      <span key={idx} className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-bold">
                        {scope.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Allergies & Latest Vitals */}
              {permittedEHR.allergies && permittedEHR.allergies.length > 0 && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl space-y-1">
                  <span className="text-xs font-bold text-rose-800 uppercase flex items-center gap-1.5">
                    <ShieldAlert className="w-4 h-4 text-rose-600" />
                    Verified Known Allergies
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {permittedEHR.allergies.map((alg: any) => (
                      <span key={alg.allergy_id} className="px-2 py-0.5 bg-white border border-rose-200 rounded text-xs text-rose-900 font-medium">
                        {alg.substance} ({alg.reaction})
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Conditions & Prescriptions */}
              {permittedEHR.conditions && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                    <span className="font-bold text-slate-900 block uppercase tracking-wider">
                      Diagnosed Conditions
                    </span>
                    <div className="space-y-1.5">
                      {permittedEHR.conditions.map((c: any, idx: number) => (
                        <div key={idx} className="p-2 bg-white rounded-lg border border-slate-200/80 flex items-center justify-between">
                          <span className="font-semibold text-slate-800">{c.diagnosis_name}</span>
                          <span className="text-[10px] text-slate-400">{c.code} · {c.status}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {permittedEHR.medications && (
                    <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                      <span className="font-bold text-slate-900 block uppercase tracking-wider">
                        Active Prescribed Medications
                      </span>
                      <div className="space-y-1.5">
                        {permittedEHR.medications.map((m: any, idx: number) => (
                          <div key={idx} className="p-2 bg-white rounded-lg border border-slate-200/80 flex items-center justify-between">
                            <span className="font-semibold text-slate-800">{m.medication_name}</span>
                            <span className="text-[10px] text-blue-700 font-medium">{m.dosage}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Lab Observations */}
              {permittedEHR.observations && permittedEHR.observations.length > 0 && (
                <div className="space-y-2">
                  <span className="font-bold text-slate-900 block text-xs uppercase tracking-wider">
                    Recent Laboratory Findings
                  </span>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-50 text-slate-500 font-semibold border-y border-slate-200">
                        <tr>
                          <th className="py-2 px-2.5">Investigation</th>
                          <th className="py-2 px-2.5">Result</th>
                          <th className="py-2 px-2.5">Reference Range</th>
                          <th className="py-2 px-2.5">Interpretation</th>
                          <th className="py-2 px-2.5">Date</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {permittedEHR.observations.slice(0, 5).map((obs: any, idx: number) => (
                          <tr key={idx}>
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
              )}

              {/* Uploaded Documents */}
              {permittedEHR.documents && permittedEHR.documents.length > 0 && (
                <div className="space-y-2">
                  <span className="font-bold text-slate-900 block text-xs uppercase tracking-wider">
                    Shared Clinical Documents & Reports
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {permittedEHR.documents.map((doc: any) => (
                      <div key={doc.document_id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                        <div className="font-bold text-slate-900 truncate">{doc.file_name}</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">Date: {doc.report_date} · Type: {doc.document_type}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: HEREDITARY PEDIGREE & GENETIC RISK */}
      {mainTab === 'hereditary_pedigree' && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-xs space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Dna className="w-5 h-5 text-indigo-600" />
                <span>Multi-Generational Genetic Pedigree</span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Family medical history tracking for cardiovascular disease, diabetes, hypertension, and hereditary conditions.
              </p>
            </div>
            <button
              onClick={() => setShowAddPedigreeModal(true)}
              className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Pedigree Relative</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {pedigreeMembers.map((member) => (
              <div key={member.id} className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">{member.relative_name || 'Relative'}</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800 capitalize">
                    {member.relation_type}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500">
                  Lineage: <strong>{member.lineage || 'Paternal'}</strong> · Status: {member.is_deceased ? 'Deceased' : 'Living'}
                </div>

                <div className="space-y-1 pt-1 border-t border-slate-200/80">
                  {member.conditions && member.conditions.map((c: any, i: number) => (
                    <div key={i} className="p-1.5 bg-white rounded border border-slate-200 text-[11px] flex justify-between">
                      <span className="font-medium text-slate-800">{c.condition_name}</span>
                      {c.approximate_age_at_onset && (
                        <span className="text-slate-400">Onset ~{c.approximate_age_at_onset}y</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* DISCOVER & SEND FAMILY LINK MODAL */}
      {showSearchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl w-full max-w-lg border border-slate-200 shadow-xl p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Users className="w-4 h-4 text-teal-600" />
                <span>Connect a Family Member</span>
              </h3>
              <button onClick={() => setShowSearchModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {!selectedPersonForLink ? (
              <div className="space-y-4 text-xs">
                <p className="text-slate-500">
                  Search registered family members by full name or Patient ID. Matching results display masked contact info to maintain strict medical privacy until link approval.
                </p>

                <form onSubmit={handleSearchFamily} className="flex gap-2">
                  <div className="relative flex-1">
                    <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      placeholder="e.g. Priya Mehta, Sunita, PAT-PRIYA-002"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isSearching}
                    className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white font-bold rounded-xl"
                  >
                    {isSearching ? 'Searching...' : 'Find'}
                  </button>
                </form>

                {searchResults.length > 0 && (
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    <span className="font-bold text-slate-700 block text-[11px] uppercase">Matching Accounts</span>
                    {searchResults.map((res) => (
                      <div
                        key={res.patient_id}
                        onClick={() => setSelectedPersonForLink(res)}
                        className="p-3 rounded-xl border border-slate-200 hover:border-teal-500 hover:bg-teal-50/40 cursor-pointer transition flex items-center justify-between"
                      >
                        <div>
                          <div className="font-bold text-slate-900">{res.full_name}</div>
                          <div className="text-[11px] text-slate-500">
                            Age: {res.age_bracket} · Contact: {res.masked_contact || 'Masked'} · {res.city_district}
                          </div>
                        </div>
                        <span className="px-2.5 py-1 bg-teal-600 text-white rounded-lg text-[10px] font-bold">
                          Select
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <form onSubmit={handleSendLinkRequest} className="space-y-3.5 text-xs">
                <div className="p-3 bg-teal-50 rounded-xl border border-teal-200">
                  <span className="text-[10px] uppercase font-bold text-teal-800">Selected Target Account</span>
                  <div className="font-bold text-slate-900 text-sm mt-0.5">{selectedPersonForLink.full_name}</div>
                  <div className="text-slate-600 text-[11px]">ID: {selectedPersonForLink.patient_id} · {selectedPersonForLink.age_bracket}</div>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Relationship Type *</label>
                  <select
                    value={linkRelationship}
                    onChange={(e) => setLinkRelationship(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-medium"
                  >
                    <option value="spouse">Spouse / Partner</option>
                    <option value="parent">Parent</option>
                    <option value="child">Child / Dependant</option>
                    <option value="sibling">Sibling (Brother / Sister)</option>
                    <option value="guardian">Legal Guardian</option>
                    <option value="other">Other Relative</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1.5">
                    Select Permissions to Request & Grant *
                  </label>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {PERMISSION_OPTIONS.map((opt) => {
                      const isChecked = selectedPermissions.includes(opt.key);
                      return (
                        <div
                          key={opt.key}
                          onClick={() => togglePermission(opt.key)}
                          className={`p-2 rounded-lg border cursor-pointer transition flex items-start gap-2 ${
                            isChecked ? 'border-teal-500 bg-teal-50/50' : 'border-slate-200 bg-slate-50/50'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => {}}
                            className="mt-0.5"
                          />
                          <div>
                            <span className="font-bold text-slate-800 block">{opt.label}</span>
                            <span className="text-[10px] text-slate-500">{opt.desc}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Invitation Notes</label>
                  <input
                    type="text"
                    value={linkNotes}
                    onChange={(e) => setLinkNotes(e.target.value)}
                    placeholder="e.g. Connecting so we can coordinate hospital checkups"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  />
                </div>

                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setSelectedPersonForLink(null)}
                    className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold"
                  >
                    Back to Search
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingLink}
                    className="flex-1 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl font-bold"
                  >
                    {isSubmittingLink ? 'Sending...' : 'Send Link Request'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ADD PEDIGREE MEMBER MODAL */}
      {showAddPedigreeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl w-full max-w-md border border-slate-200 shadow-xl p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Dna className="w-4 h-4 text-indigo-600" />
                <span>Add Relative to Hereditary Pedigree</span>
              </h3>
              <button onClick={() => setShowAddPedigreeModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleAddPedigreeMember} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Relationship</label>
                  <select
                    value={pedigreeRelationType}
                    onChange={(e) => setPedigreeRelationType(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  >
                    <option value="mother">Mother</option>
                    <option value="father">Father</option>
                    <option value="brother">Brother</option>
                    <option value="sister">Sister</option>
                    <option value="maternal_grandmother">Maternal Grandmother</option>
                    <option value="maternal_grandfather">Maternal Grandfather</option>
                    <option value="paternal_grandmother">Paternal Grandmother</option>
                    <option value="paternal_grandfather">Paternal Grandfather</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Relative Name</label>
                  <input
                    type="text"
                    value={pedigreeRelativeName}
                    onChange={(e) => setPedigreeRelativeName(e.target.value)}
                    placeholder="e.g. Ramesh Mehta"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Documented Condition</label>
                <input
                  type="text"
                  value={pedigreeConditionName}
                  onChange={(e) => setPedigreeConditionName(e.target.value)}
                  placeholder="e.g. Essential Hypertension, Coronary Artery Disease"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Approximate Age at Onset</label>
                  <input
                    type="number"
                    value={pedigreeOnsetAge || ''}
                    onChange={(e) => setPedigreeOnsetAge(e.target.value ? Number(e.target.value) : undefined)}
                    placeholder="e.g. 52"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl"
                  />
                </div>
                <div className="flex items-center pt-5">
                  <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700">
                    <input
                      type="checkbox"
                      checked={pedigreeIsDeceased}
                      onChange={(e) => setPedigreeIsDeceased(e.target.checked)}
                    />
                    <span>Deceased</span>
                  </label>
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddPedigreeModal(false)}
                  className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold"
                >
                  Add to Pedigree
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
