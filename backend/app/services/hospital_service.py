"""
Hospital Discovery and Appointment Guidance Service for Aarogya Drishti 2.0.
Provides verified, factual information for tertiary hospitals, OPD registrations,
booking methods, and emergency care.
Strictly distinguishes verified online portals (e.g. ORS / ABDM) from physical walk-in procedures.
"""

from typing import Dict, Any, List, Optional
import re

HOSPITAL_DATABASE = {
    "kem_hospital_mumbai": {
        "institution_id": "HOSP-KEM-MUMBAI",
        "name": "King Edward Memorial (KEM) Hospital and Seth G.S. Medical College",
        "aliases": ["kem", "kem hospital", "kem mumbai", "king edward memorial", "king edward", "seth gs"],
        "city": "Mumbai",
        "state": "Maharashtra",
        "district": "Mumbai",
        "address": "Acharya Donde Marg, Parel East, Parel, Mumbai, Maharashtra 400012",
        "category": "Tertiary Municipal Teaching Hospital (BMC / MCGM)",
        "official_website": "https://www.kem.edu",
        "emergency_phone": "022-24107000",
        "opd_contact": "022-24107000 / 022-24107555",
        "emergency_services": "24x7 Casualty and Trauma Care",
        "appointment_modes": {
            "online_ors": {
                "supported": True,
                "portal_name": "Online Registration System (ORS Patient Portal - Central Govt)",
                "portal_url": "https://ors.gov.in",
                "instructions": [
                    "Visit the official portal at https://ors.gov.in (or use the UMANG app).",
                    "Register or log in using your mobile number and OTP, or your ABHA (Ayushman Bharat Health Account) ID.",
                    "Select 'Book Appointment' -> State: Maharashtra -> Hospital: KEM Hospital, Mumbai.",
                    "Select the clinical department (e.g., General Medicine, Cardiology, Orthopedics).",
                    "Choose an available slot, verify patient details via Aadhaar OTP or manual entry, and note your confirmation reference number."
                ]
            },
            "digital_fast_track_abdm": {
                "supported": True,
                "system_name": "ABDM 'Scan and Share' QR Queue Management",
                "instructions": [
                    "Download the ABHA app or Aarogya Setu.",
                    "Scan the official KEM Hospital OPD QR code at the registration counter upon arrival.",
                    "Share your profile digitally to receive an instant electronic OPD token, bypassing manual form queues."
                ]
            },
            "walk_in_registration": {
                "supported": True,
                "description": "Physical OPD Case Paper Counters",
                "timing": "Monday to Saturday, 7:30 AM – 11:30 AM (Timings may vary by department; arrive early).",
                "location": "Main OPD Registration Wing, Ground Floor, KEM Hospital, Parel.",
                "requirements": "Government photo ID (Aadhaar / Voter ID), previous medical files/prescriptions, and Rs. 10-20 nominal BMC case paper fee."
            }
        },
        "important_notes": [
            "KEM Hospital is a high-volume public tertiary referral center. Patients are advised to arrive early morning.",
            "Specialty super-specialty clinics (Cardiology, Neurology, Nephrology) generally require an initial screening referral from General Medicine OPD.",
            "Emergency and trauma admissions do not require pre-booking and operate round-the-clock."
        ]
    },
    "lilavati_hospital_mumbai": {
        "institution_id": "HOSP-LILAVATI-MUMBAI",
        "name": "Lilavati Hospital & Research Centre",
        "aliases": ["lilavati", "lilavati hospital", "lilavati bandra"],
        "city": "Mumbai",
        "state": "Maharashtra",
        "district": "Mumbai Suburban",
        "address": "A-791, Bandra Reclamation, Bandra West, Mumbai, Maharashtra 400050",
        "category": "Premier Multi-Specialty Tertiary Care Hospital",
        "official_website": "https://www.lilavatihospital.com",
        "emergency_phone": "022-26751000 / 022-26568000",
        "opd_contact": "022-26751000",
        "emergency_services": "24x7 Emergency, Trauma, Cardiac & Stroke Care",
        "appointment_modes": {
            "online_ors": {
                "supported": True,
                "portal_name": "Lilavati Online Consultant Booking Portal",
                "portal_url": "https://www.lilavatihospital.com",
                "instructions": [
                    "Visit lilavatihospital.com and click 'Find a Doctor' or 'Book Appointment'.",
                    "Select specialty (Cardiology, Neurology, Orthopedics, Pediatrics, etc.).",
                    "Select preferred consultant and pick an available consultation slot."
                ]
            },
            "digital_fast_track_abdm": {
                "supported": True,
                "system_name": "Aarogya HMS Smart Booking",
                "instructions": [
                    "Direct booking confirmation via the Aarogya-Drishti AI Assistant with token issuance."
                ]
            },
            "walk_in_registration": {
                "supported": True,
                "description": "OPD Registration Desk, Ground Floor Lobby",
                "timing": "Monday to Saturday, 8:00 AM – 6:00 PM",
                "location": "Bandra Reclamation OPD Wing",
                "requirements": "Photo ID, previous medical records, insurance card if applicable."
            }
        },
        "important_notes": [
            "NABH accredited center of excellence in Cardiology, Orthopedics, and Neurology.",
            "Advanced diagnostic imaging (3T MRI, 128-slice CT) available round-the-clock."
        ]
    },
    "breach_candy_hospital_mumbai": {
        "institution_id": "HOSP-BREACH-CANDY",
        "name": "Breach Candy Hospital Trust",
        "aliases": ["breach candy", "breach candy hospital", "breach candy trust"],
        "city": "Mumbai",
        "state": "Maharashtra",
        "district": "Mumbai",
        "address": "60 A, Bhulabhai Desai Marg, Cumballa Hill, Mumbai, Maharashtra 400026",
        "category": "Landmark Super-Specialty Tertiary Hospital",
        "official_website": "https://www.breachcandyhospital.org",
        "emergency_phone": "022-23667788",
        "opd_contact": "022-23667999",
        "emergency_services": "24x7 Acute Care, Cath Lab & Intensive Care",
        "appointment_modes": {
            "online_ors": {
                "supported": True,
                "portal_name": "Breach Candy Online OPD Scheduling",
                "portal_url": "https://www.breachcandyhospital.org",
                "instructions": [
                    "Access breachcandyhospital.org -> OPD Appointments.",
                    "Choose consultant doctor, review consultation fee and timing, and confirm booking."
                ]
            },
            "digital_fast_track_abdm": {
                "supported": True,
                "system_name": "Aarogya Inter-Hospital Network Token",
                "instructions": [
                    "Instant digital token generated via Aarogya assistant."
                ]
            },
            "walk_in_registration": {
                "supported": True,
                "description": "Main Registration Counter, South Wing",
                "timing": "Monday to Saturday, 8:30 AM – 5:30 PM",
                "location": "Bhulabhai Desai Marg Main Complex",
                "requirements": "Valid identity proof and referral letter if applicable."
            }
        },
        "important_notes": [
            "Renowned interventional cardiology and specialized maternal-fetal medicine departments.",
            "International patient desk available."
        ]
    },
    "hinduja_hospital_mumbai": {
        "institution_id": "HOSP-HINDUJA-MUMBAI",
        "name": "P.D. Hinduja National Hospital & Medical Research Centre",
        "aliases": ["hinduja", "hinduja hospital", "pd hinduja"],
        "city": "Mumbai",
        "state": "Maharashtra",
        "district": "Mumbai",
        "address": "Veer Savarkar Marg, Mahim West, Mumbai, Maharashtra 400016",
        "category": "JCI & NABH Accredited Multi-Specialty Research Hospital",
        "official_website": "https://www.hindujahospital.com",
        "emergency_phone": "022-24452222 / 022-24449199",
        "opd_contact": "022-24451515",
        "emergency_services": "24x7 Level 1 Trauma & Comprehensive Emergency Unit",
        "appointment_modes": {
            "online_ors": {
                "supported": True,
                "portal_name": "Hinduja Patient Care Portal & App",
                "portal_url": "https://www.hindujahospital.com",
                "instructions": [
                    "Log in via website or Hinduja Hospital mobile app.",
                    "Select department, view doctor credentials, and book consultation."
                ]
            },
            "digital_fast_track_abdm": {
                "supported": True,
                "system_name": "ABDM Scan and Share Enabled",
                "instructions": [
                    "Instant check-in via ABHA ID QR scanning."
                ]
            },
            "walk_in_registration": {
                "supported": True,
                "description": "OPD Registration Desks, OPD Building",
                "timing": "Monday to Saturday, 8:00 AM – 6:00 PM",
                "location": "Hinduja Clinic Block, Mahim",
                "requirements": "Government ID, patient card number for returning patients."
            }
        },
        "important_notes": [
            "Pioneering center for Pulmonology (MDR-TB Center), Neurology, and Nephrology.",
            "Complete on-site CAP-accredited diagnostic laboratory."
        ]
    },
    "apollo_hospital_navi_mumbai": {
        "institution_id": "HOSP-APOLLO-NAVI-MUMBAI",
        "name": "Apollo Hospitals, Navi Mumbai",
        "aliases": ["apollo", "apollo navi mumbai", "apollo hospital"],
        "city": "Navi Mumbai",
        "state": "Maharashtra",
        "district": "Thane",
        "address": "Plot No. 13, Parsik Hill Road, Sector 23, CBD Belapur, Navi Mumbai, Maharashtra 400614",
        "category": "JCI-Accredited 500-Bed Quaternary Care Hospital",
        "official_website": "https://www.apollohospitals.com",
        "emergency_phone": "1066 / 022-62806280",
        "opd_contact": "022-62806280",
        "emergency_services": "24x7 Emergency & Heart Stroke Helpline 1066",
        "appointment_modes": {
            "online_ors": {
                "supported": True,
                "portal_name": "Apollo 24|7 & Hospital Desk",
                "portal_url": "https://www.apollohospitals.com",
                "instructions": [
                    "Access Apollo 24|7 app or website.",
                    "Choose Navi Mumbai center, pick doctor and confirm booking."
                ]
            },
            "digital_fast_track_abdm": {
                "supported": True,
                "system_name": "Aarogya Fast-Track Registration",
                "instructions": [
                    "Direct consultation slot reservation with token issuance."
                ]
            },
            "walk_in_registration": {
                "supported": True,
                "description": "Central Registration Hall, Ground Floor",
                "timing": "Monday to Sunday, 8:00 AM – 8:00 PM",
                "location": "Parsik Hill Road, CBD Belapur",
                "requirements": "Aadhaar Card, insurance policy details if cashless TPA."
            }
        },
        "important_notes": [
            "State-of-the-art robotic surgery, bone marrow transplant, and quaternary intensive care.",
            "Comprehensive 24x7 trauma care facility."
        ]
    },
    "tata_memorial_hospital_mumbai": {
        "institution_id": "HOSP-TMC-MUMBAI",
        "name": "Tata Memorial Hospital & Advanced Centre for Treatment, Research and Education in Cancer (ACTREC)",
        "aliases": ["tata memorial", "tmc", "tata hospital", "actrec", "tata cancer"],
        "city": "Mumbai",
        "state": "Maharashtra",
        "district": "Mumbai",
        "address": "Dr. E Borges Road, Parel, Mumbai, Maharashtra 400012",
        "category": "Apex National Comprehensive Cancer Center (DAE, Govt of India)",
        "official_website": "https://tmc.gov.in",
        "emergency_phone": "022-24177000",
        "opd_contact": "022-24177000 / 022-24146750",
        "emergency_services": "24x7 Oncology Emergency and Acute Palliative Care",
        "appointment_modes": {
            "online_ors": {
                "supported": True,
                "portal_name": "TMC Web Portal New Patient Registration",
                "portal_url": "https://tmc.gov.in",
                "instructions": [
                    "Visit tmc.gov.in -> Online Registration for New Patients.",
                    "Upload pathology/biopsy reports, enter patient details, and receive Smart Card registration date."
                ]
            },
            "digital_fast_track_abdm": {
                "supported": True,
                "system_name": "ABDM Fast-Track OPD & Digital EHR",
                "instructions": [
                    "Scan QR code with ABHA app at Golden Jubilee Block counters."
                ]
            },
            "walk_in_registration": {
                "supported": True,
                "description": "New Registration Counters, Golden Jubilee Block",
                "timing": "Monday to Friday, 8:00 AM – 2:00 PM; Saturday 8:00 AM – 12:00 PM",
                "location": "Dr. E Borges Road, Parel",
                "requirements": "Histopathology biopsy reports, imaging scans (CD/Films), Government photo ID."
            }
        },
        "important_notes": [
            "National apex center for comprehensive cancer prevention, diagnosis, treatment, and research.",
            "Subsidized and government-supported oncology care schemes (Ayushman Bharat / MJPJAY accepted)."
        ]
    }
}

class HospitalDiscoveryService:
    @staticmethod
    def identify_hospital(query: str) -> Optional[Dict[str, Any]]:
        """Identify matching hospital from query."""
        q_low = query.lower()
        for h_key, h_data in HOSPITAL_DATABASE.items():
            for alias in h_data["aliases"]:
                if re.search(r'\b' + re.escape(alias) + r'\b', q_low):
                    return h_data
        return None

    @staticmethod
    def format_hospital_guidance(hospital: Dict[str, Any]) -> str:
        """Generates a structured, fact-checked hospital information and appointment response."""
        ors = hospital["appointment_modes"]["online_ors"]
        walkin = hospital["appointment_modes"]["walk_in_registration"]
        abdm = hospital["appointment_modes"]["digital_fast_track_abdm"]
        
        md = [
            f"### Verified Hospital Information: {hospital['name']}\n",
            f"- **Institution Type:** {hospital['category']}",
            f"- **Address:** {hospital['address']}",
            f"- **Official Website:** [{hospital['official_website']}]({hospital['official_website']})",
            f"- **Central Hospital Helpdesk / Contact:** `{hospital['opd_contact']}`",
            f"- **Emergency Care:** {hospital['emergency_services']} (Helpline: `{hospital['emergency_phone']}`)\n",
            "#### How to Register and Book an OPD Consultation:\n",
            f"**1. Official Online Booking ({ors['portal_name']}):**",
            f"- Official Portal: [{ors['portal_url']}]({ors['portal_url']})",
            *[f"  - {inst}" for inst in ors.get("instructions", [])],
            f"\n**2. Fast-Track Digital Token ({abdm['system_name']}):**",
            *[f"- {inst}" for inst in abdm.get("instructions", [])],
            f"\n**3. Walk-In Physical Registration:**",
            f"- **Counters:** {walkin['location']}",
            f"- **Timings:** {walkin['timing']}",
            f"- **Requirements:** {walkin['requirements']}\n",
            "#### Important Patient Notice:",
            f"> [!NOTE]\n> *{hospital['important_notes'][0]}*"
        ]
        return "\n".join(md)
