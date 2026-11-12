import React, { useEffect, useState } from 'react';
import { 
  Users, 
  Plus, 
  Trash2, 
  Dna, 
  X, 
  Info
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { FamilyMember } from '../types';

export const FamilyHistoryPage: React.FC = () => {
  const { user } = useAuth();
  const patientId = user?.patient_id || 'PAT-00001';

  const [familyMembers, setFamilyMembers] = useState<FamilyMember[]>([]);
  const [loading, setLoading] = useState(true);

  // Add Relative Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [relationType, setRelationType] = useState('father');
  const [relativeName, setRelativeName] = useState('');
  const [isDeceased, setIsDeceased] = useState(false);
  const [conditionName, setConditionName] = useState('Type 2 Diabetes');
  const [onsetAge, setOnsetAge] = useState<number | undefined>(52);
  const [notes, setNotes] = useState('');

  const fetchFamilyHistory = async () => {
    setLoading(true);
    try {
      const res = await api.getPatientFamilyHistory(patientId);
      setFamilyMembers(res);
    } catch (err) {
      console.error('Failed to load family history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFamilyHistory();
  }, [patientId]);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.addPatientFamilyMember(patientId, {
        relation_type: relationType,
        relative_name: relativeName.trim() || undefined,
        is_deceased: isDeceased,
        notes: notes.trim() || undefined,
        conditions: conditionName ? [{
          condition_name: conditionName,
          approximate_age_at_onset: onsetAge ? Number(onsetAge) : undefined
        }] : []
      });

      setShowAddModal(false);
      setRelativeName('');
      setNotes('');
      fetchFamilyHistory();
    } catch (err: any) {
      alert(err.message || 'Failed to add family member');
    }
  };

  const handleDeleteMember = async (memberId: string) => {
    if (!confirm('Remove this family member from pedigree history?')) return;
    try {
      await api.deletePatientFamilyMember(patientId, memberId);
      fetchFamilyHistory();
    } catch (err: any) {
      alert(err.message || 'Failed to delete record');
    }
  };

  // Extract hereditary condition summary
  const allConditions = familyMembers.flatMap(m => m.conditions || []);
  const conditionFrequencies: Record<string, number> = {};
  allConditions.forEach(c => {
    conditionFrequencies[c.condition_name] = (conditionFrequencies[c.condition_name] || 0) + 1;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Family Health History</h1>
          <p className="text-xs text-slate-500 mt-1">
            Track multi-generational genetic predispositions and hereditary risk factors for {patientId}
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-xl shadow-sm transition"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add Family Member</span>
        </button>
      </div>

      {/* Hereditary Overview & Insights */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 p-5 bg-white rounded-xl border border-slate-200/80 shadow-sm space-y-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center">
              <Dna className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-bold text-slate-900">Pedigree Risk Summary</h2>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Multi-generational family health tracking identifies shared familial, environmental, and genetic patterns that inform preventive care and screening schedules.
          </p>

          <div className="flex flex-wrap gap-2 pt-2">
            {Object.keys(conditionFrequencies).length === 0 ? (
              <span className="text-xs text-slate-400">No familial hereditary patterns logged yet.</span>
            ) : (
              Object.entries(conditionFrequencies).map(([cond, count]) => (
                <div key={cond} className="px-3 py-1.5 rounded-lg bg-teal-50 text-teal-800 border border-teal-100 text-xs font-medium flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-teal-500"></span>
                  <span>{cond}</span>
                  <span className="px-1.5 py-0.2 bg-teal-200/60 rounded text-[10px] font-bold text-teal-900">
                    {count} {count > 1 ? 'relatives' : 'relative'}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="p-5 bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl border border-amber-200/60 text-xs text-amber-900 space-y-2">
          <div className="flex items-center gap-2 font-bold text-amber-800">
            <Info className="w-4 h-4 text-amber-600" />
            <span>Clinical Preventive Screening</span>
          </div>
          <p className="leading-relaxed">
            If first-degree relatives (parents, siblings) developed Type 2 Diabetes or early cardiovascular disease before age 55, guidelines recommend annual HbA1c screening starting at age 35.
          </p>
        </div>
      </div>

      {/* Family Pedigree Members List */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-900">Recorded Relatives & Lineage</h2>
          <span className="text-xs text-slate-500">{familyMembers.length} relatives documented</span>
        </div>

        {loading ? (
          <p className="py-8 text-center text-xs text-slate-400">Loading pedigree records...</p>
        ) : familyMembers.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-400">
            <Users className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p>No family history recorded yet.</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="mt-3 text-teal-600 font-semibold hover:underline"
            >
              Add first-degree relative
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {familyMembers.map(member => (
              <div
                key={member.id}
                className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:border-teal-200 transition space-y-3"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
                      {member.relation_type.replace(/_/g, ' ')}
                    </span>
                    <h3 className="text-sm font-bold text-slate-900 mt-1">
                      {member.relative_name || member.relation_type.charAt(0).toUpperCase() + member.relation_type.slice(1)}
                    </h3>
                  </div>
                  <button
                    onClick={() => handleDeleteMember(member.id)}
                    className="p-1 text-slate-400 hover:text-rose-600 rounded"
                    title="Delete relative"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="space-y-1 text-xs">
                  <span className="text-[11px] font-semibold text-slate-500 block">Hereditary Conditions:</span>
                  {member.conditions && member.conditions.length > 0 ? (
                    member.conditions.map((c, i) => (
                      <div key={i} className="flex items-center justify-between bg-white px-2.5 py-1.5 rounded-lg border border-slate-200/80">
                        <span className="font-semibold text-slate-800">{c.condition_name}</span>
                        {c.approximate_age_at_onset && (
                          <span className="text-[10px] text-slate-500">Onset ~{c.approximate_age_at_onset} yrs</span>
                        )}
                      </div>
                    ))
                  ) : (
                    <span className="text-slate-400 italic">No chronic illnesses noted</span>
                  )}
                </div>

                {member.is_deceased && (
                  <span className="inline-block text-[10px] text-slate-500 italic">
                    Status: Deceased
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal: Add Relative */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">Add Family Member</h3>
              <button onClick={() => setShowAddModal(false)}><X className="w-4 h-4 text-slate-400" /></button>
            </div>

            <form onSubmit={handleAddMember} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Relationship to Patient *</label>
                <select
                  value={relationType}
                  onChange={e => setRelationType(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                >
                  <option value="father">Father (1st Degree)</option>
                  <option value="mother">Mother (1st Degree)</option>
                  <option value="sister">Sister (1st Degree)</option>
                  <option value="brother">Brother (1st Degree)</option>
                  <option value="maternal_grandmother">Maternal Grandmother</option>
                  <option value="maternal_grandfather">Maternal Grandfather</option>
                  <option value="paternal_grandmother">Paternal Grandmother</option>
                  <option value="paternal_grandfather">Paternal Grandfather</option>
                  <option value="child">Child (Son / Daughter)</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Relative's Name (Optional)</label>
                <input
                  type="text"
                  value={relativeName}
                  onChange={e => setRelativeName(e.target.value)}
                  placeholder="e.g. Suresh Nair"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Hereditary Condition</label>
                  <input
                    type="text"
                    value={conditionName}
                    onChange={e => setConditionName(e.target.value)}
                    placeholder="e.g. Type 2 Diabetes"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Age at Onset (Approx)</label>
                  <input
                    type="number"
                    value={onsetAge || ''}
                    onChange={e => setOnsetAge(e.target.value ? Number(e.target.value) : undefined)}
                    placeholder="e.g. 50"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="is_dec"
                  checked={isDeceased}
                  onChange={e => setIsDeceased(e.target.checked)}
                  className="rounded text-teal-600"
                />
                <label htmlFor="is_dec" className="text-slate-700">Relative is deceased</label>
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-teal-600 text-white font-semibold rounded-lg"
                >
                  Save to Pedigree
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
