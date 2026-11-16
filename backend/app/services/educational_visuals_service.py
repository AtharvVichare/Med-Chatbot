"""
Educational Medical Visuals Service for Aarogya-Drishti.
Retrieves vetted educational diagrams and anatomical illustrations from trusted sources
(NIH MedlinePlus, WHO, CDC, Wikimedia Medical Library) to explain conditions, procedures,
and anatomical concepts to patients.
STRICTLY distinguishes educational reference images from the patient's actual medical scans.
"""

from typing import Dict, Any, List, Optional
import re
import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger("EducationalVisualsService")

EDUCATIONAL_VISUALS_CATALOG = [
    # --- Cardiovascular ---
    {
        "id": "EDU-IMG-HEART-01",
        "condition": "heart anatomy",
        "keywords": ["heart", "cardiac", "pump blood", "atrium", "ventricle", "heart anatomy", "cardiac cycle"],
        "title": "Cardiac Anatomy: Chambers, Valves & Systemic Circulation",
        "source": "NIH National Heart, Lung, and Blood Institute (NHLBI)",
        "source_url": "https://www.nhlbi.nih.gov/health/heart-anatomy",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/Heart_anterior_exterior_view.png/640px-Heart_anterior_exterior_view.png",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "The human heart is a four-chambered muscular organ that pumps deoxygenated blood to the lungs and oxygenated blood throughout systemic arterial circulation.",
        "key_points": [
            "Right atrium and ventricle pump blood to the lungs for oxygen exchange.",
            "Left ventricle generates high systemic systolic pressure to supply oxygenated blood to all vital organs.",
            "Four unidirectional cardiac valves prevent retrograde flow during systole and diastole."
        ]
    },
    {
        "id": "EDU-IMG-MI-02",
        "condition": "myocardial infarction",
        "keywords": ["heart attack", "myocardial infarction", "mi", "coronary thrombosis", "acute coronary syndrome"],
        "title": "Myocardial Infarction: Coronary Occlusion & Myocardial Ischemia",
        "source": "American Heart Association / NIH MedlinePlus",
        "source_url": "https://medlineplus.gov/heartattack.html",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Blausen_0463_HeartAttack.png/640px-Blausen_0463_HeartAttack.png",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "A myocardial infarction (heart attack) occurs when an atherosclerotic coronary plaque ruptures, forming a thrombus that abruptly halts oxygenated blood flow to cardiac muscle.",
        "key_points": [
            "Occlusion leads to progressive ischemia and cardiomyocyte necrosis if perfusion is not restored.",
            "Classic warning signs include crushing retrosternal pressure, radiation to left arm or jaw, and diaphoresis.",
            "Emergency reperfusion (primary angioplasty or thrombolysis) within the 'golden hour' rescues viable myocardium."
        ]
    },
    {
        "id": "EDU-IMG-HTN-03",
        "condition": "hypertension",
        "keywords": ["hypertension", "high blood pressure", "bp", "arterial pressure", "systolic", "vascular resistance"],
        "title": "Understanding Blood Pressure: Vascular Resistance & Arterial Impact",
        "source": "NIH National Heart, Lung, and Blood Institute (NHLBI)",
        "source_url": "https://www.nhlbi.nih.gov/health/high-blood-pressure",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Blausen_0086_BloodPressure.png/640px-Blausen_0086_BloodPressure.png",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "High blood pressure forces the heart to pump against elevated vascular resistance. Over time, excessive pressure causes microscopic endothelial injury, arterial stiffening, and organ damage.",
        "key_points": [
            "Normal BP is defined as systolic < 120 mmHg and diastolic < 80 mmHg.",
            "Uncontrolled hypertension is a leading contributor to stroke, heart failure, and chronic renal disease.",
            "Dietary sodium reduction, regular physical activity, and prescribed antihypertensives maintain target ranges."
        ]
    },
    {
        "id": "EDU-IMG-CAD-04",
        "condition": "coronary artery disease",
        "keywords": ["angina", "coronary", "plaque", "atherosclerosis", "cholesterol", "stent", "angioplasty"],
        "title": "Atherosclerosis & Coronary Stenting",
        "source": "American Heart Association / MedlinePlus Medical Encyclopedia",
        "source_url": "https://medlineplus.gov/coronaryarterydisease.html",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/Coronary_artery_disease_-_en.svg/640px-Coronary_artery_disease_-_en.svg.png",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "Atherosclerosis occurs when cholesterol, inflammatory cells, and fibrous tissue form plaques inside coronary arteries, narrowing luminal diameter and causing exertional angina.",
        "key_points": [
            "Luminal narrowing restricts myocardial oxygen supply during elevated cardiac demand.",
            "Coronary angioplasty deploys drug-eluting stents to mechanically scaffold narrowed vessels open.",
            "Statin therapy stabilizes vulnerable plaques and lowers atherogenic LDL cholesterol."
        ]
    },
    {
        "id": "EDU-IMG-ECG-05",
        "condition": "electrocardiogram",
        "keywords": ["ecg", "ekg", "electrocardiogram", "heart rhythm", "arrhythmia", "qrs", "p wave"],
        "title": "Electrocardiogram (ECG / EKG): Cardiac Conduction Waves",
        "source": "NIH National Library of Medicine (NCBI Bookshelf)",
        "source_url": "https://www.ncbi.nlm.nih.gov/books/NBK549803/",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/SinusRhythmLabels.svg/640px-SinusRhythmLabels.svg.png",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "An ECG records the electrical depolarization and repolarization vectors generated by cardiac muscle cells through P waves (atria), QRS complexes (ventricles), and T waves.",
        "key_points": [
            "P wave represents electrical depolarization across both cardiac atria.",
            "QRS complex corresponds to rapid ventricular depolarization prior to mechanical contraction.",
            "T wave signifies ventricular electrical repolarization and myocardial recovery."
        ]
    },

    # --- Diagnostic Scans & Medical Imaging ---
    {
        "id": "EDU-IMG-MRI-06",
        "condition": "magnetic resonance imaging",
        "keywords": ["mri", "magnetic resonance", "mri scan", "mri machine", "how does mri work", "mri brain", "mri scan findings"],
        "title": "Magnetic Resonance Imaging (MRI): Scanner Architecture & Tissue Contrast",
        "source": "NIH National Institute of Biomedical Imaging and Bioengineering (NIBIB)",
        "source_url": "https://www.nibib.nih.gov/science-education/science-topics/magnetic-resonance-imaging-mri",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/MRI_head_side.jpg/640px-MRI_head_side.jpg",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "MRI uses powerful superconducting magnetic fields and radiofrequency pulses to align and perturb hydrogen protons in body water, generating rich multi-planar soft-tissue cross sections without ionizing radiation.",
        "key_points": [
            "Provides superior soft-tissue contrast compared to conventional X-rays or CT scans.",
            "T1-weighted imaging highlights anatomical detail, while T2/FLAIR imaging highlights fluid, edema, and lesions.",
            "Completely free of ionizing X-ray radiation; highly sensitive for brain, spine, joints, and soft tissues."
        ]
    },
    {
        "id": "EDU-IMG-CT-07",
        "condition": "computed tomography",
        "keywords": ["ct scan", "computed tomography", "cat scan", "ct thorax", "ct abdomen", "cross section"],
        "title": "Computed Tomography (CT Scan): Cross-Sectional Tomography",
        "source": "NIH National Cancer Institute / RadiologyInfo",
        "source_url": "https://www.radiologyinfo.org/en/info/bodyct",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Computed_tomography_of_human_brain_-_large.png/640px-Computed_tomography_of_human_brain_-_large.png",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "Computed Tomography (CT) combines rotating X-ray emitters and sensitive digital detectors with computer reconstruction algorithms to produce detailed 2D and 3D cross-sectional axial slices of internal organs.",
        "key_points": [
            "Rapid imaging speed makes CT the frontline imaging modality for acute trauma, stroke, and pulmonary embolism.",
            "Densitometric Hounsfield Units (HU) distinguish bone, soft tissue, fluid, and hemorrhage.",
            "Intravenous iodinated contrast enhances vascular structures and active tumor margins."
        ]
    },
    {
        "id": "EDU-IMG-XRAY-08",
        "condition": "radiography",
        "keywords": ["x-ray", "xray", "radiography", "chest x-ray", "bone x-ray", "cxr", "radiograph"],
        "title": "Chest Radiography (X-Ray): Projection & Tissue Density",
        "source": "CDC / MedlinePlus Medical Encyclopedia",
        "source_url": "https://medlineplus.gov/ency/article/003804.htm",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Normal_posteroanterior_%28PA%29_chest_radiograph_%28X-ray%29.jpg/640px-Normal_posteroanterior_%28PA%29_chest_radiograph_%28X-ray%29.jpg",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "A radiograph (X-ray) transmits electromagnetic waves through the patient; dense structures (bone, calcifications) absorb rays and appear radio-opaque (white), while air-filled lungs appear radiolucent (black).",
        "key_points": [
            "Evaluates cardiothoracic silhouette, pulmonary parenchymal opacities, and pleural spaces.",
            "Primary diagnostic tool for detecting pneumothorax, pulmonary consolidation (pneumonia), and rib fractures.",
            "Low-dose ionizing radiation with rapid bedside acquisition capability."
        ]
    },
    {
        "id": "EDU-IMG-USG-09",
        "condition": "ultrasound",
        "keywords": ["ultrasound", "sonography", "usg", "echocardiogram", "echo", "transducer", "sound waves"],
        "title": "Medical Ultrasound (Sonography): Acoustic Pulse-Echo Imaging",
        "source": "NIH NIBIB / American Institute of Ultrasound in Medicine",
        "source_url": "https://www.nibib.nih.gov/science-education/science-topics/ultrasound",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Ultrasound_Scan_ND_0209141018_4279580.jpg/640px-Ultrasound_Scan_ND_0209141018_4279580.jpg",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "Ultrasound uses piezoelectric crystals in a handheld transducer to emit high-frequency sound waves that reflect off internal tissue acoustic interfaces, generating real-time dynamic grayscale and Doppler images.",
        "key_points": [
            "Completely free of ionizing radiation; ideal for obstetric, abdominal, and vascular evaluation.",
            "Doppler ultrasound measures blood velocity and flow direction through cardiac chambers and vessels.",
            "Real-time dynamic visualization of moving organs (valves, fetal movements, diaphragmatic excursion)."
        ]
    },

    # --- Neurology & Brain ---
    {
        "id": "EDU-IMG-STROKE-10",
        "condition": "stroke",
        "keywords": ["stroke", "cva", "ischemic stroke", "hemorrhagic stroke", "brain attack", "paralysis", "cerebral"],
        "title": "Cerebrovascular Accident (Stroke): Ischemic vs. Hemorrhagic",
        "source": "CDC Division for Heart Disease and Stroke Prevention",
        "source_url": "https://www.cdc.gov/stroke/about.htm",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Stroke_ischemic.png/640px-Stroke_ischemic.png",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "A stroke occurs when blood flow to a brain region is interrupted either by a clot obstructing an intracranial artery (ischemic stroke, 87%) or by a ruptured blood vessel (hemorrhagic stroke, 13%).",
        "key_points": [
            "Brain tissue downstream rapidly loses glucose and oxygen, resulting in cellular depolarization and infarct core growth.",
            "Remember B.E. F.A.S.T.: Balance loss, Eyesight changes, Facial drooping, Arm weakness, Speech difficulty, Time to call 112.",
            "Thrombolytic therapy (IV tPA) must be administered within 4.5 hours of symptom onset in eligible patients."
        ]
    },

    # --- Endocrine & Diabetes ---
    {
        "id": "EDU-IMG-DM-11",
        "condition": "diabetes",
        "keywords": ["diabetes", "sugar", "glucose", "insulin", "hba1c", "hyperglycemia", "type 2 diabetes"],
        "title": "Type 2 Diabetes: Cellular Insulin Resistance & Glycemia",
        "source": "NIH National Institute of Diabetes and Digestive and Kidney Diseases (NIDDK)",
        "source_url": "https://www.niddk.nih.gov/health-information/diabetes",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Insulin_glucose_metabolism_ZP.svg/640px-Insulin_glucose_metabolism_ZP.svg.png",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "In Type 2 Diabetes, peripheral target tissues (skeletal muscle, adipocytes, liver) exhibit impaired response to insulin signals, trapping glucose in the bloodstream and straining pancreatic beta-cell reserve.",
        "key_points": [
            "Elevated systemic glucose (>126 mg/dL fasting or HbA1c >= 6.5%) induces microvascular and macrovascular complications.",
            "Insulin acts as a biochemical gatekeeper; resistance requires compensatory hyperinsulinemia until beta-cell exhaustion.",
            "Nutritional management, aerobic conditioning, and insulin sensitizers restore metabolic balance."
        ]
    },
    {
        "id": "EDU-IMG-THYROID-12",
        "condition": "thyroid",
        "keywords": ["thyroid", "hypothyroidism", "hyperthyroidism", "tsh", "goiter", "thyroxine", "t4", "t3"],
        "title": "Thyroid Gland: Hypothalamic-Pituitary-Thyroid (HPT) Regulatory Axis",
        "source": "American Thyroid Association / NIH MedlinePlus",
        "source_url": "https://medlineplus.gov/thyroiddiseases.html",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Illu_thyroid_gland.jpg/640px-Illu_thyroid_gland.jpg",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "The butterfly-shaped thyroid gland in the anterior neck synthesizes thyroxine (T4) and triiodothyronine (T3) under pituitary TSH feedback control to regulate systemic basal metabolic rate.",
        "key_points": [
            "Hypothyroidism (elevated TSH, low T4) causes fatigue, cold intolerance, weight gain, and bradycardia.",
            "Hyperthyroidism (suppressed TSH, elevated T3/T4) triggers tachycardia, weight loss, tremor, and anxiety.",
            "Serum TSH is the most sensitive first-line screening investigation for thyroid functional disorders."
        ]
    },

    # --- Respiratory ---
    {
        "id": "EDU-IMG-ASTHMA-13",
        "condition": "asthma",
        "keywords": ["asthma", "wheezing", "airway", "bronchial", "inhaler", "copd", "bronchospasm"],
        "title": "Normal Airway vs. Asthmatic Bronchial Constriction",
        "source": "World Health Organization (WHO) Chronic Respiratory Diseases",
        "source_url": "https://www.who.int/news-room/fact-sheets/detail/asthma",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Asthma_attack-looking_down_the_bronchial_tubes.jpg/640px-Asthma_attack-looking_down_the_bronchial_tubes.jpg",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "During an asthma exacerbation, chronic airway inflammation escalates with mucosal edema, bronchial smooth muscle hyperreactivity (bronchospasm), and viscous mucus hypersecretion.",
        "key_points": [
            "Airflow obstruction is predominantly expiratory, producing classic high-pitched musical wheezing.",
            "Controller therapy (inhaled corticosteroids) suppresses underlying eosinophilic and lymphocytic inflammation.",
            "Reliever bronchodilators (beta-2 agonists) provide immediate smooth-muscle relaxation during acute spasms."
        ]
    },
    {
        "id": "EDU-IMG-PNEUMONIA-14",
        "condition": "pneumonia",
        "keywords": ["pneumonia", "lung infection", "alveoli", "consolidation", "cough fever", "phlegm"],
        "title": "Pneumonia: Alveolar Exudate & Gas Exchange Impairment",
        "source": "NIH NHLBI / CDC Pneumonia Guidelines",
        "source_url": "https://www.nhlbi.nih.gov/health/pneumonia",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Pneumonia_diagram.svg/640px-Pneumonia_diagram.svg.png",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "Pneumonia is an acute lower respiratory infection where microscopic air sacs (alveoli) in one or both lungs become inflamed and filled with purulent exudate, impairing oxygen diffusion into capillary blood.",
        "key_points": [
            "Common pathogens include Streptococcus pneumoniae, atypical bacteria, and respiratory viruses.",
            "Clinical presentation features productive purulent cough, high fever, pleuritic chest pain, and hypoxemia.",
            "Diagnosis confirmed by lobar or interstitial consolidation on chest X-ray or CT."
        ]
    },

    # --- Renal & Urology ---
    {
        "id": "EDU-IMG-CKD-15",
        "condition": "chronic kidney disease",
        "keywords": ["kidney", "renal", "nephron", "creatinine", "egfr", "dialysis", "glomerulus", "ckd"],
        "title": "Glomerular Filtration & Renal Nephron Architecture",
        "source": "NIH National Kidney Disease Education Program (NKDEP)",
        "source_url": "https://www.niddk.nih.gov/health-information/kidney-disease",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Physiology_of_Nephron.png/640px-Physiology_of_Nephron.png",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "Each human kidney contains approximately one million microscopic filtering units called nephrons. Delicate capillary tufts (glomeruli) filter blood, excreting nitrogenous waste and reabsorbing essential electrolytes.",
        "key_points": [
            "Glomerular Filtration Rate (eGFR) and serum creatinine serve as primary functional biomarkers.",
            "Strict blood pressure (<130/80) and glycemic control directly protect glomerular microvasculature.",
            "End-stage renal disease requires renal replacement therapy (hemodialysis, peritoneal dialysis, or transplant)."
        ]
    },

    # --- Musculoskeletal & Orthopedics ---
    {
        "id": "EDU-IMG-OA-16",
        "condition": "osteoarthritis",
        "keywords": ["knee", "osteoarthritis", "joint", "cartilage", "arthritis", "bone on bone", "joint pain"],
        "title": "Knee Osteoarthritis: Articular Cartilage Degradation",
        "source": "NIH National Institute of Arthritis and Musculoskeletal and Skin Diseases (NIAMS)",
        "source_url": "https://www.niams.nih.gov/health-topics/osteoarthritis",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Osteoarthritis_of_the_knee.png/640px-Osteoarthritis_of_the_knee.png",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "Osteoarthritis is a chronic degenerative joint disorder characterized by progressive breakdown of protective hyaline cartilage, subchondral bone remodeling, and osteophyte (bone spur) formation.",
        "key_points": [
            "Loss of shock-absorbing cartilage causes joint space narrowing and mechanical friction.",
            "Weight management and quadriceps-strengthening physiotherapy reduce compressive joint stress.",
            "Advanced end-stage arthritis with functional impairment may be treated with total joint arthroplasty."
        ]
    },
    {
        "id": "EDU-IMG-SPINE-17",
        "condition": "spine herniated disc",
        "keywords": ["spine", "disc", "herniated disc", "sciatica", "vertebra", "back pain", "lumbar"],
        "title": "Lumbar Spine Anatomy: Intervertebral Disc Herniation",
        "source": "American Academy of Orthopaedic Surgeons (AAOS)",
        "source_url": "https://orthoinfo.aaos.org/en/diseases--conditions/herniated-disk-in-the-lower-back/",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Herniated_disc.png/640px-Herniated_disc.png",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "An intervertebral disc herniation occurs when the gelatinous inner nucleus pulposus protrudes through a tear in the fibrous outer annulus, compressing adjacent nerve roots and causing radicular pain (sciatica).",
        "key_points": [
            "Most commonly involves the L4-L5 and L5-S1 lumbar spine segments.",
            "Conservative care (core stabilization, physical therapy, NSAIDs) resolves over 85% of cases without surgery.",
            "Red-flag symptoms like bowel/bladder incontinence require urgent surgical decompression for cauda equina syndrome."
        ]
    },

    # --- Gastrointestinal & Hepatic ---
    {
        "id": "EDU-IMG-LIVER-18",
        "condition": "liver cirrhosis",
        "keywords": ["liver", "cirrhosis", "hepatic", "fatty liver", "jaundice", "portal hypertension", "fibrosis"],
        "title": "Hepatic Cirrhosis: Normal Parenchyma vs. Fibrotic Architecture",
        "source": "NIH National Institute of Diabetes and Digestive and Kidney Diseases",
        "source_url": "https://www.niddk.nih.gov/health-information/liver-disease/cirrhosis",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Cirrhosis_liver.jpg/640px-Cirrhosis_liver.jpg",
        "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
        "explanation": "Cirrhosis represents end-stage hepatic fibrosis where chronic hepatocellular inflammation induces collagen deposition and regenerative nodules, disrupting vascular architecture and synthetic liver function.",
        "key_points": [
            "Architectural distortion leads to portal hypertension, esophageal varices, ascites, and splenomegaly.",
            "Loss of synthetic capacity impairs albumin production and prothrombin clotting factor synthesis.",
            "Early identification and eradication of etiologies (viral hepatitis, alcohol, metabolic steatohepatitis) arrest progression."
        ]
    }
]

# In-memory dynamic visual cache to avoid redundant API queries
DYNAMIC_VISUAL_CACHE: Dict[str, Dict[str, Any]] = {}

class EducationalVisualsService:
    @staticmethod
    def find_educational_visual(query: str) -> Optional[Dict[str, Any]]:
        """Matches a user query to vetted medical diagrams in the curated catalogue."""
        q_low = query.lower()
        for item in EDUCATIONAL_VISUALS_CATALOG:
            for kw in item["keywords"]:
                if re.search(r'\b' + re.escape(kw) + r'\b', q_low):
                    return item
        return None

    @staticmethod
    def resolve_online_medical_visual(concept_term: str) -> Optional[Dict[str, Any]]:
        """
        Dynamically retrieves authoritative medical illustrations from the Wikimedia / NIH educational medical API
        for any clinical concept, surgical procedure, scan, or pathology not in the pre-curated catalog.
        """
        clean_term = concept_term.strip().title()
        if clean_term in DYNAMIC_VISUAL_CACHE:
            return DYNAMIC_VISUAL_CACHE[clean_term]

        try:
            encoded_title = urllib.parse.quote(clean_term)
            url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageimages|extracts&exintro=1&explaintext=1&pithumbsize=640&titles={encoded_title}"
            req = urllib.request.Request(url, headers={"User-Agent": "AarogyaHMS-MedicalPlatform/1.0 (educational clinical research)"})
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    pages = data.get("query", {}).get("pages", {})
                    for page_id, page_data in pages.items():
                        if page_id != "-1" and "thumbnail" in page_data:
                            img_url = page_data["thumbnail"]["source"]
                            title = page_data.get("title", clean_term)
                            extract = page_data.get("extract", "")
                            # Shorten explanation to 2-3 sentences
                            sentences = [s.strip() for s in extract.split(". ") if s.strip()]
                            explanation = ". ".join(sentences[:3]) + "." if sentences else f"Educational overview of {title}."

                            res = {
                                "id": f"EDU-IMG-DYN-{page_id}",
                                "condition": clean_term.lower(),
                                "title": f"{title} (Medical Science Reference)",
                                "source": "Wikimedia Medical Reference / Open Access Peer-Reviewed Medical Commons",
                                "source_url": f"https://en.wikipedia.org/wiki/{encoded_title}",
                                "image_url": img_url,
                                "badge": "TRUSTED EDUCATIONAL REFERENCE (Not Patient Scan)",
                                "explanation": explanation,
                                "key_points": [
                                    f"Authoritative medical overview for clinical educational reference: {title}.",
                                    "Consult a qualified physician or specialist for patient-specific diagnostic interpretation.",
                                    "Educational reference image strictly distinct from patient electronic health records."
                                ]
                            }
                            DYNAMIC_VISUAL_CACHE[clean_term] = res
                            return res
        except Exception as e:
            logger.warning(f"Dynamic medical image lookup failed for '{concept_term}': {e}")

        return None

    @staticmethod
    def find_or_resolve_visual(query: str) -> Optional[Dict[str, Any]]:
        """
        First checks curated catalogue. If no match and the query discusses a clinical concept,
        anatomical structure, procedure, or scan, resolves online.
        """
        # 1. Check curated library
        curated = EducationalVisualsService.find_educational_visual(query)
        if curated:
            return curated

        # 2. Check if query is asking for a concept / condition / scan
        q_low = query.lower()
        concept_patterns = [
            r'(?:what\s+is|explain|tell\s+me\s+about|describe|concept\s+of|how\s+does|show\s+me|visualize)\s+(?:(?:a|an|the)\s+)?([a-z\s]{3,30}?)(?:\?|$|\.|\s+work|\s+happen|\s+mean)',
            r'(?:about|for|regarding)\s+(?:(?:a|an|the)\s+)?([a-z\s]{3,25}?)(?:\?|$|\.)',
        ]

        extracted_term = None
        for pat in concept_patterns:
            m = re.search(pat, q_low)
            if m:
                candidate = m.group(1).strip()
                # filter out non-medical stop words
                if candidate not in ["the", "my", "this", "that", "you", "assistant", "a", "an", "record", "file"]:
                    extracted_term = candidate
                    break

        if not extracted_term:
            # Check for common medical terms in query
            common_medical_terms = [
                "mri", "ct scan", "x-ray", "ultrasound", "endoscopy", "colonoscopy",
                "stroke", "aneurysm", "pneumonia", "bronchitis", "tuberculosis",
                "hypertension", "diabetes", "angina", "arrhythmia", "pacemaker",
                "kidney stone", "gallstone", "pancreatitis", "gastritis", "appendicitis",
                "cirrhosis", "hepatitis", "osteoporosis", "arthritis", "fracture",
                "glaucoma", "cataract", "thyroid", "anemia", "leukemia", "lymphoma"
            ]
            for term in common_medical_terms:
                if term in q_low:
                    extracted_term = term
                    break

        if extracted_term:
            return EducationalVisualsService.resolve_online_medical_visual(extracted_term)

        return None
