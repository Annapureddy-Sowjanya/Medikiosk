import re

QUESTION_ONTOLOGY = {
  "default": [
    {"id":"hpi", "label":"Tell us more about the problem: when it started, where you feel it, how severe it is, and what makes it better or worse.", "type":"textarea"},
    {"id":"past_medical_history", "label":"Do you have any past medical conditions (for example diabetes, high blood pressure, asthma, or kidney disease)?", "type":"textarea"},
    {"id":"past_surgical_history", "label":"Have you had any surgeries or hospital admissions before?", "type":"textarea"},
    {"id":"medications", "label":"What medicines or supplements are you currently taking? Include dose if known.", "type":"textarea"},
    {"id":"allergies", "label":"Do you have any medicine, food, or other allergies? What reaction occurs?", "type":"textarea"},
    {"id":"family_history", "label":"Are there important health conditions in your close family?", "type":"textarea"},
    {"id":"personal_history", "label":"Tell us about diet, sleep, occupation, physical activity, smoking or alcohol, if relevant.", "type":"textarea"},
    {"id":"review_of_systems", "label":"Any other symptoms involving breathing, heart, digestion, nerves, urination, muscles, or general health?", "type":"textarea"}
  ],
  "fever": [
    {"id":"hpi", "label":"Since when have you had fever? If measured, what was the highest temperature?", "type":"textarea"},
    {"id":"fever_associated", "label":"Do you also have chills, cough, sore throat, body pain, recent travel, or contact with someone unwell?", "type":"textarea"}
  ],
  "abdominal": [
    {"id":"hpi", "label":"Where is the abdominal pain, when did it start, how severe is it, and what affects it?", "type":"textarea"},
    {"id":"abdominal_associated", "label":"Any vomiting, diarrhea, constipation, blood in stool, or fever?", "type":"textarea"}
  ],
  "chest": [
    {"id":"hpi", "label":"Describe the chest discomfort, when it started, severity, whether it spreads, and what makes it better or worse.", "type":"textarea"},
    {"id":"chest_associated", "label":"Do you have breathlessness, sweating, dizziness, nausea, or fainting along with it?", "type":"textarea"}
  ]
}

def questions_for(complaint: str):
    text = (complaint or "").lower()
    if any(k in text for k in ["chest", "heart pain", "chest pain"]):
        return QUESTION_ONTOLOGY["chest"] + QUESTION_ONTOLOGY["default"][1:]
    if any(k in text for k in ["fever", "temperature", "hot"]):
        return QUESTION_ONTOLOGY["fever"] + QUESTION_ONTOLOGY["default"][1:]
    if any(k in text for k in ["stomach", "abdomen", "abdominal", "tummy"]):
        return QUESTION_ONTOLOGY["abdominal"] + QUESTION_ONTOLOGY["default"][1:]
    return QUESTION_ONTOLOGY["default"]

RED_FLAG_RULES = [
    (r"\b(severe chest pain|crushing chest pain|chest pain with breathlessness)\b", "Severe chest pain or chest pain with breathlessness"),
    (r"\b(sudden weakness|face droop|facial drooping|difficulty speaking|slurred speech)\b", "Possible sudden neurological emergency symptoms"),
    (r"\b(severe difficulty breathing|cannot breathe|can't breathe|gasping)\b", "Severe difficulty breathing"),
    (r"\b(loss of consciousness|unconscious|fainted and not waking)\b", "Loss of consciousness"),
    (r"\b(severe bleeding|bleeding heavily|uncontrolled bleeding)\b", "Severe or uncontrolled bleeding"),
    (r"\b(seizure|convulsion|fits)\b", "Seizure or convulsion"),
    (r"\b(severe allergic reaction|throat swelling|tongue swelling|anaphylaxis)\b", "Possible severe allergic reaction")
]

def detect_red_flags(text: str):
    found = []
    for pattern, label in RED_FLAG_RULES:
        if re.search(pattern, text or "", re.IGNORECASE):
            found.append(label)
    return found
