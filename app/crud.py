from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from . import models
import secrets, string

# 🔹 Hàm sinh key ngẫu nhiên, ví dụ: PRO-AB12CD34EF56
def generate_key(prefix: str = "PRO", length: int = 12) -> str:
    chars = string.ascii_uppercase + string.digits
    body = ''.join(secrets.choice(chars) for _ in range(length))
    return f"{prefix}-{body}"


def create_license(db: Session, key: str = None, owner: str = None, days_valid: int = 365, note: str = None, prefix: str = "PRO"):
    """Tạo mới license, tự sinh key nếu chưa có, tránh trùng key."""
    if not key:
        for _ in range(5):
            candidate = generate_key(prefix)
            if not get_license(db, candidate):
                key = candidate
                break
        if not key:
            raise ValueError("Không thể sinh key duy nhất. Thử lại sau.")

    expires = datetime.utcnow() + timedelta(days=days_valid)
    lic = models.License(
        key=key,
        owner=owner or "Unknown",
        expires_at=expires,
        note=note,
        revoked=False
    )

    try:
        db.add(lic)
        db.commit()
        db.refresh(lic)
        return lic
    except IntegrityError:
        db.rollback()
        # Nếu key trùng, raise lỗi cho API bắt
        raise IntegrityError(f"License key '{key}' đã tồn tại trong hệ thống.", params=None, orig=None)


def get_license(db: Session, key: str):
    """Truy vấn 1 license theo key."""
    return db.query(models.License).filter(models.License.key == key).first()


def revoke_license(db: Session, key: str):
    """Đánh dấu license là bị thu hồi."""
    lic = get_license(db, key)
    if lic:
        lic.revoked = True
        db.commit()
        db.refresh(lic)
    return lic


def get_all_licenses(db: Session):
    """Lấy toàn bộ license hiện có."""
    return db.query(models.License).all()
