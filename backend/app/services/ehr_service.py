"""
Unified Authenticated Longitudinal EHR Retrieval Service for Aarogya Drishti 2.0.
Fetches, organizes, and structures authorized patient records into a complete,
chronological lifetime longitudinal health record.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.app.db.models import (
    Patient,
    Encounter,
    Condition,
    Observation,
    Medication,
    RiskAssessment,
    Allergy,
    FamilyMember,
    FamilyCondition,
    DailyHealthLog,
    PatientDocument
)

class LongitudinalEHRService:
    @staticmethod
    def get_complete_patient_record(patient_id: str, db: Session) -> Dict[str, Any]:
        """
        Retrieves the complete verified longitudinal record for an authenticated patient.
        Organizes encounters, conditions, medications, vitals, labs, daily logs, family history,
        and uploaded clinical documents into an interactive health summary.
        """
        # 1. Patient Demographics
        patient = db.scalar(select(Patient).where(Patient.patient_id == patient_id))
        if not patient:
            return {"error": "Patient record not found", "patient_id": patient_id}

        gender = getattr(patient, "sex", None) or getattr(patient, "gender", "Unknown")
        dob = getattr(patient, "birth_date", None) or getattr(patient, "date_of_birth", "Unknown")
        blood_grp = getattr(patient, "blood_group", None)

        # 2. Conditions
        conditions = db.scalars(
            select(Condition).where(Condition.patient_id == patient_id).order_by(Condition.onset_date.desc().nullslast())
        ).all()

        # 3. Medications (using start_date)
        medications = db.scalars(
            select(Medication).where(Medication.patient_id == patient_id).order_by(Medication.start_date.desc().nullslast())
        ).all()

        # 4. Lab Observations
        observations = db.scalars(
            select(Observation).where(Observation.patient_id == patient_id).order_by(Observation.date.desc())
        ).all()

        # 5. Encounters
        encounters = db.scalars(
            select(Encounter).where(Encounter.patient_id == patient_id).order_by(Encounter.encounter_date.desc())
        ).all()

        # 6. Allergies
        allergies = db.scalars(
            select(Allergy).where(Allergy.patient_id == patient_id).order_by(Allergy.created_at.desc())
        ).all()

        # 7. Family Members & Conditions
        family_members = db.scalars(
            select(FamilyMember).where(FamilyMember.patient_id == patient_id)
        ).all()
        family_history = []
        for fm in family_members:
            conds = db.scalars(select(FamilyCondition).where(FamilyCondition.family_member_id == fm.id)).all()
            family_history.append({
                "relationship": getattr(fm, "relation_type", None) or getattr(fm, "relationship", "relative"),
                "name": getattr(fm, "relative_name", None) or getattr(fm, "first_name", "Relative"),
                "conditions": [c.condition_name for c in conds]
            })

        # 8. Daily Health Tracking Logs
        daily_logs = db.scalars(
            select(DailyHealthLog).where(DailyHealthLog.patient_id == patient_id).order_by(DailyHealthLog.log_date.desc()).limit(15)
        ).all()

        # 9. Uploaded Documents
        documents = db.scalars(
            select(PatientDocument).where(PatientDocument.patient_id == patient_id).order_by(PatientDocument.created_at.desc())
        ).all()

        # 10. Risk Assessments
        risks = db.scalars(
            select(RiskAssessment).where(RiskAssessment.patient_id == patient_id).order_by(RiskAssessment.assessment_date.desc())
        ).all()

        return {
            "patient_id": patient_id,
            "full_name": f"{patient.first_name} {patient.last_name}",
            "gender": gender,
            "date_of_birth": str(dob),
            "district": patient.district,
            "blood_group": blood_grp,
            "conditions": [
                {
                    "diagnosis_name": c.diagnosis_name,
                    "code": c.diagnosis_code,
                    "status": c.clinical_status,
                    "onset_date": str(c.onset_date) if c.onset_date else None
                } for c in conditions
            ],
            "medications": [
                {
                    "medication_name": m.medication_name,
                    "dosage": m.dosage,
                    "status": m.status,
                    "prescribed_date": str(m.start_date) if m.start_date else None
                } for m in medications
            ],
            "observations": [
                {
                    "test_name": o.test_name,
                    "test_code": o.test_code,
                    "value_numeric": float(o.value_numeric) if o.value_numeric is not None else None,
                    "unit": o.unit,
                    "date": str(o.date),
                    "interpretation": o.interpretation,
                    "reference_range": o.reference_range
                } for o in observations
            ],
            "encounters": [
                {
                    "encounter_type": e.encounter_type,
                    "facility": e.facility,
                    "date": str(e.encounter_date),
                    "provider": e.attending_provider
                } for e in encounters
            ],
            "allergies": [
                {
                    "substance": a.substance,
                    "reaction": a.reaction,
                    "severity": a.severity,
                    "status": getattr(a, "verification_status", "confirmed")
                } for a in allergies
            ],
            "family_history": family_history,
            "daily_logs": [
                {
                    "date": str(d.log_date),
                    "systolic_bp": d.systolic_bp,
                    "diastolic_bp": d.diastolic_bp,
                    "fasting_glucose": d.fasting_glucose,
                    "pulse": d.pulse,
                    "spo2": d.spo2
                } for d in daily_logs
            ],
            "documents": [
                {
                    "id": d.document_id,
                    "filename": d.file_name,
                    "document_type": d.document_type,
                    "created_at": str(d.created_at)
                } for d in documents
            ],
            "risk_assessments": [
                {
                    "model_name": getattr(r, "model_type", None) or getattr(r, "model_name", "Risk Engine"),
                    "prediction_score": float(r.score) if getattr(r, "score", None) is not None else None,
                    "risk_level": getattr(r, "risk_category", None) or getattr(r, "risk_level", "Standard"),
                    "assessment_date": str(r.assessment_date)
                } for r in risks
            ]
        }

    @staticmethod
    def format_ehr_markdown(ehr: Dict[str, Any]) -> str:
        """Formats the longitudinal EHR record into an interactive, readable summary."""
        conds = ehr.get("conditions", [])
        meds = ehr.get("medications", [])
        obs = ehr.get("observations", [])
        logs = ehr.get("daily_logs", [])
        docs = ehr.get("documents", [])
        allergies = ehr.get("allergies", [])
        fam = ehr.get("family_history", [])

        md = [
            f"### Longitudinal Health Record: {ehr.get('full_name')} ({ehr.get('patient_id')})\n",
            f"- **Demographics:** {ehr.get('gender')}, DOB: {ehr.get('date_of_birth')}, District: {ehr.get('district') or 'Maharashtra'}, Blood Group: {ehr.get('blood_group') or 'Not recorded'}\n",
            "#### Active & Historical Diagnoses:"
        ]
        if conds:
            for c in conds:
                md.append(f"- **{c['diagnosis_name']}** (Code: `{c['code']}`, Status: `{c['status']}`, Onset: {c['onset_date'] or 'N/A'})")
        else:
            md.append("- *No clinical conditions recorded.*")

        md.append("\n#### Medications:")
        if meds:
            for m in meds:
                md.append(f"- **{m['medication_name']}** ({m['dosage']}, Status: `{m['status']}`, Prescribed: {m['prescribed_date'] or 'N/A'})")
        else:
            md.append("- *No active or historical medications recorded.*")

        md.append("\n#### Allergies & Sensitivities:")
        if allergies:
            for a in allergies:
                md.append(f"- **{a['substance']}** (Reaction: {a['reaction'] or 'Mild'}, Severity: `{a['severity']}`)")
        else:
            md.append("- *No known allergies documented.*")

        md.append("\n#### Recent Clinical Laboratory Observations:")
        if obs:
            for o in obs[:6]:
                ref = f" (Ref: {o['reference_range']})" if o.get("reference_range") else ""
                md.append(f"- **{o['test_name']}**: `{o['value_numeric']} {o['unit'] or ''}` on {o['date']}{ref}")
        else:
            md.append("- *No laboratory test results recorded.*")

        if logs:
            l = logs[0]
            md.append(f"\n#### Latest Home Vitals Log ({l['date']}):")
            md.append(f"- Blood Pressure: `{l['systolic_bp']}/{l['diastolic_bp']} mmHg` | Fasting Glucose: `{l['fasting_glucose']} mg/dL` | Pulse: `{l['pulse']} bpm`")

        if docs:
            md.append(f"\n#### Connected Clinical Documents ({len(docs)} files):")
            for d in docs[:3]:
                md.append(f"- `{d['filename']}` ({d['document_type']}) - uploaded on {d['created_at'][:10]}")

        if fam:
            md.append("\n#### Family Medical History:")
            for f in fam:
                md.append(f"- **{f['relationship'].title()}**: {', '.join(f['conditions']) if f['conditions'] else 'None reported'}")

        md.append("\n> [!NOTE]\n> *This summary reflects your authenticated electronic health record. To graph specific trends over time, you can ask 'Show my blood pressure trend' or 'Show my glucose history'.*")
        return "\n".join(md)
