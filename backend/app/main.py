from fastapi import FastAPI,Depends,HTTPException,UploadFile,File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc,func
from pathlib import Path
from datetime import datetime,timezone
from io import BytesIO
import json,shutil,os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
from reportlab.lib.styles import getSampleStyleSheet
from .database import Base,engine,get_db
from . import models,schemas
from .ai_service import AIService
from .ocr_service import extract_text
from .security import hash_password,verify_password,create_access_token,current_user,require_roles
from .question_engine import questions_for,detect_red_flags
Base.metadata.create_all(bind=engine)
app=FastAPI(title='MediKiosk API',version='1.0.0',description='Educational clinical intake prototype. AI summaries are drafts requiring physician review.')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','),allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
ai_service=AIService(); UPLOAD_DIR=Path(__file__).resolve().parent.parent/'uploads'; UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
def session_or_404(db, sid):
 s=db.query(models.IntakeSession).filter(models.IntakeSession.id==sid).first()
 if not s: raise HTTPException(404,'Intake session not found')
 return s
def patient_dict(p):
 return {'id':p.id,'name':p.name,'age':p.age,'gender':p.gender,'mobile':p.mobile,'abha_id':p.abha_id,'language':p.language}
def audit(db,event,session_id=None,user=None,details=''):
 db.add(models.AuditEvent(event_type=event,session_id=session_id,user_id=getattr(user,'id',None),details=details[:1000])); db.commit()
@app.get('/')
def root(): return {'name':'MediKiosk API','status':'running','ai_provider':ai_service.provider,'database':'configured via DATABASE_URL','safety':'Draft summaries require physician review.'}
@app.get('/api/health')
def health(): return {'status':'ok'}
@app.post('/api/auth/register')
def register(payload:schemas.RegisterInput,db:Session=Depends(get_db)):
 if db.query(models.User).filter(models.User.email==payload.email.lower()).first(): raise HTTPException(409,'Email already registered')
 count=db.query(models.User).count()
 if count: raise HTTPException(403,'Public registration is closed after the first account. Ask an administrator to create staff accounts.')
 if payload.role not in ('admin','physician','staff'): raise HTTPException(400,'Role must be admin, physician, or staff')
 role='admin' if count==0 else payload.role
 u=models.User(email=payload.email.lower(),full_name=payload.full_name,password_hash=hash_password(payload.password),role=role)
 db.add(u);db.commit();db.refresh(u)
 return {'message':'Account created','user':{'id':u.id,'email':u.email,'full_name':u.full_name,'role':u.role},'access_token':create_access_token(u),'token_type':'bearer','warning':'Prototype authentication. Configure a strong JWT_SECRET and production identity controls before deployment.'}
@app.post('/api/auth/login')
def login(payload:schemas.LoginInput,db:Session=Depends(get_db)):
 u=db.query(models.User).filter(models.User.email==payload.email.lower()).first()
 if not u or not u.active or not verify_password(payload.password,u.password_hash): raise HTTPException(401,'Incorrect email or password')
 audit(db,'login',user=u,details='Successful login')
 return {'access_token':create_access_token(u),'token_type':'bearer','user':{'id':u.id,'email':u.email,'full_name':u.full_name,'role':u.role}}
@app.get('/api/auth/me')
def me(user=Depends(current_user)): return {'id':user.id,'email':user.email,'full_name':user.full_name,'role':user.role}
@app.post('/api/auth/users')
def create_staff(payload:schemas.RegisterInput,db:Session=Depends(get_db),admin=Depends(require_roles('admin'))):
 if db.query(models.User).filter(models.User.email==payload.email.lower()).first(): raise HTTPException(409,'Email already registered')
 if payload.role not in ('physician','staff'): raise HTTPException(400,'Only physician or staff roles can be provisioned')
 u=models.User(email=payload.email.lower(),full_name=payload.full_name,password_hash=hash_password(payload.password),role=payload.role);db.add(u);db.commit();db.refresh(u);audit(db,'staff_account_created',user=admin,details=f'role={u.role}');return {'id':u.id,'email':u.email,'full_name':u.full_name,'role':u.role}
@app.post('/api/patients')
def create_patient(payload:schemas.PatientCreate,db:Session=Depends(get_db)):
 p=models.Patient(**payload.model_dump());db.add(p);db.commit();db.refresh(p)
 s=models.IntakeSession(patient_id=p.id);db.add(s);db.commit();db.refresh(s)
 next_num=(db.query(func.max(models.QueueEntry.queue_number)).scalar() or 0)+1
 db.add(models.QueueEntry(session_id=s.id,queue_number=next_num,status='Waiting'));db.commit()
 return {'patient':patient_dict(p),'session_id':s.id,'queue_number':next_num}
@app.get('/api/patients')
def list_patients(db:Session=Depends(get_db),user=Depends(require_roles('admin','physician','staff'))):
 return [patient_dict(p) for p in db.query(models.Patient).order_by(desc(models.Patient.id)).limit(100).all()]
@app.get('/api/sessions/{session_id}')
def get_session(session_id:int,db:Session=Depends(get_db)):
 s=session_or_404(db,session_id);p=db.query(models.Patient).filter(models.Patient.id==s.patient_id).first()
 return {'id':s.id,'patient':patient_dict(p),'consent_given':s.consent_given,'consent_revoked':s.consent_revoked,'answers':json.loads(s.answers_json or '{}'),'summary':s.summary_draft,'physician_notes':s.physician_notes,'physician_status':s.physician_status,'red_flags':json.loads(s.red_flags_json or '[]')}
@app.post('/api/sessions/{session_id}/consent')
def set_consent(session_id:int,payload:schemas.ConsentInput,db:Session=Depends(get_db)):
 s=session_or_404(db,session_id);s.consent_given=payload.agreed;s.consent_revoked=not payload.agreed;s.consent_timestamp=datetime.now(timezone.utc) if payload.agreed else None;s.consent_version=payload.version;db.commit()
 return {'consent_given':s.consent_given,'consent_revoked':s.consent_revoked,'version':s.consent_version}
@app.post('/api/sessions/{session_id}/revoke-consent')
def revoke_consent(session_id:int,payload:schemas.RevokeInput,db:Session=Depends(get_db)):
 s=session_or_404(db,session_id);s.consent_given=False;s.consent_revoked=True;db.commit();return {'message':'Consent revoked for this demo session. Follow hospital policy for retention/deletion.','consent_given':False}
@app.get('/api/questions')
def get_questions(complaint:str=''): return {'questions':questions_for(complaint)}
@app.post('/api/sessions/{session_id}/answers')
def save_answers(session_id:int,payload:schemas.AnswerInput,db:Session=Depends(get_db)):
 s=session_or_404(db,session_id)
 if not s.consent_given or s.consent_revoked: raise HTTPException(403,'Active consent is required before collecting clinical information.')
 answers=json.loads(s.answers_json or '{}');answers.update(payload.answers or {})
 if payload.question_id: answers[payload.question_id]=payload.answer
 flags=detect_red_flags(' '.join(str(v) for v in answers.values()));s.answers_json=json.dumps(answers,ensure_ascii=False);s.red_flags_json=json.dumps(flags,ensure_ascii=False);db.commit()
 return {'answers':answers,'red_flags':flags,'urgent_attention':bool(flags)}
@app.post('/api/sessions/{session_id}/documents')
async def upload_document(session_id:int,file:UploadFile=File(...),db:Session=Depends(get_db)):
 s=session_or_404(db,session_id)
 if not s.consent_given or s.consent_revoked: raise HTTPException(403,'Active consent is required before uploading documents.')
 safe_name=Path(file.filename or 'upload.bin').name
 if Path(safe_name).suffix.lower() not in {'.pdf','.png','.jpg','.jpeg','.webp','.tif','.tiff'}: raise HTTPException(415,'Upload a PDF or supported image file.')
 data=await file.read()
 if not data: raise HTTPException(400,'Uploaded file is empty')
 if len(data)>10*1024*1024: raise HTTPException(413,'Maximum upload size is 10 MB')
 target=UPLOAD_DIR/f'session_{session_id}_{int(datetime.now().timestamp())}_{safe_name}'
 target.write_bytes(data);text,status=extract_text(target)
 doc=models.UploadedDocument(session_id=session_id,filename=safe_name,stored_path=str(target),extracted_text=text,ocr_status=status);db.add(doc);db.commit();db.refresh(doc)
 return {'id':doc.id,'filename':doc.filename,'extracted_text':doc.extracted_text,'ocr_status':doc.ocr_status,'created_at':str(doc.created_at)}
@app.get('/api/sessions/{session_id}/documents')
def list_documents(session_id:int,db:Session=Depends(get_db)):
 session_or_404(db,session_id);docs=db.query(models.UploadedDocument).filter(models.UploadedDocument.session_id==session_id).all()
 return [{'id':d.id,'filename':d.filename,'extracted_text':d.extracted_text,'ocr_status':d.ocr_status,'created_at':str(d.created_at)} for d in docs]
@app.post('/api/sessions/{session_id}/summary')
def generate_summary(session_id:int,db:Session=Depends(get_db)):
 s=session_or_404(db,session_id)
 if not s.consent_given or s.consent_revoked: raise HTTPException(403,'Active consent is required.')
 p=db.query(models.Patient).filter(models.Patient.id==s.patient_id).first();answers=json.loads(s.answers_json or '{}');flags=json.loads(s.red_flags_json or '[]')
 docs=db.query(models.UploadedDocument).filter(models.UploadedDocument.session_id==session_id).all()
 summary=ai_service.structure_summary(patient_dict(p),answers,[f'[{d.filename}; OCR status: {d.ocr_status}]\n{d.extracted_text}' for d in docs])
 if flags: summary='POTENTIAL RED-FLAG WORDING DETECTED: '+ '; '.join(flags)+'\nAlert clinical staff to assess. This automated rule is not an emergency detector.\n\n'+summary
 s.summary_draft=summary;s.physician_status='Pending review';db.commit();return {'summary':summary,'red_flags':flags,'status':s.physician_status,'ai_provider':ai_service.provider}
@app.put('/api/sessions/{session_id}/review')
def physician_review(session_id:int,payload:schemas.ReviewInput,db:Session=Depends(get_db),user=Depends(require_roles('admin','physician'))):
 s=session_or_404(db,session_id)
 if payload.status not in ['Pending review','Edited','Confirmed','Needs clarification']: raise HTTPException(400,'Invalid review status')
 if not s.summary_draft and not payload.summary.strip(): raise HTTPException(400,'Generate or enter a draft before review')
 s.summary_draft=payload.summary;s.physician_notes=payload.notes;s.physician_status=payload.status;db.commit();audit(db,'physician_review',session_id,user,f'status={payload.status}')
 return {'message':'Review saved','status':s.physician_status,'summary':s.summary_draft,'reviewer':user.full_name}
@app.get('/api/dashboard')
def dashboard(db:Session=Depends(get_db),user=Depends(require_roles('admin','physician','staff'))):
 sessions=db.query(models.IntakeSession).order_by(desc(models.IntakeSession.id)).limit(100).all();out=[]
 for s in sessions:
  p=db.query(models.Patient).filter(models.Patient.id==s.patient_id).first();q=db.query(models.QueueEntry).filter(models.QueueEntry.session_id==s.id).first()
  out.append({'session_id':s.id,'patient':patient_dict(p),'status':s.physician_status,'consent_given':s.consent_given,'red_flags':json.loads(s.red_flags_json or '[]'),'created_at':str(s.created_at),'queue_number':q.queue_number if q else None,'queue_status':q.status if q else 'Not queued'})
 return {'total_sessions':db.query(models.IntakeSession).count(),'pending_review':db.query(models.IntakeSession).filter(models.IntakeSession.physician_status=='Pending review').count(),'sessions':out}
@app.get('/api/queue')
def get_queue(db:Session=Depends(get_db),user=Depends(require_roles('admin','physician','staff'))):
 rows=db.query(models.QueueEntry).order_by(models.QueueEntry.queue_number).all();out=[]
 for q in rows:
  s=db.query(models.IntakeSession).filter(models.IntakeSession.id==q.session_id).first();p=db.query(models.Patient).filter(models.Patient.id==s.patient_id).first() if s else None
  if p: out.append({'id':q.id,'session_id':q.session_id,'queue_number':q.queue_number,'status':q.status,'priority_note':q.priority_note,'patient':patient_dict(p),'created_at':str(q.created_at)})
 return out
@app.put('/api/queue/{entry_id}')
def update_queue(entry_id:int,payload:schemas.QueueUpdate,db:Session=Depends(get_db),user=Depends(require_roles('admin','physician','staff'))):
 allowed={'Waiting','In consultation','Completed','On hold'}
 if payload.status not in allowed: raise HTTPException(400,'Invalid queue status')
 q=db.query(models.QueueEntry).filter(models.QueueEntry.id==entry_id).first()
 if not q: raise HTTPException(404,'Queue entry not found')
 q.status=payload.status;q.priority_note=payload.priority_note[:255];db.commit();audit(db,'queue_updated',q.session_id,user,f'status={q.status}');return {'id':q.id,'status':q.status}
@app.get('/api/sessions/{session_id}/timeline')
def timeline(session_id:int,db:Session=Depends(get_db),user=Depends(require_roles('admin','physician','staff'))):
 s=session_or_404(db,session_id);p=db.query(models.Patient).filter(models.Patient.id==s.patient_id).first();items=[{'date':str(s.created_at),'type':'Intake created','detail':f'Clinical intake session #{s.id} created'}]
 if s.consent_timestamp:items.append({'date':str(s.consent_timestamp),'type':'Consent','detail':'Consent given' if s.consent_given else 'Consent later revoked'})
 docs=db.query(models.UploadedDocument).filter(models.UploadedDocument.session_id==session_id).all()
 for d in docs:items.append({'date':str(d.created_at),'type':'Medical document','detail':f'{d.filename} · OCR status: {d.ocr_status}'})
 if s.summary_draft:items.append({'date':str(s.created_at),'type':'Clinical summary','detail':f'Draft status: {s.physician_status}'})
 q=db.query(models.QueueEntry).filter(models.QueueEntry.session_id==session_id).first()
 if q:items.append({'date':str(q.created_at),'type':'Queue','detail':f'Queue #{q.queue_number} · {q.status}'})
 return {'patient':patient_dict(p),'session_id':s.id,'events':sorted(items,key=lambda x:x['date'] or '',reverse=True)}
def pdf_bytes(title,body):
 buf=BytesIO();doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=42);styles=getSampleStyleSheet();story=[Paragraph(title,styles['Title']),Spacer(1,12)]
 for line in body.splitlines():
  safe=line.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
  story.append(Paragraph(safe or '&nbsp;',styles['BodyText']));story.append(Spacer(1,4))
 doc.build(story);buf.seek(0);return buf
@app.get('/api/sessions/{session_id}/summary.pdf')
def summary_pdf(session_id:int,db:Session=Depends(get_db),user=Depends(require_roles('admin','physician'))):
 s=session_or_404(db,session_id)
 if not s.summary_draft: raise HTTPException(404,'No summary draft exists yet')
 p=db.query(models.Patient).filter(models.Patient.id==s.patient_id).first();body=f'Patient: {p.name} | Age: {p.age} | Session: {s.id}\nStatus: {s.physician_status}\n\n{s.summary_draft}\n\nNOT A DIAGNOSIS. Draft must be verified and approved by a qualified physician.'
 return StreamingResponse(pdf_bytes('MediKiosk Clinical Intake Draft',body),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename=medikiosk-session-{session_id}-draft.pdf'})
@app.get('/api/sessions/{session_id}/fhir')
def export_fhir(session_id:int,db:Session=Depends(get_db),user=Depends(require_roles('admin','physician'))):
 s=session_or_404(db,session_id);p=db.query(models.Patient).filter(models.Patient.id==s.patient_id).first()
 # Local FHIR R4-shaped export only. This endpoint does not connect to ABDM or a health information exchange.
 bundle={'resourceType':'Bundle','type':'collection','meta':{'profile':['http://hl7.org/fhir/StructureDefinition/Bundle']},'entry':[{'resource':{'resourceType':'Patient','id':f'mk-patient-{p.id}','name':[{'text':p.name}],'gender':{'Male':'male','Female':'female'}.get(p.gender,'unknown'),'identifier':([{'system':'urn:abdm:abha','value':p.abha_id}] if p.abha_id else [])}},{'resource':{'resourceType':'DocumentReference','id':f'mk-summary-{s.id}','status':'current' if s.physician_status=='Confirmed' else 'preliminary','description':'MediKiosk clinical intake draft; physician review status: '+s.physician_status,'content':[{'attachment':{'contentType':'text/plain','data':__import__('base64').b64encode((s.summary_draft or '').encode()).decode()}}]}}]}
 return bundle
@app.get('/api/integrations/status')
def integration_status(): return {'fhir':'local FHIR R4-shaped JSON export available to authorized clinicians','abdm':'not connected','note':'No real ABDM sandbox/production credentials, consent artefact flow, or health information exchange is enabled. Do not claim ABDM integration.'}
