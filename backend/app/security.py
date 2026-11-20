import os, hashlib, hmac, secrets
from datetime import datetime,timedelta,timezone
from jose import jwt,JWTError
from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from . import models
JWT_SECRET=os.getenv("JWT_SECRET","CHANGE_THIS_DEVELOPMENT_SECRET_BEFORE_DEPLOYMENT"); JWT_ALGORITHM="HS256"; TOKEN_MINUTES=int(os.getenv("TOKEN_MINUTES","480")); bearer=HTTPBearer(auto_error=False)
def hash_password(password:str)->str:
 salt=secrets.token_hex(16); digest=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),310000); return f"pbkdf2_sha256$310000${salt}${digest.hex()}"
def verify_password(password:str,stored:str)->bool:
 try:
  _,rounds,salt,expected=stored.split("$"); actual=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),int(rounds)).hex(); return hmac.compare_digest(actual,expected)
 except Exception:return False
def create_access_token(user):
 now=datetime.now(timezone.utc); return jwt.encode({"sub":str(user.id),"role":user.role,"iat":now,"exp":now+timedelta(minutes=TOKEN_MINUTES)},JWT_SECRET,algorithm=JWT_ALGORITHM)
def current_user(credentials:HTTPAuthorizationCredentials=Depends(bearer),db:Session=Depends(get_db)):
 if not credentials: raise HTTPException(401,"Sign in required",headers={"WWW-Authenticate":"Bearer"})
 try: payload=jwt.decode(credentials.credentials,JWT_SECRET,algorithms=[JWT_ALGORITHM]); uid=int(payload.get("sub","0"))
 except Exception: raise HTTPException(401,"Invalid or expired access token")
 user=db.query(models.User).filter(models.User.id==uid,models.User.active==True).first()
 if not user: raise HTTPException(401,"User account is unavailable")
 return user
def require_roles(*roles):
 def dependency(user=Depends(current_user)):
  if user.role not in roles: raise HTTPException(403,"Your account does not have permission for this action")
  return user
 return dependency
