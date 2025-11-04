from app.db import SessionLocal, engine
from app.models import Base
from app.crud import create_license

Base.metadata.create_all(bind=engine)
db = SessionLocal()

create_license(db, key="TRIAL-1234-ABCDE", owner="Test User", days_valid=30)
print("✅ Created sample license key: TRIAL-1234-ABCDE")
