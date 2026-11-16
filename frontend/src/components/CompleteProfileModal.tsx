import React, { useState } from 'react';
import { User, Calendar, Phone, MapPin, Heart, ArrowRight, ArrowLeft, CheckCircle2, ShieldCheck, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

interface CompleteProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCompleted?: () => void;
}

export const CompleteProfileModal: React.FC<CompleteProfileModalProps> = ({ isOpen, onClose, onCompleted }) => {
  const { user, updateUser } = useAuth();
  const [step, setStep] = useState<number>(1);
  const [gender, setGender] = useState<string>('female');
  const [dateOfBirth, setDateOfBirth] = useState<string>('1995-05-15');
  const [phone, setPhone] = useState<string>('');
  const [district, setDistrict] = useState<string>('Mumbai');
  const [stateName, setStateName] = useState<string>('Maharashtra');
  const [bloodGroup, setBloodGroup] = useState<string>('O+');
  const [isSmoker, setIsSmoker] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen || !user || user.role !== 'patient') return null;

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

  const handleSave = async () => {
    if (!gender || gender === 'unspecified') {
      setErrorMsg('Please specify your gender/biological sex.');
      setStep(1);
      return;
    }
    if (!dateOfBirth) {
      setErrorMsg('Please select your date of birth.');
      setStep(2);
      return;
    }

    setSaving(true);
    setErrorMsg(null);
    try {
      const patientId = user.patient_id || 'PAT-AARAV-001';
      await api.updatePatient(patientId, {
        gender,
        date_of_birth: dateOfBirth,
        phone_number: phone.trim() || undefined,
        district: district.trim() || undefined,
        state: stateName.trim() || undefined,
        blood_group: bloodGroup,
        is_smoker: isSmoker
      });

      updateUser({
        gender,
        date_of_birth: dateOfBirth
      });

      if (onCompleted) onCompleted();
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update profile. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-100 overflow-hidden">
        {/* Header */}
        <div className="p-5 bg-gradient-to-r from-teal-700 to-emerald-600 text-white relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-white/80 hover:text-white p-1 rounded-full hover:bg-white/10 transition"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/20 text-teal-100 text-[11px] font-semibold mb-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Clinical Onboarding</span>
          </div>
          <h2 className="text-xl font-bold tracking-tight">Complete Your Health Profile</h2>
          <p className="text-teal-100 text-xs mt-1">
            Step {step} of 4 · We need your biological baseline to display accurate reference ranges and risk models.
          </p>

          {/* Stepper Progress Bar */}
          <div className="flex gap-1.5 mt-3">
            {[1, 2, 3, 4].map(s => (
              <div
                key={s}
                className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${
                  s <= step ? 'bg-white' : 'bg-white/30'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-4">
          {errorMsg && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl">
              {errorMsg}
            </div>
          )}

          {/* Step 1: Gender */}
          {step === 1 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
                <User className="w-4 h-4 text-teal-600" />
                <span>Select Your Gender / Biological Sex</span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                Biomarkers, hemoglobin baselines, and cardiac indices require biological sex to calibrate standard clinical lab ranges.
              </p>

              <div className="grid grid-cols-3 gap-2.5 pt-2">
                {[
                  { id: 'female', label: 'Female', desc: 'Standard female clinical ranges' },
                  { id: 'male', label: 'Male', desc: 'Standard male clinical ranges' },
                  { id: 'other', label: 'Other', desc: 'Neutral clinical ranges' }
                ].map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setGender(opt.id)}
                    className={`p-3 text-center rounded-xl border-2 transition-all ${
                      gender === opt.id
                        ? 'border-teal-600 bg-teal-50/70 text-teal-900 shadow-sm'
                        : 'border-slate-200 bg-slate-50/50 hover:bg-slate-100 text-slate-700'
                    }`}
                  >
                    <span className="block font-bold text-sm capitalize">{opt.label}</span>
                    <span className="text-[10px] text-slate-500 mt-1 block">{opt.desc}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 2: Date of Birth */}
          {step === 2 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
                <Calendar className="w-4 h-4 text-teal-600" />
                <span>When Were You Born?</span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                Your date of birth is used to compute biological age and screen age-related disease risks.
              </p>

              <div className="pt-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1">Date of Birth</label>
                <input
                  type="date"
                  value={dateOfBirth}
                  onChange={e => setDateOfBirth(e.target.value)}
                  className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                  required
                />
              </div>

              {dateOfBirth && calculateAge(dateOfBirth) !== null && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-xs text-emerald-800">
                  <span className="font-semibold">Calculated Current Age:</span>
                  <span className="font-bold text-sm bg-emerald-100 px-2.5 py-0.5 rounded-lg">
                    {calculateAge(dateOfBirth)} Years Old
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Contact & Location */}
          {step === 3 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
                <MapPin className="w-4 h-4 text-teal-600" />
                <span>Contact Phone & Residential Location</span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                Used to find nearest hospital facilities and coordinate appointment scheduling.
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Contact Phone</label>
                <div className="relative">
                  <Phone className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="tel"
                    value={phone}
                    onChange={e => setPhone(e.target.value)}
                    placeholder="+91 98201 44521"
                    className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">District</label>
                  <input
                    type="text"
                    value={district}
                    onChange={e => setDistrict(e.target.value)}
                    placeholder="e.g. Mumbai"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">State</label>
                  <input
                    type="text"
                    value={stateName}
                    onChange={e => setStateName(e.target.value)}
                    placeholder="e.g. Maharashtra"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Health Baseline */}
          {step === 4 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
                <Heart className="w-4 h-4 text-teal-600" />
                <span>Health Baseline & Lifestyle</span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                Helps in blood transfusions, prescription cross-referencing, and respiratory modeling.
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Blood Group</label>
                <select
                  value={bloodGroup}
                  onChange={e => setBloodGroup(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
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

              <div className="flex items-center gap-2 pt-2">
                <input
                  type="checkbox"
                  id="modalIsSmoker"
                  checked={isSmoker}
                  onChange={e => setIsSmoker(e.target.checked)}
                  className="w-4 h-4 text-teal-600 rounded border-slate-300 focus:ring-teal-500"
                />
                <label htmlFor="modalIsSmoker" className="text-xs text-slate-700 select-none">
                  Past or current tobacco / smoking use
                </label>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1">
                <span className="font-semibold block text-slate-700">Summary:</span>
                <p className="text-slate-600">Gender: <strong className="capitalize">{gender}</strong></p>
                <p className="text-slate-600">DOB: <strong>{dateOfBirth}</strong> ({calculateAge(dateOfBirth)} yrs)</p>
                <p className="text-slate-600">District: <strong>{district}, {stateName}</strong></p>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-between items-center pt-4 border-t border-slate-100">
            {step > 1 ? (
              <button
                type="button"
                onClick={() => setStep(step - 1)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-xl transition"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Previous</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={onClose}
                className="text-xs text-slate-400 hover:text-slate-600 font-medium px-2 py-1"
              >
                Skip for now
              </button>
            )}

            {step < 4 ? (
              <button
                type="button"
                onClick={() => setStep(step + 1)}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-teal-600 hover:bg-teal-700 rounded-xl shadow-sm transition"
              >
                <span>Next Question</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                type="button"
                disabled={saving}
                onClick={handleSave}
                className="inline-flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-sm transition disabled:opacity-50"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{saving ? 'Saving...' : 'Save & Synchronize Record'}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
