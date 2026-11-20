import os
from typing import Any
class AIService:
    """Optional OpenAI draft generation with a deterministic offline fallback."""
    def __init__(self):
        self.api_key=os.getenv('OPENAI_API_KEY','').strip(); self.model=os.getenv('OPENAI_MODEL','gpt-4o-mini'); self.provider='openai' if self.api_key and os.getenv('AI_PROVIDER','openai').lower()=='openai' else 'demo'
    def structure_summary(self,patient:dict,answers:dict[str,Any],documents:list[str]|None=None)->str:
        docs='\n\n'.join(documents or []) or 'No extracted text available.'
        if self.provider=='openai':
            try:
                from openai import OpenAI
                client=OpenAI(api_key=self.api_key)
                r=client.chat.completions.create(model=self.model,temperature=0.1,messages=[
                 {'role':'system','content':'You are a clinical documentation assistant, not a diagnostic system. Use only supplied facts, do not infer diagnoses or treatment, mark unknowns Not provided, distinguish patient-reported facts from unverified OCR, and require clinician review.'},
                 {'role':'user','content':f'Patient: {patient}\nAnswers: {answers}\nUnverified OCR text: {docs}\nCreate sections: chief complaint, present illness, medical/surgical history, medicines, allergies, family/personal history, review of systems, document findings (unverified), missing details to verify, clinician review note.'}])
                return 'AI-GENERATED CLINICAL INTAKE SUMMARY (DRAFT FOR PHYSICIAN REVIEW)\n\n'+(r.choices[0].message.content or '')+'\n\nNOT A DIAGNOSIS. Verify every detail before clinical use.'
            except Exception as exc: print(f'AI provider unavailable; using fallback ({type(exc).__name__}).')
        fields=[('Chief complaint','chief_complaint'),('History of present illness','hpi'),('Past medical history','past_medical_history'),('Past surgical history','past_surgical_history'),('Current medications','medications'),('Allergies and reactions','allergies'),('Family history','family_history'),('Personal history','personal_history'),('Review of systems','review_of_systems')]
        body='\n\n'.join(f'{label}:\n{answers.get(key) or "Not provided"}' for label,key in fields)
        return f'CLINICAL INTAKE SUMMARY (DRAFT FOR PHYSICIAN REVIEW)\nPatient: {patient.get("name")} | Age: {patient.get("age")} | Gender: {patient.get("gender")}\nPreferred language: {patient.get("language")}\n\n{body}\n\nUploaded-document text (unverified OCR):\n{docs}\n\nVerification checklist: verify OCR text against original reports, confirm dates/units/medicines, ask about missing details.\n\nNOT A DIAGNOSIS OR TREATMENT RECOMMENDATION. Physician review is mandatory.'
