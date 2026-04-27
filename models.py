# models.py
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class URL(Base):
    __tablename__ = "urls"
    
    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(10), unique=True, index=True, nullable=False)
    long_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    clicks = Column(Integer, default=0)

# ⚠️ IMPORTANT: Replace 'YOUR_PASSWORD' with your actual PostgreSQL password
# ⚠️ Note: database name is 'url_shortener' (with your spelling)
DATABASE_URL = "postgresql://postgres:postgres@localhost/url_shortener"

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)

print("✅ Database tables created successfully!")
print("   Table 'urls' is ready to store your shortened links!")