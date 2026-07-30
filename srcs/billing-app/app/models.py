"""Models for Billing API."""
import os
from sqlalchemy import create_engine, Column, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    number_of_items = Column(Integer, nullable=False)
    total_amount = Column(Float, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'number_of_items': self.number_of_items,
            'total_amount': self.total_amount
        }

def get_engine():
    db_user = os.getenv("BILLING_DB_USER", "billing_user")
    db_password = os.getenv("BILLING_DB_PASSWORD", "12qw!@QW")
    db_host = os.getenv("BILLING_DB_HOST", "localhost")
    db_port = os.getenv("BILLING_DB_PORT", "5432")
    db_name = os.getenv("BILLING_DB_NAME", "billing_db")
    
    db_uri = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    return create_engine(db_uri)

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
