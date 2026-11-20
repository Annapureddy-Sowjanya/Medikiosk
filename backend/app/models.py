from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base
class User(Base):
    __tablename__="users"
    id=Column(Integer,primary_key=True,index=True); email=Column(String(190),unique=True,index=True,nullable=False)
    full_name=Column(String(120),nullable=False); password_hash=Column(String(255),nullable=False); role=Column(String(30),default="physician",nullable=False)
    active=Column(Boolean,default=True,nullable=False); created_at=Column(DateTime(timezone=True),server_default=func.now())
class Patient(Base):
    __tablename__="patients"
    id=Column(Integer,primary_key=True,index=True); name=Column(String(120),nullable=False); age=Column(Integer,nullable=False)
    gender=Column(String(40),default="Prefer not to say"); mobile=Column(String(30),default=""); abha_id=Column(String(80),default="")
    language=Column(String(30),default="English"); created_at=Column(DateTime(timezone=True),server_default=func.now())
class IntakeSession(Base):
    __tablename__="intake_sessions"
    id=Column(Integer,primary_key=True,index=True); patient_id=Column(Integer,ForeignKey("patients.id"),nullable=False)
    consent_given=Column(Boolean,default=False); consent_timestamp=Column(DateTime(timezone=True),nullable=True); consent_version=Column(String(30),default="v1.0")
    consent_revoked=Column(Boolean,default=False); answers_json=Column(Text,default="{}"); summary_draft=Column(Text,default="")
    physician_notes=Column(Text,default=""); physician_status=Column(String(30),default="Pending review"); red_flags_json=Column(Text,default="[]")
    created_at=Column(DateTime(timezone=True),server_default=func.now())
class UploadedDocument(Base):
    __tablename__="documents"
    id=Column(Integer,primary_key=True,index=True); session_id=Column(Integer,ForeignKey("intake_sessions.id"),nullable=False)
    filename=Column(String(255),nullable=False); stored_path=Column(String(500),nullable=False); extracted_text=Column(Text,default="")
    ocr_status=Column(String(30),default="pending"); created_at=Column(DateTime(timezone=True),server_default=func.now())
class QueueEntry(Base):
    __tablename__="queue_entries"
    id=Column(Integer,primary_key=True,index=True); session_id=Column(Integer,ForeignKey("intake_sessions.id"),unique=True,nullable=False)
    queue_number=Column(Integer,nullable=False); status=Column(String(30),default="Waiting",nullable=False); priority_note=Column(String(255),default="")
    created_at=Column(DateTime(timezone=True),server_default=func.now()); updated_at=Column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
class AuditEvent(Base):
    __tablename__="audit_events"
    id=Column(Integer,primary_key=True,index=True); user_id=Column(Integer,ForeignKey("users.id"),nullable=True); session_id=Column(Integer,ForeignKey("intake_sessions.id"),nullable=True)
    event_type=Column(String(80),nullable=False); details=Column(Text,default=""); created_at=Column(DateTime(timezone=True),server_default=func.now())
