# faq_data.py

def policies_and_procedures():
    return [
        {
            "question": "Where can I find the most up-to-date version of a specific hospital policy?",
            "answer": "Our hospital maintains an online repository for all active policies and procedures, accessible through the intranet. Look for the 'Policy and Procedure Manual' or 'Clinical Resources' section. You can search by keyword, policy number, or department. If you can't find what you're looking for, contact your department manager or the Policy Committee."
        },
        {
            "question": "What is the procedure for reporting a deviation from a policy or procedure?",
            "answer": "If you witness or become aware of a deviation from a policy or procedure that could potentially compromise patient safety or quality of care, you are required to report it. The preferred method is through our incident reporting system (e.g., RL Solutions, Quantros), accessible through the intranet. You can also report it directly to your supervisor or the Risk Management department. We have a non-punitive reporting culture, so you will not be penalized for reporting in good faith."
        },
        {
            "question": "If a policy seems outdated or impractical, what's the process for suggesting a revision?",
            "answer": "We encourage staff to provide feedback on policies. There is a dedicated form on the intranet's Policy and Procedure page to submit suggested revisions. Your suggestion will be reviewed by the relevant policy committee. You will receive feedback on the status of your suggestion."
        },
        {
            "question": "What are the key policies I need to know regarding patient privacy and HIPAA?",
            "answer": "The most important policies to review are the 'Confidentiality and Privacy of Patient Information' policy, the 'Social Media Use' policy, and the 'Electronic Health Record (EHR) Access and Security' policy. These outline how to protect patient information and comply with HIPAA regulations. Annual HIPAA training is mandatory."
        },
        {
            "question": "What's the hospital's policy on mandatory overtime and call schedules?",
            "answer": "The 'Staffing and Scheduling' policy addresses staffing ratios, on-call requirements, fair distribution of overtime, and procedures for declining overtime. This aligns with state regulations and any collective bargaining agreements."
        },
        {
            "question": "What is the policy on patient identification and medication administration verification?",
            "answer": "Always adhere to the Two-Patient-Identifier policy. Confirm both the patient’s full name and date of birth before any medication is administered. Verify against the ID band, medical record, or EMR to prevent errors."
        }
    ]

def medication_interaction():
    return [
        {
            "question": "The electronic prescribing system flagged a potential interaction, but I don't think it's clinically significant. What should I do?",
            "answer": "Never disregard an alert completely. If you believe the interaction is not clinically significant, consult with the prescribing physician and clinical pharmacist. Document the discussion and rationale in the patient record."
        },
        {
            "question": "What resources can I use to quickly check for medication interactions outside of the electronic prescribing system?",
            "answer": "Use the hospital-approved references like Lexicomp or Micromedex available on nursing units. You may also contact the on-call pharmacist. Do NOT use unverified online sources."
        },
        {
            "question": "What is the hospital's policy on administering medications brought in by patients from home?",
            "answer": "Use of patient-supplied medications must be authorized by the prescribing physician. These medications must be labeled, verified by pharmacy, securely stored, and documented in the patient’s profile according to the 'Medication Management' policy."
        },
        {
            "question": "What are the procedures for administering high-alert medications (e.g., insulin, heparin, opioids)?",
            "answer": "High-alert medications require independent double-checks by two qualified nurses. This includes confirming the drug, dose, route, timing, and patient identification prior to administration."
        },
        {
            "question": "How do I document medication administration, including any reactions or interactions?",
            "answer": "Document drug name, dose, route, time, and site in the EHR promptly. For adverse reactions, include detailed symptoms, vital signs, interventions, and notify the physician and pharmacy immediately."
        },
        {
            "question": "What action needs to be taken if the doctor has given an incorrect dose for a specific patient?",
            "answer": "Contact the doctor immediately upon identifying the error. Escalate to the charge nurse or higher authority if necessary to ensure correction."
        }
    ]

def clinical_pathways():
    return [
        {
            "question": "How do I access the clinical pathway for a specific condition?",
            "answer": "Clinical pathways are available in the EHR under the 'Clinical Pathway' section. You can search by condition name or ICD-10 code. Paper copies may be available in select units, but EHR is the primary source."
        },
        {
            "question": "What if a patient on a clinical pathway refuses a specific intervention (e.g., physical therapy)?",
            "answer": "Respect patient autonomy. Document the refusal, the reason, and any education provided. Notify the physician and discuss alternative options."
        },
        {
            "question": "The clinical pathway doesn't seem to address a specific co-morbidity the patient has. Should I deviate from the pathway?",
            "answer": "Yes, when clinically justified. Consult with the physician or specialist. Document the deviation and rationale clearly in the patient chart."
        },
        {
            "question": "How often are clinical pathways reviewed and updated?",
            "answer": "They are reviewed at least annually or sooner if prompted by changes in evidence-based guidelines. The Clinical Practice Committee oversees this process."
        },
        {
            "question": "What are the benefits of using clinical pathways in my daily practice?",
            "answer": "They promote evidence-based care, reduce complications, improve outcomes, and enhance team coordination. Clinical pathways also streamline workflow and documentation."
        },
        {
            "question": "What is the hospital policy if a clinical pathway is not followed?",
            "answer": "Deviations must be justified with valid clinical reasoning and documented. Unexplained deviations may be subject to review or audit by clinical leadership."
        }
    ]
