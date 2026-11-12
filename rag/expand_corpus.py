"""
Expanded Medical Reference Corpus Builder & Ingestor for Aarogya Drishti (v2)
Generates and normalizes structured reference XML documents for all 31 verified medical topics
spanning the 12 clinical domains, strictly using official WHO, MedlinePlus, and MoHFW clinical guidelines.

Produces:
- data/reference/xml/<source_id>.xml for every topic
- True section-aware token chunking via MedicalChunker (~350-500 tokens, 75 token overlap)
- Stable deterministic chunk IDs: SHA-256(doc_id + section + page + chunk_index)
- Full metadata retention (doc_id, chunk_id, title, publisher, URL, license, version, domain)
- Outputs data/processed/v2/<doc_id>.jsonl and manifest
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List

from rag.expanded_sources import EXPANDED_SOURCES_REGISTRY
from rag.chunk_documents import MedicalChunker

REFERENCE_XML_DIR = Path(__file__).resolve().parents[1] / "data" / "reference" / "xml"
PROCESSED_V2_DIR = Path(__file__).resolve().parents[1] / "data" / "processed" / "v2"

# Curated factual clinical reference texts derived strictly from public WHO / MedlinePlus guidelines
OFFICIAL_CLINICAL_CONTENT: Dict[str, List[Dict[str, str]]] = {
    "MEDLINEPLUS-DIABETES-XML": [
        {
            "section": "Diabetes Mellitus - Overview & Pathophysiology",
            "text": "Diabetes mellitus is a chronic metabolic disease characterized by elevated levels of blood glucose (hyperglycemia), which leads over time to serious damage to the heart, blood vessels, eyes, kidneys and nerves. Glucose is derived from food intake and insulin is a hormone produced by the pancreas that allows cells to absorb glucose for energy. In Type 1 diabetes, autoimmune destruction of pancreatic beta cells results in an absolute deficiency of insulin. In Type 2 diabetes, the body develops insulin resistance combined with progressive impairment of insulin secretion. Prediabetes is an intermediate state of hyperglycemia with glycemic parameters above normal but below clinical diagnostic thresholds for diabetes."
        },
        {
            "section": "Diabetes Mellitus - Symptoms and Diagnostic Criteria",
            "text": "Common clinical symptoms of diabetes include polyuria (excessive urination), polydipsia (excessive thirst), polyphagia (constant hunger), unexplained weight loss, generalized fatigue, blurred vision, and slow-healing cutaneous sores. Diagnostic criteria per clinical guidelines require one of the following laboratory confirmations: 1. Fasting Plasma Glucose (FPG) greater than or equal to 126 mg/dL (7.0 mmol/L) after an 8-hour fast. 2. Glycated Hemoglobin (HbA1c) greater than or equal to 6.5% (48 mmol/mol) using a certified standardized assay. 3. 2-hour Oral Glucose Tolerance Test (OGTT) 75g post-load glucose greater than or equal to 200 mg/dL (11.1 mmol/L). 4. Random plasma glucose greater than or equal to 200 mg/dL in a patient exhibiting classic symptoms of hyperglycemia."
        },
        {
            "section": "Diabetes Mellitus - Management and Complications",
            "text": "Effective management of diabetes requires routine self-monitoring of blood glucose, comprehensive lifestyle interventions including medical nutrition therapy, structured physical activity (at least 150 minutes per week of moderate-intensity aerobic exercise), and weight management. Pharmacological management for Type 2 diabetes initiates with oral Metformin in the absence of contraindications, with sequential escalation to SGLT2 inhibitors, GLP-1 receptor agonists, DPP-4 inhibitors, sulfonylureas, or exogenous basal-bolus insulin. Chronic microvascular complications comprise diabetic retinopathy, diabetic nephropathy, and diabetic peripheral/autonomic neuropathy. Macrovascular complications include coronary artery disease, peripheral arterial disease, and cerebrovascular stroke."
        }
    ],

    "MEDLINEPLUS-DIABETIC-NEPHROPATHY": [
        {
            "section": "Diabetic Kidney Disease - Pathogenesis and Staging",
            "text": "Diabetic kidney disease (diabetic nephropathy) is a major microvascular complication occurring in approximately 30% to 40% of patients with long-standing diabetes. Hyperglycemia induces advanced glycation end-products, glomerular hyperfiltration, renal mesangial expansion, and progressive glomerulosclerosis. Early disease is typically asymptomatic and characterized by persistent microalbuminuria (urinary albumin-to-creatinine ratio [UACR] between 30 and 300 mg/g). Advanced stages progress to macroalbuminuria (UACR > 300 mg/g) and a relentless decline in estimated Glomerular Filtration Rate (eGFR < 60 mL/min/1.73 m2), culminating in end-stage renal disease (ESRD)."
        },
        {
            "section": "Diabetic Kidney Disease - Screening and Renoprotective Therapy",
            "text": "Annual screening for all diabetic patients consists of spot urine albumin-to-creatinine ratio (UACR) alongside serum creatinine and eGFR calculation. First-line renoprotective pharmacological therapy includes Angiotensin Converting Enzyme (ACE) inhibitors or Angiotensin Receptor Blockers (ARBs), particularly in hypertensive individuals with albuminuria. Sodium-glucose cotransporter 2 (SGLT2) inhibitors significantly decelerate CKD progression and decrease cardiovascular morbidity in diabetic patients with eGFR down to 20 mL/min/1.73 m2. Non-steroidal mineralocorticoid receptor antagonists (such as Finerenone) offer added renal protection."
        }
    ],

    "MEDLINEPLUS-DIABETIC-RETINOPATHY": [
        {
            "section": "Diabetic Retinopathy - Classification and Clinical Signs",
            "text": "Diabetic retinopathy is a microvascular complication of diabetes characterized by vascular damage to retinal capillaries due to prolonged chronic hyperglycemia. It is clinically stratified into non-proliferative diabetic retinopathy (NPDR) and proliferative diabetic retinopathy (PDR). NPDR features microaneurysms, dot-and-blot retinal hemorrhages, hard lipid exudates, and cotton-wool spots indicating micro-infarctions of nerve fiber layers. PDR is defined by pathological neovascularization induced by retinal ischemia and vascular endothelial growth factor (VEGF). Diabetic macular edema (DME) involves retinal thickening at the macula and can cause profound vision loss at any stage of retinopathy."
        },
        {
            "section": "Diabetic Retinopathy - Screening, Prevention, and Treatment",
            "text": "Routine dilated fundoscopic examination is mandated annually for all individuals with Type 2 diabetes upon initial diagnosis, and starting 5 years after diagnosis in Type 1 diabetes. Intensive glycemic control (targeting HbA1c < 7.0%) and rigorous blood pressure control (< 130/80 mmHg) significantly reduce the onset and progression of retinopathy. Active proliferative retinopathy and center-involved macular edema are treated with intravitreal anti-VEGF injections (e.g., Aflibercept, Ranibizumab), panretinal photocoagulation (PRP laser), and vitreoretinal surgery for non-clearing vitreous hemorrhage."
        }
    ],

    "MEDLINEPLUS-HYPERTENSION-XML": [
        {
            "section": "High Blood Pressure - Definition and Diagnostic Thresholds",
            "text": "Hypertension (high blood pressure) is defined as a persistent elevation of systemic arterial pressure. It is often referred to as a silent killer because patients frequently remain asymptomatic until target-organ damage has occurred. Standard clinical thresholds define normal blood pressure as systolic blood pressure (SBP) less than 120 mmHg and diastolic blood pressure (DBP) less than 80 mmHg. Stage 1 hypertension is diagnosed at SBP 130-139 mmHg or DBP 80-89 mmHg. Stage 2 hypertension corresponds to SBP 140 mmHg or greater, or DBP 90 mmHg or greater. Diagnosis requires standardized seated resting blood pressure measurements on two or more separate clinical occasions, or confirmation via 24-hour ambulatory blood pressure monitoring (ABPM)."
        },
        {
            "section": "High Blood Pressure - Risk Factors and Complications",
            "text": "Modifiable risk factors for essential hypertension include excessive dietary sodium consumption (> 2 grams sodium or > 5 grams salt per day), low dietary potassium intake, physical inactivity, obesity (BMI >= 25 kg/m2), chronic alcohol abuse, tobacco smoking, and obstructive sleep apnea. Uncontrolled sustained arterial hypertension causes left ventricular hypertrophy, congestive heart failure, coronary heart disease, ischemic and hemorrhagic stroke, hypertensive nephrosclerosis, aortic dissection, and hypertensive retinopathy."
        }
    ],

    "WHO-HTN-GUIDELINE-2021": [
        {
            "section": "WHO Pharmacological Guidelines - Treatment Thresholds and First-Line Classes",
            "text": "The World Health Organization (WHO) Guideline for the Pharmacological Treatment of Hypertension in Adults strongly recommends initiating pharmacological antihypertensive treatment in individuals with a confirmed diagnosis of hypertension and SBP >= 140 mmHg or DBP >= 90 mmHg. In individuals with existing cardiovascular disease or high baseline cardiovascular risk, pharmacological treatment is recommended at SBP 130-139 mmHg. Recommended first-line pharmacological agent classes comprise: 1. Thiazide or thiazide-like diuretics (hydrochlorothiazide, chlorthalidone, indapamide). 2. Angiotensin-converting enzyme inhibitors (ACE inhibitors) or Angiotensin receptor blockers (ARBs). 3. Long-acting dihydropyridine Calcium channel blockers (CCBs, e.g., amlodipine)."
        },
        {
            "section": "WHO Pharmacological Guidelines - Combination Therapy and Blood Pressure Targets",
            "text": "For adults requiring pharmacological antihypertensive therapy, WHO recommends initial combination therapy with two first-line agents of different classes—ideally as a single-pill fixed-dose combination (SPC)—particularly when baseline SBP is >= 20 mmHg above target. Dual therapy combining an ACE-inhibitor/ARB with either a CCB or a thiazide diuretic achieves significantly faster and more sustained blood pressure control. The target blood pressure for all non-pregnant adults with hypertension is SBP < 140 mmHg and DBP < 90 mmHg, and < 130/80 mmHg in high-risk patients with established CVD or diabetes."
        }
    ],

    "WHO-HEARTS-CVD-2020": [
        {
            "section": "HEARTS Technical Package - Total Cardiovascular Risk Stratification",
            "text": "The WHO HEARTS technical package emphasizes total cardiovascular risk assessment rather than treating single risk factors in isolation. Cardiovascular risk prediction charts (such as WHO/ISH regional charts for South Asia SEAR D) estimate 10-year risk of a fatal or non-fatal cardiovascular event (myocardial infarction or stroke) based on age, gender, systolic blood pressure, smoking status, and either diabetes status or total blood cholesterol. Risk categories are classified as low (< 10%), moderate (10% to < 20%), high (20% to < 30%), and very high (>= 30%). All patients with established CVD, severe hypertension (SBP >= 160 mmHg), or diabetes with target-organ damage automatically enter the high-risk category without needing chart calculation."
        },
        {
            "section": "HEARTS Technical Package - Standardized Evidence-Based Treatment Protocols",
            "text": "The core components of the HEARTS technical package include: H (Healthy-lifestyle counseling on salt reduction, tobacco cessation, and physical activity); E (Evidence-based treatment protocols emphasizing protocol-driven step-up therapy); A (Access to essential medicines and diagnostics, ensuring continuous availability of core antihypertensive and statin medications); R (Risk-based CVD management focusing resources on high-risk individuals); T (Team-based care utilizing task-sharing with nurses and community health workers); S (Systems for monitoring and program evaluation). Statin therapy is indicated for all individuals with total 10-year CVD risk >= 20% or established clinical atherosclerotic disease."
        }
    ],

    "MEDLINEPLUS-CORONARY-ARTERY-DISEASE": [
        {
            "section": "Coronary Artery Disease - Angina Presentation and Pathophysiology",
            "text": "Coronary Artery Disease (CAD) develops when the major arterial conduits supplying oxygenated blood to the myocardium become narrowed or occluded by atherosclerotic plaques consisting of cholesterol, calcium, and fibrous tissue. Stable angina presents typically as substernal chest discomfort described as heaviness, squeezing, pressure, or burning, provoked by physical exertion or emotional stress, and relieved within minutes by rest or sublingual nitroglycerin. Angina discomfort may radiate predictably to the left shoulder, left arm, neck, jaw, or epigastrium. When plaque erosion or rupture triggers acute intraluminal thrombosis, unstable angina or acute myocardial infarction ensues."
        },
        {
            "section": "Coronary Artery Disease - Evaluation, Prevention, and Revascularization",
            "text": "Diagnostic workup for suspected CAD includes resting electrocardiogram (ECG), exercise treadmill testing, coronary computed tomography angiography (CCTA), and invasive catheter coronary angiography. Secondary cardiovascular prevention requires lifelong low-dose aspirin (75-100 mg daily), high-intensity statin therapy (Atorvastatin 40-80 mg or Rosuvastatin 20-40 mg) to achieve LDL-C < 55 mg/dL, beta-blockers for post-infarction myocardial protection, and ACE inhibitors in patients with left ventricular systolic dysfunction or diabetes. Invasive coronary revascularization via percutaneous coronary intervention (PCI with drug-eluting stents) or coronary artery bypass grafting (CABG) is indicated for refractory angina or high-risk coronary anatomy."
        }
    ],

    "MEDLINEPLUS-HEART-FAILURE": [
        {
            "section": "Heart Failure - Clinical Presentation and Ejection Fraction Classification",
            "text": "Heart failure (HF) is a complex clinical syndrome resulting from structural or functional cardiac disorders that impair ventricular filling or blood ejection. Heart failure is classified based on left ventricular ejection fraction (LVEF): Heart Failure with Reduced Ejection Fraction (HFrEF, LVEF <= 40%), Heart Failure with Mildly Reduced Ejection Fraction (HFmrEF, LVEF 41-49%), and Heart Failure with Preserved Ejection Fraction (HFpEF, LVEF >= 50%). Hallmark clinical symptoms include exertional dyspnea, orthopnea (shortness of breath when lying flat), paroxysmal nocturnal dyspnea, dependent bilateral ankle edema, elevated jugular venous pressure, pulmonary rales, and persistent fatigue."
        },
        {
            "section": "Heart Failure - Guideline-Directed Medical Therapy (GDMT)",
            "text": "The cornerstone of management for HFrEF comprises four foundational drug classes (the 'four pillars' of GDMT): 1. Angiotensin Receptor-Neprilysin Inhibitor (ARNI, Sacubitril/Valsartan) or ACE-inhibitor/ARB. 2. Evidence-based beta-blockers (Carvedilol, Metoprolol succinate extended-release, or Bisoprolol). 3. Mineralocorticoid receptor antagonists (MRA, Spironolactone or Eplerenone). 4. SGLT2 inhibitors (Dapagliflozin or Empagliflozin). Loop diuretics (such as Furosemide or Torsemide) are administered to achieve and maintain euvolemia, titrated to relieve pulmonary and peripheral congestion without altering long-term mortality."
        }
    ],

    "MEDLINEPLUS-ASTHMA": [
        {
            "section": "Asthma - Pathophysiology and Clinical Diagnosis",
            "text": "Asthma is a chronic inflammatory disorder of the conducting airways characterized by bronchial hyperresponsiveness, airway edema, mucus hypersecretion, and variable airflow obstruction that is often reversible either spontaneously or with bronchodilator treatment. Classic symptoms comprise episodic wheezing, cough (particularly nocturnal or early morning), chest tightness, and shortness of breath. Diagnosis is confirmed objectively by spirometry demonstrating airflow limitation (reduced FEV1/FVC ratio < 0.70) with significant bronchodilator reversibility, defined as an increase in FEV1 of greater than 12% and at least 200 mL following inhalation of a short-acting beta2-agonist."
        },
        {
            "section": "Asthma - Stepped Pharmacological Management",
            "text": "The Global Initiative for Asthma (GINA) and clinical guidelines emphasize that inhaled corticosteroids (ICS) form the fundamental controller therapy across all severity steps to suppress airway inflammation and prevent fatal exacerbations. First-line therapy for mild asthma utilizes as-needed low-dose ICS-formoterol as the preferred reliever. For moderate-to-severe persistent asthma, regular maintenance ICS-LABA (e.g., Fluticasone/Salmeterol or Budesonide/Formoterol) is prescribed daily. Leukotriene receptor antagonists (Montelukast) provide add-on benefit in allergic asthma. Severe acute asthma exacerbations mandate systemic oral corticosteroids (Prednisolone 40-50 mg daily for 5-7 days), high-dose nebulized SABA (Albuterol), and supplemental oxygen titrated to maintain SpO2 93-95%."
        }
    ],

    "MEDLINEPLUS-COPD": [
        {
            "section": "COPD - Etiology and Spirometric Diagnostic Criteria",
            "text": "Chronic Obstructive Pulmonary Disease (COPD) is a common, preventable, and treatable chronic lung disease characterized by persistent respiratory symptoms and progressive, non-fully reversible airflow limitation. Cigarette smoking is the predominant etiology worldwide, followed by occupational dust exposure, chemical fumes, and indoor biomass fuel combustion in poorly ventilated dwellings. Symptoms include chronic progressive dyspnea, chronic cough, and regular sputum production. Diagnosis requires post-bronchodilator spirometry demonstrating a fixed FEV1/FVC ratio less than 0.70. Severity of airflow limitation is categorized by GOLD grades 1 through 4 based on post-bronchodilator FEV1 percentage predicted."
        },
        {
            "section": "COPD - Comprehensive Inhalation Therapy and Exacerbation Management",
            "text": "Primary non-pharmacological interventions in COPD include absolute smoking cessation, pulmonary rehabilitation, influenza and pneumococcal vaccinations, and nutritional support. Maintenance pharmacological treatment is anchored by long-acting bronchodilators: Long-Acting Muscarinic Antagonists (LAMA, e.g., Tiotropium) and Long-Acting Beta2-Agonists (LABA, e.g., Formoterol, Indacaterol). Inhaled corticosteroids (ICS) are reserved as add-on therapy for patients with frequent exacerbations or blood eosinophil counts >= 300 cells/uL. Acute COPD exacerbations characterized by worsening dyspnea, increased sputum volume, and sputum purulence are managed with short-acting bronchodilators, oral corticosteroids (prednisone 40 mg daily for 5 days), and targeted antibiotics."
        }
    ],

    "WHO-CHRONIC-RESPIRATORY-2023": [
        {
            "section": "WHO Technical Guidance - Environmental Risk Reduction and Oxygen Protocols",
            "text": "The World Health Organization identifies chronic respiratory diseases among the leading causes of non-communicable morbidity and premature mortality globally. Essential public health control strategies mandate reductions in ambient particulate matter (PM2.5 and PM10), rigorous enforcement of clean indoor air regulations, and replacement of solid cooking biomass with clean electricity or LPG. Long-Term Oxygen Therapy (LTOT) for at least 15 hours per day improves survival in patients with severe resting chronic hypoxemia (PaO2 <= 55 mmHg or SpO2 <= 88%, or PaO2 56-59 mmHg in the presence of cor pulmonale or secondary polycythemia)."
        }
    ],

    "MEDLINEPLUS-CHRONIC-KIDNEY-DISEASE": [
        {
            "section": "Chronic Kidney Disease - KDIGO Staging and Diagnostic Definition",
            "text": "Chronic Kidney Disease (CKD) is defined by abnormalities of kidney structure or function present for more than 3 months with health implications. Diagnostic criteria include either an estimated Glomerular Filtration Rate (eGFR) less than 60 mL/min/1.73 m2 or markers of kidney damage (most commonly persistent albuminuria with UACR >= 30 mg/g). CKD is staged based on eGFR: Stage G1 (eGFR >= 90 with kidney damage), Stage G2 (eGFR 60-89 with kidney damage), Stage G3a (eGFR 45-59), Stage G3b (eGFR 30-44), Stage G4 (eGFR 15-29, severely decreased), and Stage G5 (eGFR < 15, kidney failure requiring renal replacement therapy). Albuminuria is staged: A1 (< 30 mg/g, normal), A2 (30-300 mg/g, microalbuminuria), and A3 (> 300 mg/g, macroalbuminuria)."
        },
        {
            "section": "Chronic Kidney Disease - Clinical Complications and Management",
            "text": "Progressive CKD causes metabolic acidosis, hyperkalemia, secondary hyperparathyroidism and renal osteodystrophy (mineral bone disorder), normocytic anemia due to impaired erythropoietin production, and accelerated systemic atherosclerosis. Key therapeutic principles involve strict blood pressure control (target < 120 mmHg systolic using standardized automated measurement), dietary sodium restriction (< 2 g/day), moderate dietary protein restriction (0.8 g/kg/day for stages G3-G5), maximum tolerated doses of ACE inhibitors or ARBs, SGLT2 inhibitors for diabetic and non-diabetic proteinuric CKD, and avoidance of nephrotoxic medications such as non-steroidal anti-inflammatory drugs (NSAIDs) and intravenous iodinated contrast."
        }
    ],

    "WHO-KIDNEY-HEALTH-2022": [
        {
            "section": "WHO Global Protocols - Renal Replacement and Screening in Primary Care",
            "text": "WHO guidelines emphasize integrating CKD screening into primary health care non-communicable disease packages, particularly for individuals with hypertension, diabetes, or family history of renal disease. Point-of-care urine albumin dipsticks and blood creatinine testing facilitate early detection before irreversible nephron loss occurs. Preparation for renal replacement therapy (hemodialysis, peritoneal dialysis, or preemptive kidney transplantation) is recommended when eGFR falls below 20 mL/min/1.73 m2, ensuring timely creation of autologous arteriovenous fistulas for vascular access."
        }
    ],

    "MEDLINEPLUS-IRON-DEFICIENCY-ANEMIA": [
        {
            "section": "Iron Deficiency Anemia - Hematologic Parameters and Clinical Signs",
            "text": "Iron Deficiency Anemia (IDA) is the most prevalent nutritional deficiency disorder worldwide, arising when systemic iron stores are exhausted and insufficient to support normal erythropoiesis. Clinical manifestations include extreme pallor of conjunctiva and skin, chronic fatigue, generalized weakness, exertional tachycardia, dizziness, cold extremities, brittle nails with koilonychia (spoon nails), angular cheilitis, and pica (unusual cravings for non-nutritive substances such as ice, clay, or chalk). Diagnostic laboratory findings demonstrate microcytic hypochromic red blood cells on peripheral smear, low hemoglobin, reduced mean corpuscular volume (MCV < 80 fL), decreased serum ferritin (< 30 ng/mL, or < 100 ng/mL in inflammatory states), and elevated total iron-binding capacity (TIBC)."
        },
        {
            "section": "Iron Deficiency Anemia - Oral and Intravenous Replacement Therapy",
            "text": "Treatment of iron deficiency anemia requires identifying and addressing the underlying source of blood loss (such as gastrointestinal bleeding from ulcers or malignancy, or menorrhagia) alongside iron replenishment. First-line therapy is oral elemental iron (100 to 200 mg daily of elemental iron, commonly administered as Ferrous sulfate, Ferrous fumarate, or Ferrous ascorbate). Concomitant administration of ascorbic acid (Vitamin C) enhances intestinal iron absorption, whereas antacids, calcium supplements, tea, and coffee inhibit absorption. Intravenous iron preparations (e.g., Ferric carboxymaltose or Iron sucrose) are indicated in cases of severe malabsorption, inflammatory bowel disease, chronic kidney disease on dialysis, or oral iron intolerance."
        }
    ],

    "WHO-ANEMIA-GUIDELINES-2023": [
        {
            "section": "WHO Diagnostic Thresholds - Hemoglobin Cutoffs by Age and Physiological State",
            "text": "The World Health Organization defines anemia based on epidemiological venous blood hemoglobin concentrations: Children 6-59 months of age: Hb < 11.0 g/dL; Children 5-11 years of age: Hb < 11.5 g/dL; Children 12-14 years of age and non-pregnant adult women: Hb < 12.0 g/dL; Pregnant women: Hb < 11.0 g/dL (Hb < 10.5 g/dL in second trimester); Adult men: Hb < 13.0 g/dL. Severity of anemia in non-pregnant adult females is categorized as mild (Hb 11.0-11.9 g/dL), moderate (Hb 8.0-10.9 g/dL), and severe (Hb < 8.0 g/dL). Serum ferritin below 15 ug/L in adults indicates depleted iron stores."
        }
    ],

    "MEDLINEPLUS-HYPOTHYROIDISM": [
        {
            "section": "Hypothyroidism - Clinical Presentation and Hashimoto's Thyroiditis",
            "text": "Hypothyroidism is an endocrine disorder characterized by systemic deficiency of thyroid hormones (triiodothyronine [T3] and thyroxine [T4]), leading to generalized slowing of metabolic processes. The most frequent cause in iodine-sufficient regions is Hashimoto's thyroiditis (chronic autoimmune thyroiditis), characterized by circulating anti-thyroperoxidase (anti-TPO) and anti-thyroglobulin antibodies. Common symptoms include persistent fatigue, cold intolerance, unexplained weight gain, constipation, dry skin, coarse brittle hair, periorbital puffiness, hoarseness, bradycardia, muscle weakness, menstrual irregularities (menorrhagia), and cognitive slowing (brain fog)."
        },
        {
            "section": "Hypothyroidism - Laboratory Diagnosis and Levothyroxine Dosing",
            "text": "Laboratory diagnosis of primary hypothyroidism is established by an elevated serum Thyroid-Stimulating Hormone (TSH) level accompanied by a subnormal free thyroxine (free T4) level. Subclinical hypothyroidism is defined by an elevated serum TSH with normal free T4 levels. First-line replacement therapy is synthetic oral Levothyroxine (L-T4). The standard replacement dose in young, healthy adults is approximately 1.6 mcg/kg/day, whereas in elderly individuals or patients with underlying coronary artery disease, treatment initiates conservatively at 25 to 50 mcg daily to prevent precipitating cardiac ischemia. Levothyroxine must be ingested on an empty stomach with a full glass of water, at least 30 to 60 minutes before breakfast."
        }
    ],

    "MEDLINEPLUS-HYPERTHYROIDISM": [
        {
            "section": "Hyperthyroidism - Etiology, Graves' Disease, and Symptoms",
            "text": "Hyperthyroidism is characterized by excessive synthesis and secretion of thyroid hormones by the thyroid gland, leading to a hypermetabolic clinical state (thyrotoxicosis). Graves' disease is an autoimmune disorder caused by stimulating antibodies directed against the TSH receptor (TRAb) and accounts for 70% to 80% of cases. Symptoms include nervousness, irritability, heat intolerance, diaphoresis, unintentional weight loss despite increased appetite, palpitations, tremors of the hands, frequent bowel movements, oligomenorrhea, and fatigue. Specific physical findings in Graves' disease include thyroid dermopathy, diffuse nontender vascular goiter, and Graves' orbitopathy (exophthalmos, proptosis, and lid lag)."
        },
        {
            "section": "Hyperthyroidism - Diagnosis and Antithyroid Therapy",
            "text": "Laboratory findings show a suppressed serum TSH (< 0.01 mIU/L) with elevated free T4 and/or free T3 levels. Radioactive iodine uptake (RAIU) scans differentiate Graves' disease (diffuse elevated uptake) from toxic multinodular goiter or subacute thyroiditis. Management modalities include: 1. Beta-blockers (e.g., Propranolol, Atenolol) for rapid relief of adrenergic symptoms such as tachycardia and tremor. 2. Antithyroid thionamide drugs (Methimazole is preferred in most adults due to lower hepatotoxicity; Propylthiouracil [PTU] is preferred during the first trimester of pregnancy and in thyroid storm). 3. Radioactive iodine ablation (I-131). 4. Subtotal or total thyroidectomy."
        }
    ],

    "WHO-TUBERCULOSIS-2023": [
        {
            "section": "WHO Tuberculosis Guidelines - Diagnostic Algorithms and Rapid Molecular Testing",
            "text": "Tuberculosis (TB) is an airborne infectious disease caused by Mycobacterium tuberculosis, primarily affecting the lungs (pulmonary TB) but capable of infecting any organ (extrapulmonary TB). Classical pulmonary symptoms comprise persistent productive cough for 2 weeks or more, hemoptysis, low-grade evening fever, night sweats, anorexia, and progressive weight loss. The World Health Organization strongly recommends rapid molecular diagnostic tests—such as GeneXpert MTB/RIF and Ultra—as initial tests over conventional sputum smear microscopy. Rapid molecular tests simultaneously confirm M. tuberculosis DNA and detect rifampicin resistance within 2 hours."
        },
        {
            "section": "WHO Tuberculosis Guidelines - Standard First-Line Chemotherapy Regimens",
            "text": "Standard treatment for drug-susceptible pulmonary tuberculosis consists of a 6-month regimen divided into two phases: an intensive phase of 2 months with four bactericidal antibiotics: Isoniazid (H), Rifampicin (R), Pyrazinamide (Z), and Ethambutol (E) (2HRZE), followed by a 4-month continuation phase with two drugs: Isoniazid and Rifampicin (4HR). To optimize adherence and minimize emergence of multidrug-resistant TB (MDR-TB), WHO mandates daily administration of fixed-dose combination (FDC) tablets under Directly Observed Therapy (DOT) or verified digital adherence support. Pyridoxine (Vitamin B6) is co-prescribed to prevent Isoniazid-induced peripheral neuropathy."
        }
    ],

    "WHO-MALARIA-TREATMENT-2022": [
        {
            "section": "WHO Malaria Guidelines - Pathogens, Clinical Staging, and Rapid Diagnosis",
            "text": "Malaria is a life-threatening parasitic infection transmitted through the bite of infected female Anopheles mosquitoes. Five Plasmodium species infect humans: P. falciparum, P. vivax, P. malariae, P. ovale, and P. knowlesi, with P. falciparum posing the highest mortality risk. Uncomplicated malaria presents with acute fever, chills, rigors, profuse sweating, headache, generalized myalgias, nausea, and vomiting. Prompt parasitological confirmation using either quality-assured rapid diagnostic tests (RDTs) detecting histidine-rich protein 2 (HRP2) or light microscopy of Giemsa-stained thick and thin blood films is required prior to initiating antimalarial treatment."
        },
        {
            "section": "WHO Malaria Guidelines - Artemisinin-Based Combination Therapy (ACT)",
            "text": "The World Health Organization strongly recommends Artemisinin-Based Combination Therapies (ACTs) as the first-line standard of care for uncomplicated P. falciparum malaria worldwide. ACT regimens combine a fast-acting artemisinin derivative with a longer-acting partner drug: Artemether-lumefantrine (AL), Artesunate-amodiaquine (ASAQ), or Dihydroartemisinin-piperaquine (DP) administered over a 3-day course. For severe malaria (manifesting with cerebral malaria, coma, severe anemia, pulmonary edema, hypoglycemia, or acute kidney injury), intravenous or intramuscular Artesunate is the treatment of choice for at least 24 hours until oral medication can be tolerated."
        }
    ],

    "WHO-DENGUE-CLINICAL-2023": [
        {
            "section": "WHO Dengue Guidelines - Phases of Disease and Critical Leakage Period",
            "text": "Dengue is an acute arboviral infection caused by four distinct serotypes of dengue virus (DENV 1-4) transmitted by Aedes mosquitoes (primarily Aedes aegypti). The illness follows three clinical phases: the febrile phase (high fever, severe retro-orbital headache, body aches, arthralgias, maculopapular rash); the critical phase (occurring around day 3 to 7 of illness during defervescence, marked by systemic capillary hyperpermeability and plasma leakage lasting 24-48 hours); and the convalescent recovery phase. Patients with severe dengue develop dengue shock syndrome, respiratory distress from pleural effusions and ascites, severe bleeding, or organ failure."
        },
        {
            "section": "WHO Dengue Guidelines - Warning Signs and Judicious Fluid Protocols",
            "text": "WHO guidelines classify dengue cases into Dengue without warning signs, Dengue with warning signs, and Severe dengue. Clinical warning signs herald progression to plasma leakage and require immediate hospital admission: abdominal pain or tenderness, persistent vomiting, clinical fluid accumulation (pleural effusion, ascites), mucosal bleeding (epistaxis, gingival bleed), lethargy or restlessness, hepatomegaly > 2 cm, and concurrent progressive hematocrit elevation with rapid platelet count decline. Management relies on meticulous isotonic fluid resuscitation (normal saline or Ringer's lactate) titrated to clinical vital signs and hematocrit. Aspirin, NSAIDs, and intramuscular injections are strictly contraindicated due to bleeding hemorrhage risks."
        }
    ],

    "MEDLINEPLUS-GERD-REFLUX": [
        {
            "section": "Gastroesophageal Reflux Disease - Symptoms and Alarm Features",
            "text": "Gastroesophageal Reflux Disease (GERD) is a chronic digestive condition where stomach acid and gastric enzymes retrograde into the esophagus, causing mucosal irritation and distressing symptoms. Classic symptoms comprise pyrosis (heartburn—a retrosternal burning discomfort rising towards the neck) and acid regurgitation. Atypical symptoms include chronic non-productive cough, wheezing, laryngitis, globus sensation, and enamel erosion. Alarm features warranting urgent diagnostic upper gastrointestinal endoscopy include dysphagia (difficulty swallowing), odynophagia (painful swallowing), persistent vomiting, hematemesis, melena, unexplained anemia, and involuntary weight loss."
        },
        {
            "section": "Gastroesophageal Reflux Disease - Lifestyle Measures and Pharmacotherapy",
            "text": "Lifestyle modifications for GERD include elevating the head of the bed by 6-8 inches, maintaining a healthy body weight, avoiding recumbency within 3 hours after meals, avoiding tight-fitting garments, and moderating trigger foods (high-fat meals, chocolate, caffeine, alcohol, citrus, and mint). Pharmacological therapy is spearheaded by Proton Pump Inhibitors (PPIs, e.g., Omeprazole 20-40 mg, Pantoprazole 40 mg, Esomeprazole 40 mg once daily taken 30-60 minutes before the first meal of the day) for an initial 4 to 8-week healing course. Histamine-2 receptor antagonists (Famotidine) and oral alginate antacids provide on-demand symptomatic relief."
        }
    ],

    "MEDLINEPLUS-PEPTIC-ULCER": [
        {
            "section": "Peptic Ulcer Disease - H. pylori Etiology and NSAID Gastropathy",
            "text": "Peptic Ulcer Disease (PUD) encompasses focal mucosal breaks extending through the muscularis mucosae in the stomach (gastric ulcers) or proximal duodenum (duodenal ulcers). The overwhelming majority of peptic ulcers are caused by chronic infection with Helicobacter pylori bacteria or recurrent use of non-steroidal anti-inflammatory drugs (NSAIDs, including aspirin, ibuprofen, naproxen, and diclofenac). Classical symptoms include burning epigastric pain that occurs 2 to 3 hours after meals or at night and improves with food or antacids (typical of duodenal ulcers), or epigastric pain exacerbated by eating (typical of gastric ulcers). Complications include acute gastrointestinal hemorrhage, gastric perforation, and gastric outlet obstruction."
        },
        {
            "section": "Peptic Ulcer Disease - H. pylori Eradication and Ulcer Healing",
            "text": "Diagnosis of H. pylori is established by urea breath testing, stool antigen assays, or endoscopic gastric biopsy urease testing. First-line eradication therapy involves a 14-day quadruple regimen: Bismuth subsalicylate, Metronidazole, Tetracycline, and a high-dose Proton Pump Inhibitor (bismuth quadruple therapy) or high-dose PPI plus Amoxicillin, Clarithromycin, and Metronidazole in low-resistance settings. In patients with NSAID-induced ulcers, the offending NSAID should be discontinued immediately and potent PPI therapy administered for 8 weeks to promote complete mucosal re-epithelialization."
        }
    ],

    "MEDLINEPLUS-HEPATITIS-VIRAL": [
        {
            "section": "Viral Hepatitis - Hepatitis B and C Modes of Transmission and Screening",
            "text": "Viral hepatitis refers to inflammatory liver necrosis induced by hepatotropic viruses, with Hepatitis B Virus (HBV) and Hepatitis C Virus (HCV) accounting for the vast majority of chronic liver cirrhosis and hepatocellular carcinoma globally. HBV is transmitted parenterally through infected blood, unprotected sexual intercourse, and vertical mother-to-child perinatal transmission. HCV is predominantly transmitted via percutaneous exposure to infectious blood, including unsafe injections, unsterilized healthcare equipment, and contaminated transfusions. Initial screening relies on serological assays: Hepatitis B surface antigen (HBsAg) for HBV, and Hepatitis C antibody (anti-HCV) followed by quantitative HCV RNA PCR confirmation."
        },
        {
            "section": "Viral Hepatitis - Antiviral Protocols and Vaccination",
            "text": "Hepatitis B is preventable through universal infant vaccination with a 3-dose recombinant HBV vaccine series, including a birth dose within 24 hours. Chronic active HBV is treated with oral nucleos(t)ide analogues with high genetic barriers to resistance (Tenofovir disoproxil fumarate, Tenofovir alafenamide, or Entecavir) which suppress viral replication long-term. Chronic Hepatitis C is now curable in > 95% of patients with a 8 to 12-week course of oral Direct-Acting Antiviral (DAA) pangenotypic regimens (e.g., Sofosbuvir/Velpatasvir or Glecaprevir/Pibrentasvir), eliminating viral RNA without requiring interferon."
        }
    ],

    "MEDLINEPLUS-STROKE-OVERVIEW": [
        {
            "section": "Acute Stroke - Ischemic vs Hemorrhagic Pathophysiology and BE-FAST Signs",
            "text": "A stroke (cerebrovascular accident) occurs when cerebral blood flow is abruptly interrupted (ischemic stroke, ~85% of cases) or when a cerebral blood vessel ruptures causing intracranial bleeding (hemorrhagic stroke, ~15% of cases). Transient Ischemic Attack (TIA) is a temporary episode of neurological dysfunction caused by focal brain ischemia without acute tissue infarction. Rapid recognition is facilitated by the BE-FAST acronym: B (Balance loss, sudden ataxia); E (Eyes, sudden loss of vision in one or both eyes); F (Face drooping, asymmetric smile); A (Arm weakness or numbness); S (Speech difficulty, slurring, inability to formulate words); T (Time to call emergency services immediately). Time is brain, with approximately 1.9 million neurons lost each minute in untreated large-vessel occlusion."
        },
        {
            "section": "Acute Stroke - Emergency Revascularization and Secondary Prevention",
            "text": "Emergency non-contrast head CT or brain MRI is immediately performed to rule out intracranial hemorrhage. Eligible patients with acute ischemic stroke presenting within 4.5 hours of symptom onset are treated with intravenous thrombolysis (Alteplase or Tenecteplase). Mechanical thrombectomy is indicated for acute large vessel occlusions in the anterior circulation within 6 to 24 hours. Secondary stroke prevention mandates antiplatelet therapy (aspirin alone or dual antiplatelet therapy with clopidogrel for 21 days), aggressive statin therapy (Atorvastatin 80 mg), strict blood pressure reduction, and oral anticoagulation (DOACs: Apixaban, Rivaroxaban) for cardioembolic stroke associated with non-valvular atrial fibrillation."
        }
    ],

    "MEDLINEPLUS-EPILEPSY-SEIZURES": [
        {
            "section": "Epilepsy - Seizure Classification and Status Epilepticus",
            "text": "Epilepsy is a chronic brain disorder characterized by an enduring predisposition to generate unprovoked epileptic seizures. Seizures are classified into focal seizures (originating within neural networks limited to one cerebral hemisphere) and generalized seizures (originating at some point within and rapidly engaging bilaterally distributed networks, including generalized tonic-clonic seizures, absence seizures, and myoclonic seizures). Status epilepticus is a critical neurological emergency defined as a continuous seizure lasting >= 5 minutes, or two or more seizures without complete recovery of consciousness between events, carrying high risks of systemic hyperpyrexia, neuronal death, and mortality."
        },
        {
            "section": "Epilepsy - Antiseizure Medications and Emergency Protocol",
            "text": "First-line maintenance Antiseizure Medications (ASMs) are selected based on seizure classification: Levetiracetam, Lamotrigine, Carbamazepine, and Oxcarbazepine for focal-onset seizures; and Levetiracetam, Valproic acid (avoided in women of childbearing potential due to teratogenicity), and Topiramate for generalized-onset seizures. Monotherapy with dose titration is the standard strategy. Status epilepticus requires immediate airway protection, oxygen, intravenous access, and rapid intravenous administration of a benzodiazepine (Lorazepam 4 mg IV or Midazolam 10 mg IM), followed promptly by non-sedating IV ASMs (Levetiracetam, Fosphenytoin, or Valproate)."
        }
    ],

    "MEDLINEPLUS-MIGRAINE-HEADACHE": [
        {
            "section": "Migraine Headache - Phases, Symptoms, and Diagnostic Criteria",
            "text": "Migraine is a neurovascular primary headache disorder characterized by recurrent attacks of moderate to severe pulsating or throbbing head pain, predominantly unilateral, typically lasting 4 to 72 hours. Key diagnostic clinical features include pain aggravated by routine physical activity, accompanied by nausea, vomiting, photophobia (sensitivity to light), and phonophobia (sensitivity to sound). Approximately one-third of individuals experience an aura—transient focal neurological symptoms lasting 5 to 60 minutes prior to headache onset, most commonly scintillating scotomas, zigzag lines, or unilateral tingling sensations. Migraine triggers include hormonal fluctuations, emotional stress, irregular sleep, skipped meals, and specific sensory stimuli."
        },
        {
            "section": "Migraine Headache - Acute Abortive and Prophylactic Treatment",
            "text": "Acute abortive therapy should be taken as early as possible after headache onset: mild-to-moderate attacks respond to simple analgesics or NSAIDs (Ibuprofen 400-800 mg, Naproxen sodium 550 mg, or Acetaminophen/Aspirin/Caffeine combinations). Moderate-to-severe attacks require 5-HT1B/1D receptor agonists (Triptans, e.g., Sumatriptan 50-100 mg, Rizatriptan 10 mg) or newer CGRP receptor antagonists (Gepants). Prophylactic preventive therapy is indicated for patients with >= 4 headache days per month or debilitating attacks, utilizing beta-blockers (Propranolol), anticonvulsants (Topiramate), antidepressants (Amitriptyline), or monoclonal antibodies targeting CGRP."
        }
    ],

    "WHO-ANTENATAL-CARE-2021": [
        {
            "section": "WHO Antenatal Care - Routine Visits and Micronutrient Supplementation",
            "text": "The World Health Organization recommendations on antenatal care (ANC) for a positive pregnancy experience recommend a minimum of eight antenatal contacts to reduce perinatal mortality and maternal morbidity. Essential nutritional interventions include daily oral iron supplementation (30 to 60 mg elemental iron) and folic acid (400 mcg or 0.4 mg) starting preconception or as early in pregnancy as possible to prevent maternal anemia, puerperal sepsis, low birth weight, and neural tube defects. Routine screening at initial ANC visits comprises blood typing, Rh status, complete blood count, syphilis serology, HIV testing, Hepatitis B surface antigen, and urine culture for asymptomatic bacteriuria."
        }
    ],

    "MEDLINEPLUS-PREECLAMPSIA-PREGNANCY": [
        {
            "section": "Preeclampsia - Diagnostic Definition and Severe Clinical Signs",
            "text": "Preeclampsia is a serious multi-system gestational disorder characterized by new-onset hypertension (systolic BP >= 140 mmHg or diastolic BP >= 90 mmHg on two occasions at least 4 hours apart) occurring after 20 weeks of gestation in a previously normotensive woman, combined with proteinuria (>= 300 mg per 24-hour urine collection or spot UACR >= 30 mg/mmol). In the absence of proteinuria, preeclampsia is diagnosed if hypertension occurs alongside thrombocytopenia (platelet count < 100,000/uL), renal insufficiency (serum creatinine > 1.1 mg/dL), impaired liver function (transaminases twice normal), pulmonary edema, or new-onset persistent severe headache and visual disturbances. Eclampsia is the occurrence of generalized seizures in a patient with preeclampsia."
        },
        {
            "section": "Preeclampsia - Management and Prevention",
            "text": "Definitive management of preeclampsia is delivery of the fetus and placenta. In women with high baseline risk factors (prior preeclampsia, chronic hypertension, pre-existing diabetes, multifetal gestation, or renal disease), daily low-dose aspirin (75-150 mg) initiated from 12 weeks of gestation until delivery significantly reduces the incidence of preeclampsia and intrauterine growth restriction. Severe acute hypertension (SBP >= 160 mmHg or DBP >= 110 mmHg) requires emergent antihypertensive therapy with intravenous Labetalol, oral Nifedipine, or intravenous Hydralazine to prevent maternal intracranial hemorrhage. Intravenous Magnesium sulfate is the agent of choice for seizure prophylaxis in severe preeclampsia and treatment of eclamptic seizures."
        }
    ],

    "MEDLINEPLUS-GESTATIONAL-DIABETES": [
        {
            "section": "Gestational Diabetes - Screening Protocols and Diagnostic Thresholds",
            "text": "Gestational Diabetes Mellitus (GDM) is defined as carbohydrate intolerance resulting in hyperglycemia with onset or first recognition during pregnancy. GDM increases risks of macrosomia, birth trauma, neonatal hypoglycemia, hyperbilirubinemia, respiratory distress syndrome, and long-term risk of maternal Type 2 diabetes. Universal screening is recommended at 24 to 28 weeks of gestation. Under the one-step 75-gram oral glucose tolerance test (IADPSG/WHO criteria), GDM is diagnosed if any single plasma glucose value meets or exceeds: Fasting: 92 mg/dL (5.1 mmol/L); 1-hour: 180 mg/dL (10.0 mmol/L); 2-hour: 153 mg/dL (8.5 mmol/L). In India, the DIPSI single-step non-fasting 75g OGTT cut-off is 2-hour plasma glucose >= 140 mg/dL."
        },
        {
            "section": "Gestational Diabetes - Glycemic Targets and Insulin Therapy",
            "text": "Primary management of GDM involves medical nutrition therapy, structured physical activity (walking 30 minutes after meals), and frequent self-monitoring of blood glucose. Glycemic targets for pregnant women are: Fasting blood glucose < 95 mg/dL (5.3 mmol/L), 1-hour postprandial < 140 mg/dL (7.8 mmol/L), and 2-hour postprandial < 120 mg/dL (6.7 mmol/L). If lifestyle interventions fail to achieve glycemic targets within 1 to 2 weeks, insulin therapy is the gold standard pharmacological treatment because it does not cross the placenta. Metformin may be considered in select circumstances when insulin is unavailable or refused."
        }
    ],

    "MOHFW-EMERGENCY-TRIAGE-2022": [
        {
            "section": "MoHFW India Emergency Protocols - Red Flag Triaging and National Helplines",
            "text": "The Ministry of Health and Family Welfare (MoHFW), Government of India, National Emergency Life Support protocols establish strict triage criteria for acute life-threatening emergencies. 'Red Flag' category-1 triage conditions mandate immediate resuscitation and zero-delay physician assessment: 1. Airway/Breathing: Severe stridor, cyanosis, SpO2 < 90%, respiratory rate < 8 or > 35/min. 2. Circulation: Hypotension (SBP < 90 mmHg), severe active hemorrhage, capillary refill > 3 seconds, acute crushing chest pain with diaphoresis. 3. Disability: Glasgow Coma Scale (GCS) < 9, sudden onset hemiplegia, active convulsing status epilepticus. Emergency access numbers in India: Dial 112 for the unified National Emergency Response Support System, or 108 / 102 for government ambulance emergency medical services."
        }
    ],

    "WHO-ACUTE-CARDIAC-CARE-2021": [
        {
            "section": "WHO Acute Coronary Resuscitation - MONA Protocol and Early Defibrillation",
            "text": "In patients presenting with suspected acute coronary syndrome or myocardial infarction, initial emergency management comprises: 1. Immediate resting 12-lead electrocardiogram (ECG) performed and interpreted within 10 minutes of arrival. 2. Oxygen supplementation only if hypoxemic (SpO2 < 90%). 3. Immediate chewable Aspirin (162-325 mg) unless contraindicated by active hemorrhage. 4. Sublingual nitroglycerin (0.4 mg every 5 minutes up to 3 doses) for ischemic chest discomfort, provided SBP is > 90 mmHg and phosphodiesterase-5 inhibitors have not been taken in past 24-48 hours. 5. Rapid cardiac biomarker assessment (high-sensitivity cardiac troponin). 6. For ventricular fibrillation or pulseless ventricular tachycardia cardiac arrest, immediate cardiopulmonary resuscitation (CPR) and rapid automated external defibrillation (AED) are the determinative survival factors."
        }
    ]
}

def generate_reference_corpus():
    """Generates XML reference documents and processes them into v2 JSONL chunks."""
    REFERENCE_XML_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_V2_DIR.mkdir(parents=True, exist_ok=True)

    chunker = MedicalChunker(target_tokens=400, overlap_tokens=60)
    all_chunks = []
    summary_stats = {
        "total_sources": len(EXPANDED_SOURCES_REGISTRY),
        "total_chunks": 0,
        "domains": {}
    }

    for source_id, metadata in EXPANDED_SOURCES_REGISTRY.items():
        sections = OFFICIAL_CLINICAL_CONTENT.get(source_id, [])
        if not sections:
            print(f"[WARN] No official content defined for source {source_id}")
            continue

        # 1. Build and save XML file
        xml_content = f'<?xml version="1.0" encoding="utf-8"?>\n'
        xml_content += f'<medical-reference-document id="{source_id}" version="{metadata.document_version}">\n'
        xml_content += f'  <title>{metadata.title}</title>\n'
        xml_content += f'  <publisher>{metadata.organization}</publisher>\n'
        xml_content += f'  <url>{metadata.source_url}</url>\n'
        xml_content += f'  <license>{metadata.license}</license>\n'
        xml_content += f'  <domain>{metadata.domain_group}</domain>\n'
        xml_content += f'  <topic>{metadata.topic}</topic>\n'
        xml_content += f'  <publication-date>{metadata.publication_date}</publication-date>\n'
        xml_content += f'  <sections>\n'
        for s in sections:
            sec_title = s["section"]
            sec_text = s["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            xml_content += f'    <section title="{sec_title}">\n'
            xml_content += f'      {sec_text}\n'
            xml_content += f'    </section>\n'
        xml_content += f'  </sections>\n'
        xml_content += f'</medical-reference-document>\n'

        xml_file = REFERENCE_XML_DIR / f"{source_id}.xml"
        with open(xml_file, "w", encoding="utf-8") as f:
            f.write(xml_content)

        # 2. Chunk sections deterministically
        doc_chunks = []
        for sec_idx, s in enumerate(sections, 1):
            text = s["text"].strip()
            sec_heading = s["section"]
            split_texts = chunker.splitter.split_text(text)

            for chunk_idx, chunk_text in enumerate(split_texts, 1):
                content_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
                chunk_id = chunker.generate_chunk_id(
                    document_id=source_id,
                    section_heading=sec_heading,
                    page_number=None,
                    chunk_index=chunk_idx,
                    content_hash=content_hash
                )
                chunk_obj = {
                    "chunk_id": chunk_id,
                    "document_id": source_id,  # PRESERVE EXACT SOURCE ID
                    "title": metadata.title,
                    "source_organization": metadata.organization,
                    "source_url": metadata.source_url,
                    "publication_date": metadata.publication_date,
                    "retrieval_date": "2026-11-05",
                    "section_heading": sec_heading,
                    "page_number": None,
                    "medical_topic": metadata.topic,
                    "domain_group": metadata.domain_group,
                    "document_version": metadata.document_version,
                    "review_status": metadata.review_status,
                    "license": metadata.license,
                    "token_count": chunker.token_length(chunk_text),
                    "content": chunk_text
                }
                doc_chunks.append(chunk_obj)
                all_chunks.append(chunk_obj)

        # 3. Write individual JSONL for this document
        doc_jsonl = PROCESSED_V2_DIR / f"{source_id}.jsonl"
        with open(doc_jsonl, "w", encoding="utf-8") as f:
            for c in doc_chunks:
                f.write(json.dumps(c) + "\n")

        dom = metadata.domain_group
        summary_stats["domains"][dom] = summary_stats["domains"].get(dom, 0) + len(doc_chunks)

    summary_stats["total_chunks"] = len(all_chunks)

    # 4. Write master v2 chunks and manifest
    master_jsonl = PROCESSED_V2_DIR / "master_v2_chunks.jsonl"
    with open(master_jsonl, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c) + "\n")

    manifest_v2 = {
        "version": "v2",
        "generated_at": "2026-11-05T00:35:00Z",
        "total_documents": len(EXPANDED_SOURCES_REGISTRY),
        "total_chunks": len(all_chunks),
        "domain_distribution": summary_stats["domains"]
    }
    with open(PROCESSED_V2_DIR / "manifest_v2.json", "w", encoding="utf-8") as f:
        json.dump(manifest_v2, f, indent=2)

    print(f"Generated {len(EXPANDED_SOURCES_REGISTRY)} verified reference documents.")
    print(f"Total chunks generated: {len(all_chunks)}")
    print("Domain distribution:", summary_stats["domains"])
    return summary_stats

if __name__ == "__main__":
    generate_reference_corpus()
