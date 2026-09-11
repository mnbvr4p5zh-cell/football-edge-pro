import json, os, secrets, hashlib, hmac
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
import jwt

DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///./football_edge.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL=DATABASE_URL.replace("postgres://","postgresql+psycopg://",1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL=DATABASE_URL.replace("postgresql://","postgresql+psycopg://",1)
connect_args={"check_same_thread":False} if DATABASE_URL.startswith("sqlite") else {}
engine=create_engine(DATABASE_URL,connect_args=connect_args,pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine,expire_on_commit=False)
SECRET=os.getenv("JWT_SECRET",secrets.token_hex(24))

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    email:Mapped[str]=mapped_column(String(240),unique=True,index=True)
    password_hash:Mapped[str]=mapped_column(String(400))
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Analysis(Base):
    __tablename__="analyses"
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    user_id:Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
    home:Mapped[str]=mapped_column(String(120)); away:Mapped[str]=mapped_column(String(120))
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,index=True)
    payload:Mapped[str]=mapped_column(Text)
Base.metadata.create_all(engine)

def hash_password(password:str)->str:
    salt=secrets.token_bytes(16); rounds=210_000
    dk=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${dk.hex()}"
def verify_password(password:str, encoded:str)->bool:
    try:
        _,rounds,salt,expected=encoded.split('$')
        dk=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(rounds))
        return hmac.compare_digest(dk.hex(),expected)
    except Exception:return False
def make_token(user_id:int)->str:
    exp=datetime.now(timezone.utc)+timedelta(days=14)
    return jwt.encode({"sub":str(user_id),"exp":exp},SECRET,algorithm="HS256")
def parse_token(token:str)->int|None:
    try:return int(jwt.decode(token,SECRET,algorithms=["HS256"])["sub"])
    except Exception:return None
def save_analysis(home:str,away:str,payload:dict,user_id:int|None=None):
    with SessionLocal() as db:
        row=Analysis(home=home,away=away,payload=json.dumps(payload,ensure_ascii=False),user_id=user_id); db.add(row); db.commit()
def history(user_id:int|None=None,limit:int=30):
    with SessionLocal() as db:
        q=db.query(Analysis)
        if user_id is not None:q=q.filter(Analysis.user_id==user_id)
        rows=q.order_by(Analysis.created_at.desc()).limit(limit).all()
        return [{"id":r.id,"home":r.home,"away":r.away,"created_at":r.created_at.isoformat(),"data":json.loads(r.payload)} for r in rows]
