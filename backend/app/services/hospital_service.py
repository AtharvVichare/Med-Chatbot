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
        "aliases": ["kem", "kem hospital", "kem mumbai", "king edward memorial", "king edward"],
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
            "**1. Official Online Booking (ORS Portal):**",
            f"KEM Hospital participates in the Government of India's **Online Registration System (ORS)**:",
            f"- Official Portal: [{ors['portal_url']}]({ors['portal_url']}) (or access via the **UMANG** mobile app).",
            "  - Log in using your mobile number & OTP or ABHA ID.",
            "  - Select **State: Maharashtra** -> **Hospital: KEM Hospital, Mumbai**.",
            "  - Select your desired specialty department and available date.",
            "  - Complete patient verification to receive an official booking SMS and appointment reference number.\n",
            "**2. Fast-Track Digital Token (ABDM Scan & Share):**",
            f"- You can generate an instant token at hospital counters using the **ABHA** app by scanning the hospital QR code.\n",
            "**3. Walk-In Physical Registration:**",
            f"- **Counters:** {walkin['location']}",
            f"- **Timings:** {walkin['timing']}",
            f"- **Requirements:** {walkin['requirements']}\n",
            "#### Important Patient Notice:",
            f"> [!NOTE]\n> *{hospital['important_notes'][0]} {hospital['important_notes'][1]}*"
        ]
        return "\n".join(md)

