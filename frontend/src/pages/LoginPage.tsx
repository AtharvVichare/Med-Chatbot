import React, { useState, useEffect } from 'react';
import { 
  Eye, 
  EyeOff, 
  Lock, 
  User, 
  Mail, 
  Phone, 
  AlertCircle, 
  ArrowRight, 
  ArrowLeft, 
  CheckCircle2, 
  Calendar, 
  MapPin, 
  Heart, 
  ShieldCheck, 
  Sparkles,
  Check
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

declare global {
  interface Window {
    google?: any;
  }
}

export const LoginPage: React.FC = () => {
  const { login, googleLogin, signup } = useAuth();
  const [mode, setMode] = useState<'signin' | 'signup' | 'forgot'>('signin');

  // Sign In State
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  // Sign Up State
  const [signupStep, setSignupStep] = useState<number>(1);
  const [signupUsername, setSignupUsername] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupFirstName, setSignupFirstName] = useState('');
  const [signupLastName, setSignupLastName] = useState('');
  const [signupGender, setSignupGender] = useState('female');
  const [signupDob, setSignupDob] = useState('1995-05-15');
  const [signupPhone, setSignupPhone] = useState('');
  const [signupDistrict, setSignupDistrict] = useState('Mumbai');
  const [signupState, setSignupState] = useState('Maharashtra');
  const [signupBloodGroup, setSignupBloodGroup] = useState('O+');
  const [signupIsSmoker, setSignupIsSmoker] = useState(false);

  // Forgot Password State
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSuccess, setForgotSuccess] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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

  const handleSignupStepNext = () => {
    setErrorMessage(null);
    if (signupStep === 1) {
      if (!signupFirstName.trim() || !signupLastName.trim()) {
        setErrorMessage('Please enter both your first and last legal name.');
        return;
      }
      if (!signupUsername.trim()) {
        setErrorMessage('Please choose a username for your account.');
        return;
      }
      if (!signupEmail.trim() || !signupEmail.includes('@')) {
        setErrorMessage('Please enter a valid email address.');
        return;
      }
      if (!signupPassword || signupPassword.length < 6) {
        setErrorMessage('Password must be at least 6 characters long.');
        return;
      }
      setSignupStep(2);
    } else if (signupStep === 2) {
      if (!signupGender || signupGender === 'unspecified') {
        setErrorMessage('Please select your gender / biological sex.');
        return;
      }
      if (!signupDob) {
        setErrorMessage('Please specify your date of birth.');
        return;
      }
      setSignupStep(3);
    } else if (signupStep === 3) {
      if (!signupDistrict.trim()) {
        setErrorMessage('Please specify your residential district.');
        return;
      }
      setSignupStep(4);
    } else if (signupStep === 4) {
      setSignupStep(5);
    }
  };

  // Initialize Google Identity Services
  useEffect(() => {
    const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

    const handleGoogleCredentialResponse = async (response: any) => {
      if (!response.credential) return;
      setIsLoading(true);
      setErrorMessage(null);
      try {
        await googleLogin(response.credential);
      } catch (err: any) {
        setErrorMessage(err.message || 'Google sign-in failed. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    if (window.google?.accounts?.id && googleClientId) {
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: handleGoogleCredentialResponse,
      });

      const btnElement = document.getElementById('googleSignInBtn');
      if (btnElement) {
        window.google.accounts.id.renderButton(btnElement, {
          theme: 'outline',
          size: 'large',
          width: '100%',
          text: 'continue_with',
          shape: 'pill'
        });
      }
    }
  }, [mode, googleLogin]);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMessage('Please enter both username and password.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      await login(username.trim(), password);
    } catch (err: any) {
      setErrorMessage(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!signupUsername || !signupEmail || !signupPassword || !signupFirstName || !signupLastName) {
      setErrorMessage('Please fill in all required account fields.');
      setSignupStep(1);
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      await signup({
        username: signupUsername.trim(),
        email: signupEmail.trim(),
        password: signupPassword,
        first_name: signupFirstName.trim(),
        last_name: signupLastName.trim(),
        gender: signupGender,
        date_of_birth: signupDob,
        phone: signupPhone.trim() || undefined,
        district: signupDistrict.trim() || 'Mumbai',
        state: signupState.trim() || 'Maharashtra',
        is_smoker: signupIsSmoker,
        blood_group: signupBloodGroup
      });
    } catch (err: any) {
      setErrorMessage(err.message || 'Account creation failed. Username or email may already exist.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!forgotEmail) {
      setErrorMessage('Please enter your email address.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await api.forgotPassword(forgotEmail.trim());
      setForgotSuccess(res.message || 'Password reset instructions have been generated.');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to request password reset.');
    } finally {
      setIsLoading(false);
    }
  };

  const setDemoAccount = (u: string, p: string) => {
    setMode('signin');
    setUsername(u);
    setPassword(p);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4 py-8">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl border border-slate-100 p-8">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-teal-600 text-white shadow-lg shadow-teal-600/30 mb-3">
            <span className="font-bold text-3xl">आ</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Aarogya Drishti 2.0</h1>
          <p className="text-sm text-slate-500 mt-1">One patient · One health record · One AI companion</p>
        </div>

        {/* Mode Selector Tabs */}
        <div className="flex border-b border-slate-200 mb-6">
          <button
            type="button"
            onClick={() => { setMode('signin'); setErrorMessage(null); }}
            className={`flex-1 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
              mode === 'signin'
                ? 'border-teal-600 text-teal-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setMode('signup'); setErrorMessage(null); }}
            className={`flex-1 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
              mode === 'signup'
                ? 'border-teal-600 text-teal-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            Create Patient Account
          </button>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div className="mb-5 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-600 mt-0.5 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Forgot Success */}
        {forgotSuccess && (
          <div className="mb-5 p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
            <span>{forgotSuccess}</span>
          </div>
        )}

        {/* Sign In Mode */}
        {mode === 'signin' && (
          <form onSubmit={handleLoginSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <User className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. aarav_mehta or doctor_user"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-colors"
                  required
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => { setMode('forgot'); setErrorMessage(null); setForgotSuccess(null); }}
                  className="text-xs text-teal-600 hover:text-teal-700 font-medium"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  className="w-full pl-10 pr-10 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500 transition-colors"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-3 px-4 bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold rounded-xl shadow-md shadow-teal-600/20 flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
            >
              {isLoading ? (
                <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              ) : (
                <>
                  <span>Sign In to Health Portal</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            {/* Google Sign In Divider & Container */}
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-200"></div>
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-slate-400 font-medium">Or continue with</span>
              </div>
            </div>

            <div id="googleSignInBtn" className="flex justify-center w-full min-h-[44px]"></div>
          </form>
        )}

        {/* Sign Up Mode - One-by-One Progressive Questionnaire */}
        {mode === 'signup' && (
          <div className="space-y-4">
            {/* Stepper Header */}
            <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700 mb-2">
                <span>Step {signupStep} of 5: {
                  signupStep === 1 ? 'Account Credentials' :
                  signupStep === 2 ? 'Biological Demographics' :
                  signupStep === 3 ? 'Location & Phone' :
                  signupStep === 4 ? 'Clinical Baseline' : 'Review & Confirm'
                }</span>
                <span className="text-[11px] text-teal-700 font-bold bg-teal-100 px-2 py-0.5 rounded-full">
                  {Math.round((signupStep / 5) * 100)}% Complete
                </span>
              </div>
              <div className="flex gap-1.5">
                {[1, 2, 3, 4, 5].map((s) => (
                  <div
                    key={s}
                    className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${
                      s <= signupStep ? 'bg-teal-600' : 'bg-slate-200'
                    }`}
                  />
                ))}
              </div>
            </div>

            {/* Step 1: Account Credentials */}
            {signupStep === 1 && (
              <div className="space-y-3 animate-in fade-in">
                <div className="text-xs text-slate-500 mb-1">
                  Step 1: Enter your legal name and set up your login credentials.
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">First Name *</label>
                    <input
                      type="text"
                      value={signupFirstName}
                      onChange={(e) => setSignupFirstName(e.target.value)}
                      placeholder="Pooja"
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Last Name *</label>
                    <input
                      type="text"
                      value={signupLastName}
                      onChange={(e) => setSignupLastName(e.target.value)}
                      placeholder="Sharma"
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Desired Username *</label>
                  <div className="relative">
                    <User className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="text"
                      value={signupUsername}
                      onChange={(e) => setSignupUsername(e.target.value)}
                      placeholder="pooja_sharma"
                      className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address *</label>
                  <div className="relative">
                    <Mail className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="email"
                      value={signupEmail}
                      onChange={(e) => setSignupEmail(e.target.value)}
                      placeholder="pooja@example.com"
                      className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Password *</label>
                  <div className="relative">
                    <Lock className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="password"
                      value={signupPassword}
                      onChange={(e) => setSignupPassword(e.target.value)}
                      placeholder="Minimum 6 characters"
                      className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                      required
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Biological & Gender Details */}
            {signupStep === 2 && (
              <div className="space-y-3.5 animate-in fade-in">
                <div className="flex items-center gap-1.5 text-xs text-slate-600">
                  <User className="w-4 h-4 text-teal-600" />
                  <span>Step 2: Biological Sex & Date of Birth</span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Gender / Biological Sex *
                  </label>
                  <p className="text-[11px] text-slate-500 mb-2 leading-relaxed">
                    Required to establish standard clinical lab reference ranges, hemoglobin limits, and disease risk baselines.
                  </p>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { id: 'female', label: 'Female', sub: 'Standard female ranges' },
                      { id: 'male', label: 'Male', sub: 'Standard male ranges' },
                      { id: 'other', label: 'Other', sub: 'Neutral ranges' }
                    ].map(opt => (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => setSignupGender(opt.id)}
                        className={`p-3 text-center rounded-xl border-2 transition-all ${
                          signupGender === opt.id
                            ? 'border-teal-600 bg-teal-50 text-teal-900 shadow-sm'
                            : 'border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700'
                        }`}
                      >
                        <span className="block font-bold text-xs capitalize">{opt.label}</span>
                        <span className="text-[9px] text-slate-500 mt-0.5 block">{opt.sub}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="pt-2">
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-xs font-semibold text-slate-700">Date of Birth *</label>
                    {signupDob && calculateAge(signupDob) !== null && (
                      <span className="text-[11px] font-bold text-teal-700 bg-teal-100 px-2 py-0.5 rounded-full">
                        Age: {calculateAge(signupDob)} yrs
                      </span>
                    )}
                  </div>
                  <div className="relative">
                    <Calendar className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="date"
                      value={signupDob}
                      onChange={(e) => setSignupDob(e.target.value)}
                      className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                      required
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Location & Phone */}
            {signupStep === 3 && (
              <div className="space-y-3.5 animate-in fade-in">
                <div className="flex items-center gap-1.5 text-xs text-slate-600">
                  <MapPin className="w-4 h-4 text-teal-600" />
                  <span>Step 3: Contact Phone & Regional Location</span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Primary Mobile Phone</label>
                  <div className="relative">
                    <Phone className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                    <input
                      type="tel"
                      value={signupPhone}
                      onChange={(e) => setSignupPhone(e.target.value)}
                      placeholder="+91 98765 43210"
                      className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                    />
                  </div>
                  <span className="text-[10px] text-slate-400 mt-1 block">Used for appointment reminder tickets and verification.</span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Residential District *</label>
                    <input
                      type="text"
                      value={signupDistrict}
                      onChange={(e) => setSignupDistrict(e.target.value)}
                      placeholder="e.g. Mumbai"
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">State</label>
                    <input
                      type="text"
                      value={signupState}
                      onChange={(e) => setSignupState(e.target.value)}
                      placeholder="Maharashtra"
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Step 4: Clinical Health Baseline */}
            {signupStep === 4 && (
              <div className="space-y-3.5 animate-in fade-in">
                <div className="flex items-center gap-1.5 text-xs text-slate-600">
                  <Heart className="w-4 h-4 text-teal-600" />
                  <span>Step 4: Clinical Baseline & Lifestyle</span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Blood Group</label>
                  <select
                    value={signupBloodGroup}
                    onChange={(e) => setSignupBloodGroup(e.target.value)}
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

                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="signupSmokerCheck"
                      checked={signupIsSmoker}
                      onChange={(e) => setSignupIsSmoker(e.target.checked)}
                      className="w-4 h-4 text-teal-600 rounded border-slate-300 focus:ring-teal-500"
                    />
                    <label htmlFor="signupSmokerCheck" className="text-xs font-semibold text-slate-700 select-none">
                      Current or past tobacco / smoking use
                    </label>
                  </div>
                  <p className="text-[10px] text-slate-400 mt-1 pl-6">Used to calibrate respiratory and cardiovascular risk calculations.</p>
                </div>
              </div>
            )}

            {/* Step 5: Review & Confirmation */}
            {signupStep === 5 && (
              <div className="space-y-3 animate-in fade-in">
                <div className="flex items-center gap-1.5 text-xs font-bold text-teal-800 bg-teal-50 p-2.5 rounded-xl border border-teal-200">
                  <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0" />
                  <span>Step 5: Review & Confirm Lifetime Health Account</span>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 space-y-2 text-xs">
                  <div className="flex justify-between border-b border-slate-200/60 pb-1.5">
                    <span className="text-slate-500">Legal Name:</span>
                    <span className="font-semibold text-slate-900">{signupFirstName} {signupLastName}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-200/60 pb-1.5">
                    <span className="text-slate-500">Username / Email:</span>
                    <span className="font-semibold text-slate-900">@{signupUsername} · {signupEmail}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-200/60 pb-1.5">
                    <span className="text-slate-500">Gender / DOB:</span>
                    <span className="font-semibold text-slate-900 capitalize">{signupGender} · {signupDob} ({calculateAge(signupDob)} yrs)</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-200/60 pb-1.5">
                    <span className="text-slate-500">Location:</span>
                    <span className="font-semibold text-slate-900">{signupDistrict}, {signupState}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Blood / Lifestyle:</span>
                    <span className="font-semibold text-slate-900">Blood {signupBloodGroup} · {signupIsSmoker ? 'Smoker' : 'Non-smoker'}</span>
                  </div>
                </div>

                <p className="text-[11px] text-slate-500 leading-relaxed">
                  By creating this account, a secure longitudinal EHR will be instantiated with an automated ABHA digital health identifier. You can edit any details in Settings at any time.
                </p>
              </div>
            )}

            {/* Step Action Buttons */}
            <div className="flex gap-2 pt-2">
              {signupStep > 1 && (
                <button
                  type="button"
                  onClick={() => { setSignupStep(signupStep - 1); setErrorMessage(null); }}
                  className="py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-xl flex items-center gap-1.5 transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </button>
              )}

              {signupStep < 5 ? (
                <button
                  type="button"
                  onClick={handleSignupStepNext}
                  className="flex-1 py-2.5 px-4 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-xl shadow-md shadow-teal-600/20 flex items-center justify-center gap-1.5 transition-colors"
                >
                  <span>Next Question</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              ) : (
                <button
                  type="button"
                  disabled={isLoading}
                  onClick={handleSignupSubmit}
                  className="flex-1 py-3 px-4 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl shadow-md shadow-emerald-600/20 flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                >
                  {isLoading ? (
                    <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  ) : (
                    <>
                      <span>Create Lifetime Health Record</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Forgot Password Mode */}
        {mode === 'forgot' && (
          <form onSubmit={handleForgotSubmit} className="space-y-4">
            <p className="text-sm text-slate-600">
              Enter the email associated with your account, and we will generate instructions to securely reset your credentials.
            </p>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Registered Email
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
                <input
                  type="email"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
                  required
                />
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => { setMode('signin'); setErrorMessage(null); }}
                className="flex-1 py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold rounded-xl transition-colors"
              >
                Back to Sign In
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 py-2.5 px-4 bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold rounded-xl shadow-md shadow-teal-600/20 transition-colors disabled:opacity-50"
              >
                {isLoading ? 'Sending...' : 'Send Reset Link'}
              </button>
            </div>
          </form>
        )}

        {/* Demo Credentials Selector */}
        <div className="mt-8 pt-5 border-t border-slate-100">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 text-center">
            Demo Family Accounts (Synthetic Showcase)
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs mb-3">
            <button
              type="button"
              onClick={() => setDemoAccount('aarav_mehta', 'DemoPassword123!')}
              className="p-2 text-left rounded-lg border border-teal-300 bg-teal-50 hover:bg-teal-100 text-slate-800 transition-colors shadow-2xs"
            >
              <span className="font-bold block text-teal-900">Aarav Mehta</span>
              <span className="text-[10px] text-teal-700 font-medium">Primary Patient (PAT-AARAV-001)</span>
            </button>
            <button
              type="button"
              onClick={() => setDemoAccount('priya_mehta', 'DemoPassword123!')}
              className="p-2 text-left rounded-lg border border-rose-200 bg-rose-50/70 hover:bg-rose-100 text-slate-800 transition-colors"
            >
              <span className="font-bold block text-rose-900">Priya Mehta</span>
              <span className="text-[10px] text-rose-700 font-medium">Spouse (PAT-PRIYA-002)</span>
            </button>
            <button
              type="button"
              onClick={() => setDemoAccount('rohan_mehta', 'DemoPassword123!')}
              className="p-2 text-left rounded-lg border border-amber-200 bg-amber-50/70 hover:bg-amber-100 text-slate-800 transition-colors"
            >
              <span className="font-bold block text-amber-900">Rohan Mehta</span>
              <span className="text-[10px] text-amber-700 font-medium">Brother (PAT-ROHAN-003)</span>
            </button>
            <button
              type="button"
              onClick={() => setDemoAccount('sunita_mehta', 'DemoPassword123!')}
              className="p-2 text-left rounded-lg border border-indigo-200 bg-indigo-50/70 hover:bg-indigo-100 text-slate-800 transition-colors"
            >
              <span className="font-bold block text-indigo-900">Sunita Mehta</span>
              <span className="text-[10px] text-indigo-700 font-medium">Mother (PAT-SUNITA-004)</span>
            </button>
          </div>

          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 text-center">
            Hospital Clinical & Admin Staff
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              onClick={() => setDemoAccount('doctor_user', 'DemoPassword123!')}
              className="p-2 text-left rounded-lg border border-blue-200 bg-blue-50/70 hover:bg-blue-100 text-slate-800 transition-colors"
            >
              <span className="font-bold block text-blue-900">Dr. Deshmukh</span>
              <span className="text-[10px] text-blue-700">Role: Doctor (Cardiology)</span>
            </button>
            <button
              type="button"
              onClick={() => setDemoAccount('nurse_user', 'DemoPassword123!')}
              className="p-2 text-left rounded-lg border border-emerald-200 bg-emerald-50/70 hover:bg-emerald-100 text-slate-800 transition-colors"
            >
              <span className="font-bold block text-emerald-900">Nurse Sharma</span>
              <span className="text-[10px] text-emerald-700">Role: Nurse (Head Nurse)</span>
            </button>
            <button
              type="button"
              onClick={() => setDemoAccount('admin_user', 'DemoPassword123!')}
              className="p-2 text-left rounded-lg border border-purple-200 bg-purple-50/70 hover:bg-purple-100 text-slate-800 transition-colors"
            >
              <span className="font-bold block text-purple-900">Hospital Admin</span>
              <span className="text-[10px] text-purple-700">Role: Admin & Bed Board</span>
            </button>
            <button
              type="button"
              onClick={() => setDemoAccount('analyst_user', 'DemoPassword123!')}
              className="p-2 text-left rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-800 transition-colors"
            >
              <span className="font-bold block text-slate-900">Epidemiologist</span>
              <span className="text-[10px] text-slate-600">Role: Public Health Analyst</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
