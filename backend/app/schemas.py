from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Any
class PatientCreate(BaseModel):
    name:str=Field(min_length=1,max_length=120); age:int=Field(ge=0,le=120); gender:str="Prefer not to say"; mobile:str=""; abha_id:str=""; language:str="English"
class ConsentInput(BaseModel): agreed:bool; version:str="v1.0"
class AnswerInput(BaseModel): question_id:str=""; answer:str=""; answers:dict[str,Any]={}
class ReviewInput(BaseModel): summary:str; notes:str=""; status:str="Confirmed"
class RevokeInput(BaseModel): reason:Optional[str]=None
class LoginInput(BaseModel): email:EmailStr; password:str=Field(min_length=8,max_length=128)
class RegisterInput(BaseModel): email:EmailStr; full_name:str=Field(min_length=2,max_length=120); password:str=Field(min_length=12,max_length=128); role:str="physician"
class QueueUpdate(BaseModel): status:str; priority_note:str=""
