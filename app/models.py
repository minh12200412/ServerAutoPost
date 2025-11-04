# app/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from .db import Base

class License(Base):
    __tablename__ = "licenses"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    owner = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, default=False)
    note = Column(String, nullable=True)
