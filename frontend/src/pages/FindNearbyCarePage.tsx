import React, { useState } from 'react';
import { 
  MapPin, 
  Phone, 
  Clock, 
  ShieldAlert, 
  Navigation, 
  Search,
  ExternalLink
} from 'lucide-react';

export const FindNearbyCarePage: React.FC = () => {
  const [searchDistrict, setSearchDistrict] = useState('Mumbai');

  const demoHospitals = [
    {
      name: 'KEM Hospital & Seth GS Medical College',
      type: 'Government Tertiary Hospital & Trauma Center',
      distance: '2.4 km',
      address: 'Acharya Donde Marg, Parel, Mumbai, Maharashtra 400012',
      phone: '+91 22 2410 7000',
      emergency: '24/7 Emergency & ICU Available',
      timings: 'OPD: 8:00 AM - 1:00 PM',
      rating: '4.4 / 5'
    },
    {
      name: 'Lilavati Hospital and Research Centre',
      type: 'Multi-Specialty Research Hospital',
      distance: '4.8 km',
      address: 'A-791, Bandra Reclamation, Bandra West, Mumbai, Maharashtra 400050',
      phone: '+91 22 2675 1000',
      emergency: '24/7 Emergency & Cardiac Care',
      timings: 'OPD: 9:00 AM - 6:00 PM',
      rating: '4.6 / 5'
    },
    {
      name: 'Bandra Bhabha Municipal General Hospital',
      type: 'Municipal Secondary Care Center',
      distance: '5.1 km',
      address: 'Waterfield Road, Bandra West, Mumbai, Maharashtra 400050',
      phone: '+91 22 2642 2775',
      emergency: 'Emergency Services Available',
      timings: 'OPD: 8:30 AM - 12:30 PM',
      rating: '4.1 / 5'
    },
    {
      name: 'Dadar Community Urban Health Center',
      type: 'Primary Health Center (Ayushman Bharat HWC)',
      distance: '1.8 km',
      address: 'Dr. Babasaheb Ambedkar Road, Dadar East, Mumbai, Maharashtra 400014',
      phone: '+91 22 2414 1122',
      emergency: 'Non-emergency Primary Care',
      timings: 'Mon-Sat: 9:00 AM - 5:00 PM',
      rating: '4.2 / 5'
    }
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold mb-2">
            <MapPin className="w-3.5 h-3.5 text-teal-600" />
            <span>Prototype Healthcare Discovery Service</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Find Nearby Healthcare Services</h1>
          <p className="text-xs text-slate-500 mt-1">
            Locate accredited hospitals, Ayushman Bharat health centers, and emergency trauma facilities
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              value={searchDistrict}
              onChange={e => setSearchDistrict(e.target.value)}
              placeholder="Filter by district / pin..."
              className="pl-8 pr-3 py-2 bg-white border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500"
            />
          </div>
        </div>
      </div>

      {/* Prototype Notice Banner */}
      <div className="p-4 rounded-xl bg-slate-100 border border-slate-200 text-xs text-slate-700 flex items-start gap-3">
        <ShieldAlert className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        <div className="leading-relaxed">
          <span className="font-bold">Demonstration Care Locator:</span> Real-time hospital bed availability and direct ABDM (Ayushman Bharat Digital Mission) appointment booking will be activated in Phase 5 upon healthcare registry API federations. In case of acute medical emergencies, immediately dial <span className="font-bold text-slate-900">112</span> or <span className="font-bold text-slate-900">108</span> for emergency ambulance dispatch.
        </div>
      </div>

      {/* Hospital Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {demoHospitals.map((hosp, i) => (
          <div key={i} className="p-5 bg-white rounded-xl border border-slate-200/80 shadow-sm space-y-3 hover:border-teal-300 transition">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] uppercase font-bold text-teal-700 bg-teal-50 px-2 py-0.5 rounded">
                  {hosp.type}
                </span>
                <h3 className="text-sm font-bold text-slate-900 mt-1.5">{hosp.name}</h3>
              </div>
              <span className="inline-flex items-center gap-1 text-xs font-bold text-slate-700 bg-slate-100 px-2.5 py-1 rounded-lg shrink-0">
                <Navigation className="w-3 h-3 text-teal-600" />
                <span>{hosp.distance}</span>
              </span>
            </div>

            <p className="text-xs text-slate-600 flex items-start gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
              <span>{hosp.address}</span>
            </p>

            <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-slate-100">
              <div className="flex items-center gap-1.5 text-slate-600">
                <Phone className="w-3.5 h-3.5 text-teal-600" />
                <span className="font-mono text-[11px]">{hosp.phone}</span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-600">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>{hosp.timings}</span>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg">
                {hosp.emergency}
              </span>
              <button
                onClick={() => alert(`Directions for ${hosp.name} will open in your navigation application.`)}
                className="text-xs font-semibold text-teal-600 hover:text-teal-700 flex items-center gap-1"
              >
                <span>Get Directions</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
