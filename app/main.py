# app/main.py
from fastapi import FastAPI, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from . import crud, models
from .db import SessionLocal, engine
from .config import settings
from app.config import settings  
import secrets, string
from sqlalchemy.exc import IntegrityError
from app.init_db import init_db
init_db()

models.Base.metadata.create_all(bind=engine)
SECRET_KEY = settings.SECRET_KEY
app = FastAPI(title="License Verification API")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"message": "License Server is running."}

# ----------------------------
# 1️⃣ API: Kích hoạt License
# ----------------------------
@app.post("/activate")
async def activate_license(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    key = data.get("key")
    if not key:
        raise HTTPException(status_code=400, detail="License key is required")

    lic = crud.get_license(db, key)
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")

    if lic.revoked:
        return {"status": "revoked", "message": "License has been revoked"}

    if lic.expires_at and lic.expires_at < datetime.utcnow():
        return {"status": "expired", "message": "License expired"}

    payload = {
        "key": lic.key,
        "owner": lic.owner,
        "exp": int(lic.expires_at.timestamp())
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return {
        "status": "valid",
        "token": token,
        "expires_at": lic.expires_at.isoformat(),
        "message": "License is valid"
    }

# ----------------------------
# 2️⃣ API: Kiểm tra License
# ----------------------------
@app.post("/validate")
async def validate_license(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    token = data.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        key = payload.get("key")

        # ✅ kiểm tra trong database
        lic = crud.get_license(db, key)
        if not lic:
            return {"valid": False, "reason": "License not found"}
        if lic.revoked:
            return {"valid": False, "reason": "License revoked"}

        # Nếu chưa bị revoke và còn hạn → valid
        if lic.expires_at < datetime.utcnow():
            return {"valid": False, "reason": "License expired"}

        return {"valid": True, "key": key, "owner": lic.owner, "expires": lic.expires_at.isoformat()}

    except jwt.ExpiredSignatureError:
        return {"valid": False, "reason": "Token expired"}
    except jwt.InvalidTokenError:
        return {"valid": False, "reason": "Invalid token"}
    except Exception as e:
        return {"valid": False, "reason": str(e)}

# ----------------------------
# 3️⃣ API: Admin tạo License
# ----------------------------

def generate_key(prefix: str = "PRO", length: int = 12):
    """Sinh key ngẫu nhiên dạng PRO-ABC123XYZ"""
    chars = string.ascii_uppercase + string.digits
    body = ''.join(secrets.choice(chars) for _ in range(length))
    return f"{prefix}-{body}"

@app.post("/admin/create")
async def create_license(request: Request, db: Session = Depends(get_db)):
    """
    API tạo License:
    - Nếu không truyền key → tự sinh key duy nhất.
    - Nếu key đã tồn tại → báo lỗi rõ ràng (409 Conflict).
    """
    data = await request.json()
    owner = data.get("owner", "Unknown")
    days = int(data.get("days_valid", 365))
    prefix = data.get("prefix", "PRO")

    # Nếu không nhập key → tự sinh
    key = data.get("key")
    if not key:
        for _ in range(5):  # thử tối đa 5 lần để tránh trùng
            candidate = generate_key(prefix=prefix)
            if not crud.get_license(db, candidate):
                key = candidate
                break
        if not key:
            raise HTTPException(status_code=500, detail="Không thể sinh key duy nhất. Thử lại sau.")

    # Tạo bản ghi mới
    try:
        new_license = crud.create_license(db, key, owner, days)
        db.commit()
        return {
            "message": "License created",
            "key": new_license.key,
            "expires": new_license.expires_at,
            "owner": owner
        }
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"License key '{key}' đã tồn tại.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo license: {e}")

# ----------------------------
# 4️⃣ API: Admin thu hồi License
# ----------------------------
@app.post("/admin/revoke")
async def revoke_license(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    key = data.get("key")
    lic = crud.revoke_license(db, key)
    if not lic:
        raise HTTPException(status_code=404, detail="License not found")
    return {"message": f"License {key} revoked"}

@app.get("/admin/list")
def list_licenses(active_only: bool = True, db: Session = Depends(get_db)):
    """
    Liệt kê tất cả license hiện có trong hệ thống.
    - Nếu active_only=True → chỉ hiển thị license chưa hết hạn và chưa bị thu hồi.
    """
    licenses = crud.get_all_licenses(db)
    now = datetime.utcnow()
    result = []

    for lic in licenses:
        if active_only:
            if lic.revoked or lic.expires_at < now:
                continue
        result.append({
            "key": lic.key,
            "owner": lic.owner,
            "created_at": lic.created_at.isoformat(),
            "expires_at": lic.expires_at.isoformat(),
            "revoked": lic.revoked
        })

    return {"count": len(result), "licenses": result}