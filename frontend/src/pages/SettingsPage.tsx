import React, { useEffect, useState } from 'react';
import { 
  User, 
  Lock, 
  Download, 
  Save, 
  CheckCircle2, 
  AlertCircle
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { Patient } from '../types';

export const SettingsPage: React.FC = () => {
  const { user, updateUser } = useAuth();
  const isPatient = user?.role === 'patient';
  const patientId = isPatient ? (user?.patient_id || 'PAT-AARAV-001') : null;

  const [patient, setPatient] = useState<Patient | null>(null);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [district, setDistrict] = useState('');
  const [stateName, setStateName] = useState('Maharashtra');
  const [gender, setGender] = useState('female');
  const [dateOfBirth, setDateOfBirth] = useState('1995-05-15');
  const [bloodGroup, setBloodGroup] = useState('O+');
  const [isSmoker, setIsSmoker] = useState(false);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Password reset state
  const [resetEmail, setResetEmail] = useState('');
  const [resetSuccess, setResetSuccess] = useState<string | null>(null);

  const calculateAge = (dobString: string): number | null => {
    if (!dobString) return null;
    const dob = new Date(dobString);
    if (isNaN(dob.getTime())) return null;
    const today = new Date();
    let age = today.getFullYear() - dob.getFullYear();
    const m = today.getMonth() - dob.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) {
      age--;
    }
    return Math.max(0, age);
  };

  useEffect(() => {
    const fetchProfile = async () => {
      setLoading(true);
      if (isPatient && patientId) {
        try {
          const p = await api.getPatient(patientId);
          setPatient(p);
          setFirstName(p.first_name || '');
          setLastName(p.last_name || '');
          setPhone(p.phone_number || p.contact_no || '');
          setDistrict(p.district || 'Mumbai');
          setStateName(p.state || 'Maharashtra');
          setGender((p.gender || p.sex || user?.gender || 'unspecified').toLowerCase());
          setDateOfBirth(p.date_of_birth || p.birth_date || user?.date_of_birth || '1995-05-15');
          setBloodGroup(p.blood_group || p.blood_type || 'O+');
          setIsSmoker(Boolean(p.is_smoker));
        } catch (err: any) {
          setErrorMsg(err.message || 'Failed to load profile');
        } finally {
          setLoading(false);
        }
      } else {
        // Clinician / Staff profile (Doctor, Nurse, Admin)
        const fullName = user?.full_name || 'Dr. Priya Deshmukh';
        const nameParts = fullName.split(' ');
        setFirstName(nameParts[0]);
        setLastName(nameParts.slice(1).join(' '));
        setPhone('+91 22 2410 7000');
        setDistrict('Mumbai');
        setStateName('Maharashtra');
        setLoading(false);
      }
    };
    fetchProfile();
  }, [user, patientId, isPatient]);

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(null);
    setErrorMsg(null);
    try {
      if (isPatient && patientId) {
        const updated = await api.updatePatient(patientId, {
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          phone_number: phone.trim() || undefined,
          district: district.trim() || undefined,
          state: stateName.trim() || undefined,
          gender: gender,
          date_of_birth: dateOfBirth || undefined,
          is_smoker: isSmoker,
          blood_group: bloodGroup
        });
        setPatient(updated);
        updateUser({
          full_name: `${firstName.trim()} ${lastName.trim()}`,
          gender: gender,
          date_of_birth: dateOfBirth
        });
      }
      setSaveSuccess(`${isPatient ? 'Health record demographic & biological profile' : 'Staff profile'} successfully updated!`);
    } catch (err: any) {
      setErrorMsg(err.message || 'Update failed');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetEmail) return;
    try {
      const res = await api.forgotPassword(resetEmail.trim());
      setResetSuccess(res.message);
    } catch (err: any) {
      alert(err.message || 'Failed to trigger reset');
    }
  };

  const handleExportData = async () => {
    if (!patientId) {
      alert('Data export is available for patient longitudinal health records.');
      return;
    }
    try {
      const [pat, conds, meds, allgs, docs] = await Promise.all([
        api.getPatient(patientId),
        api.getPatientConditions(patientId),
        api.getPatientMedications(patientId),
        api.getPatientAllergies(patientId),
        api.getPatientDocuments(patientId)
      ]);

      const exportObj = {
        export_date: new Date().toISOString(),
        patient_summary: pat,
        active_conditions: conds,
        medications: meds,
        allergies: allgs,
        uploaded_documents: docs
      };

      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportObj, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `Aarogya_Health_Record_${patientId}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (err: any) {
      alert('Failed to export record data.');
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Account & Profile Settings</h1>
        <p className="text-xs text-slate-500 mt-1">
          Manage your personal patient details, account security, and health record export
        </p>
      </div>

      {/* Alerts */}
      {saveSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{saveSuccess}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {loading && (
        <div className="p-3 bg-teal-50 border border-teal-200 rounded-xl text-teal-800 text-xs">
          Loading profile settings...
        </div>
      )}

      {/* Profile Details Form */}
      <div className="p-6 bg-white rounded-xl border border-slate-200/80 shadow-sm space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <User className="w-4 h-4 text-teal-600" />
          <h2 className="text-sm font-bold text-slate-900">
            {isPatient ? 'Patient Demographic Information' : 'Clinician & Staff Profile'}
          </h2>
        </div>

        <form onSubmit={handleProfileSave} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">First Name *</label>
              <input
                type="text"
                value={firstName}
                onChange={e => setFirstName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                required
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Last Name *</label>
              <input
                type="text"
                value={lastName}
                onChange={e => setLastName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Contact Phone</label>
              <input
                type="tel"
                value={phone}
                onChange={e => setPhone(e.target.value)}
                placeholder="+91 98201 44521"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                {isPatient ? 'Residential District' : 'Clinical Station / Facility'}
              </label>
              <input
                type="text"
                value={district}
                onChange={e => setDistrict(e.target.value)}
                placeholder="e.g. Mumbai Suburban"
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
              />
            </div>
          </div>

          {isPatient ? (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Gender / Biological Sex *
                  </label>
                  <select
                    value={gender}
                    onChange={e => setGender(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                    required
                  >
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                    <option value="other">Other / Non-Binary</option>
                    <option value="unspecified">Unspecified</option>
                  </select>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block font-semibold text-slate-700">Date of Birth *</label>
                    {dateOfBirth && calculateAge(dateOfBirth) !== null && (
                      <span className="text-[10px] font-bold text-teal-700 bg-teal-100 px-1.5 py-0.5 rounded">
                        Age: {calculateAge(dateOfBirth)} yrs
                      </span>
                    )}
                  </div>
                  <input
                    type="date"
                    value={dateOfBirth}
                    onChange={e => setDateOfBirth(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                    required
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Blood Group</label>
                  <select
                    value={bloodGroup}
                    onChange={e => setBloodGroup(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                  >
                    <option value="O+">O Positive (O+)</option>
                    <option value="O-">O Negative (O-)</option>
                    <option value="A+">A Positive (A+)</option>
                    <option value="A-">A Negative (A-)</option>
                    <option value="B+">B Positive (B+)</option>
                    <option value="B-">B Negative (B-)</option>
                    <option value="AB+">AB Positive (AB+)</option>
                    <option value="AB-">AB Negative (AB-)</option>
                    <option value="Unknown">Unknown / Untested</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">State / Region</label>
                  <input
                    type="text"
                    value={stateName}
                    onChange={e => setStateName(e.target.value)}
                    placeholder="e.g. Maharashtra"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                  />
                </div>
                <div className="flex items-center gap-2 pt-5">
                  <input
                    type="checkbox"
                    id="isSmokerCheck"
                    checked={isSmoker}
                    onChange={e => setIsSmoker(e.target.checked)}
                    className="w-4 h-4 text-teal-600 rounded border-slate-300 focus:ring-teal-500"
                  />
                  <label htmlFor="isSmokerCheck" className="text-xs text-slate-700 select-none">
                    Current or past tobacco / smoking history
                  </label>
                </div>
              </div>

              <div className="p-2.5 bg-teal-50/70 border border-teal-200/60 rounded-lg text-[11px] text-teal-800">
                You can change and keep your gender, birthdate, and demographic baseline details up-to-date at any time. These details are used to calibrate clinical normal ranges and future risk models.
              </div>
            </>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-slate-500 pt-1">
              <div>
                <span className="font-semibold block text-slate-400">Staff Role</span>
                <p className="mt-0.5 font-medium text-slate-700 capitalize">{user?.role?.replace('_', ' ') || 'Staff'}</p>
              </div>
              <div>
                <span className="font-semibold block text-slate-400">Authorized Facility</span>
                <p className="mt-0.5 font-medium text-slate-700">{(user as any)?.facility || 'Seth GS Medical College & KEM Hospital'}</p>
              </div>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg font-semibold shadow-sm transition disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{saving ? 'Saving...' : 'Update Health Profile'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Security & Password Reset */}
      <div className="p-6 bg-white rounded-xl border border-slate-200/80 shadow-sm space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <Lock className="w-4 h-4 text-teal-600" />
          <h2 className="text-sm font-bold text-slate-900">Security & Authentication</h2>
        </div>

        <form onSubmit={handlePasswordReset} className="space-y-3 text-xs max-w-md">
          <label className="block font-semibold text-slate-700">Request Password Reset Link</label>
          <div className="flex gap-2">
            <input
              type="email"
              value={resetEmail}
              onChange={e => setResetEmail(e.target.value)}
              placeholder="Enter your registered email..."
              className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
            />
            <button
              type="submit"
              className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg font-semibold transition shrink-0"
            >
              Send Link
            </button>
          </div>
          {resetSuccess && (
            <p className="text-emerald-700 text-[11px] font-medium">{resetSuccess}</p>
          )}
        </form>
      </div>

      {/* Data Export & Portability */}
      <div className="p-6 bg-white rounded-xl border border-slate-200/80 shadow-sm space-y-3">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <Download className="w-4 h-4 text-teal-600" />
          <h2 className="text-sm font-bold text-slate-900">Data Portability & Lifetime Health Record Export</h2>
        </div>

        <p className="text-xs text-slate-600 leading-relaxed">
          You have full ownership over your longitudinal health data. Download a complete JSON summary of your clinical conditions, medication history, allergies, vitals timeline, and diagnostic documents at any time.
        </p>

        <div className="pt-2">
          <button
            onClick={handleExportData}
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg font-semibold text-xs transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download My Lifetime Health Record (JSON)</span>
          </button>
        </div>
      </div>
    </div>
  );
};
