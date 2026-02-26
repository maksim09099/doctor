import json
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

app = FastAPI(title="Oculus MD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "data.json")

SECRET_KEY = "super_secret_key_change_me"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def load_data():
    if not os.path.exists(DB_FILE):
        return {"users": [], "patients": [], "iol_calculations": []}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PatientRequest(BaseModel):
    full_name: str
    snils: str = ""
    policy_number: str = ""
    diagnosis_icd10: str = ""
    status: str = "yellow"


class IolCalcRequest(BaseModel):
    patient_id: int
    formula_name: str
    k1: float
    k2: float
    acd: Optional[float] = None
    axial_length: float
    a_constant: Optional[float] = None
    target_refraction: float = 0.0


@app.get("/")
def root():
    return {"message": "Oculus MD backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register")
def register(payload: RegisterRequest):
    data = load_data()

    if any(u["email"] == payload.email for u in data["users"]):
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    user_id = len(data["users"]) + 1
    user = {
        "id": user_id,
        "full_name": payload.full_name,
        "email": payload.email,
        "hashed_password": hash_password(payload.password),
        "role": payload.role
    }

    data["users"].append(user)
    save_data(data)

    token = create_access_token({"sub": str(user_id), "role": payload.role})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/login")
def login(payload: LoginRequest):
    data = load_data()
    user = next((u for u in data["users"] if u["email"] == payload.email), None)

    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    token = create_access_token({"sub": str(user["id"]), "role": user["role"]})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/patients")
def create_patient(payload: PatientRequest):
    data = load_data()
    patient_id = len(data["patients"]) + 1

    patient = {
        "id": patient_id,
        "full_name": payload.full_name,
        "snils": payload.snils,
        "policy_number": payload.policy_number,
        "diagnosis_icd10": payload.diagnosis_icd10,
        "status": payload.status
    }

    data["patients"].append(patient)
    save_data(data)
    return patient


@app.get("/patients")
def list_patients():
    data = load_data()
    return data["patients"]


@app.post("/iol/calculate")
def iol_calculate(payload: IolCalcRequest):
    data = load_data()

    mean_k = round((payload.k1 + payload.k2) / 2, 2)

    result = {
        "id": len(data["iol_calculations"]) + 1,
        "patient_id": payload.patient_id,
        "formula_name": payload.formula_name,
        "k1": payload.k1,
        "k2": payload.k2,
        "acd": payload.acd,
        "axial_length": payload.axial_length,
        "a_constant": payload.a_constant,
        "target_refraction": payload.target_refraction,
        "mean_k": mean_k,
        "message": "Расчёт сохранён. Требуется подтверждение хирургом."
    }

    data["iol_calculations"].append(result)
    save_data(data)
    return result