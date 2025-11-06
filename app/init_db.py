from app.db import Base, engine
from app.models import License

def init_db():
    print("🔹 Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")

if __name__ == "__main__":
    init_db()
