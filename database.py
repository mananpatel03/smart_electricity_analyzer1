import os
import json
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey, select
)
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

Base = declarative_base()

# Models
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(150), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else ''
        }

class Tariff(Base):
    __tablename__ = 'tariffs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    name = Column(String(100), nullable=False)
    rate_type = Column(String(20), default='slab')
    flat_rate = Column(Float, default=7.0)
    fixed_charge = Column(Float, default=60.0)
    tax_percent = Column(Float, default=6.0)
    slab_json = Column(Text, nullable=True)
    is_default = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'rate_type': self.rate_type,
            'flat_rate': float(self.flat_rate or 7.0),
            'fixed_charge': float(self.fixed_charge or 60.0),
            'tax_percent': float(self.tax_percent or 6.0),
            'slab_json': self.slab_json or '[]',
            'is_default': self.is_default
        }

class Appliance(Base):
    __tablename__ = 'appliances'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    name = Column(String(150), nullable=False)
    category = Column(String(50), default='General')
    power_watts = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)
    hours_per_day = Column(Float, nullable=False)
    days_per_month = Column(Integer, default=30)
    standby_watts = Column(Float, default=0.0)
    standby_hours = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'category': self.category,
            'power_watts': float(self.power_watts),
            'quantity': int(self.quantity),
            'hours_per_day': float(self.hours_per_day),
            'days_per_month': int(self.days_per_month),
            'standby_watts': float(self.standby_watts or 0.0),
            'standby_hours': float(self.standby_hours or 0.0),
            'created_at': self.created_at.isoformat() if self.created_at else ''
        }

class BillRecord(Base):
    __tablename__ = 'bill_records'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    billing_period = Column(String(50), nullable=False)
    prev_reading = Column(Float, default=0.0)
    curr_reading = Column(Float, default=0.0)
    units_consumed = Column(Float, nullable=False)
    tariff_rate = Column(Float, nullable=False)
    fixed_charge = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    estimated_amount = Column(Float, nullable=False)
    actual_amount = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'billing_period': self.billing_period,
            'prev_reading': float(self.prev_reading or 0.0),
            'curr_reading': float(self.curr_reading or 0.0),
            'units_consumed': float(self.units_consumed),
            'tariff_rate': float(self.tariff_rate),
            'fixed_charge': float(self.fixed_charge or 0.0),
            'tax_amount': float(self.tax_amount or 0.0),
            'estimated_amount': float(self.estimated_amount),
            'actual_amount': float(self.actual_amount) if self.actual_amount is not None else None,
            'notes': self.notes or '',
            'created_at': self.created_at.isoformat() if self.created_at else ''
        }

class SavingScenario(Base):
    __tablename__ = 'saving_scenarios'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, default=1)
    scenario_name = Column(String(150), nullable=False)
    details_json = Column(Text, nullable=True)
    monthly_saved_kwh = Column(Float, nullable=False)
    monthly_saved_cost = Column(Float, nullable=False)
    yearly_saved_cost = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Engine Resolution (Render PostgreSQL vs MySQL vs SQLite)
def get_database_url():
    # Render and major cloud providers inject DATABASE_URL
    url = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL') or os.environ.get('MYSQL_URL')
    if url:
        # Render specifies 'postgres://', which needs to be 'postgresql+pg8000://' for SQLAlchemy + pure Python driver
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql+pg8000://', 1)
        elif url.startswith('postgresql://'):
            url = url.replace('postgresql://', 'postgresql+pg8000://', 1)
        return url

    # Local fallback: SQLite database in current project directory
    local_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'energy_analyzer.db')
    return f"sqlite:///{local_db_path}"

# Setup Engine and Session
DB_URL = get_database_url()
is_sqlite = DB_URL.startswith('sqlite')

engine_args = {}
if is_sqlite:
    engine_args['connect_args'] = {'check_same_thread': False}
else:
    # Pool settings for hosted PostgreSQL / MySQL on Render
    engine_args['pool_pre_ping'] = True
    engine_args['pool_size'] = 5
    engine_args['max_overflow'] = 10

engine = create_engine(DB_URL, **engine_args)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_session():
    return SessionLocal()

def init_db():
    """Create all tables and seed sample data if first run"""
    Base.metadata.create_all(bind=engine)
    session = get_session()
    try:
        # Seed default User
        user = session.query(User).filter_by(id=1).first()
        if not user:
            user = User(id=1, username='demo_user', email='demo@energyanalyzer.local', password_hash='demo_hash')
            session.add(user)
            session.commit()

        # Seed default Tariff
        tariff = session.query(Tariff).filter_by(is_default=1).first()
        if not tariff:
            default_slabs = [
                {"from": 0, "to": 100, "rate": 3.75},
                {"from": 101, "to": 300, "rate": 6.50},
                {"from": 301, "to": 500, "rate": 8.75},
                {"from": 501, "to": 999999, "rate": 11.20}
            ]
            tariff = Tariff(
                user_id=1,
                name='Standard Domestic (Tiered Slabs)',
                rate_type='slab',
                flat_rate=7.0,
                fixed_charge=60.0,
                tax_percent=6.0,
                slab_json=json.dumps(default_slabs),
                is_default=1
            )
            session.add(tariff)
            session.commit()

        # Seed sample Appliances if empty
        app_count = session.query(Appliance).filter_by(user_id=1).count()
        if app_count == 0:
            sample_appliances = [
                Appliance(user_id=1, name='Inverter Air Conditioner 1.5T', category='Cooling', power_watts=1200.0, quantity=1, hours_per_day=6.0, days_per_month=30, standby_watts=2.0, standby_hours=18.0),
                Appliance(user_id=1, name='Ceiling Fan', category='Cooling', power_watts=75.0, quantity=3, hours_per_day=10.0, days_per_month=30, standby_watts=0.0, standby_hours=0.0),
                Appliance(user_id=1, name='Double-Door Refrigerator', category='Kitchen', power_watts=180.0, quantity=1, hours_per_day=24.0, days_per_month=30, standby_watts=0.0, standby_hours=0.0),
                Appliance(user_id=1, name='LED Room Bulbs', category='Lighting', power_watts=9.0, quantity=6, hours_per_day=6.0, days_per_month=30, standby_watts=0.0, standby_hours=0.0),
                Appliance(user_id=1, name='Desktop PC / Monitor', category='Computing', power_watts=220.0, quantity=1, hours_per_day=5.0, days_per_month=30, standby_watts=5.0, standby_hours=19.0),
                Appliance(user_id=1, name='Smart LED TV 43"', category='Entertainment', power_watts=80.0, quantity=1, hours_per_day=4.0, days_per_month=30, standby_watts=3.0, standby_hours=20.0),
                Appliance(user_id=1, name='Water Geyser / Heater', category='Heating', power_watts=2000.0, quantity=1, hours_per_day=0.75, days_per_month=30, standby_watts=0.0, standby_hours=0.0),
                Appliance(user_id=1, name='Washing Machine', category='Laundry', power_watts=500.0, quantity=1, hours_per_day=0.8, days_per_month=20, standby_watts=1.0, standby_hours=23.0)
            ]
            session.add_all(sample_appliances)
            session.commit()

        # Seed sample Bill Records if empty
        bill_count = session.query(BillRecord).filter_by(user_id=1).count()
        if bill_count == 0:
            sample_bills = [
                BillRecord(user_id=1, billing_period='May 2026', prev_reading=1420.0, curr_reading=1780.0, units_consumed=360.0, tariff_rate=7.0, fixed_charge=60.0, tax_amount=151.2, estimated_amount=2731.2, actual_amount=2810.0, notes='Hot summer month, high AC use'),
                BillRecord(user_id=1, billing_period='Jun 2026', prev_reading=1780.0, curr_reading=2195.0, units_consumed=415.0, tariff_rate=7.0, fixed_charge=60.0, tax_amount=174.3, estimated_amount=3139.3, actual_amount=3190.0, notes='Peak summer billing'),
                BillRecord(user_id=1, billing_period='Jul 2026', prev_reading=2195.0, curr_reading=2520.0, units_consumed=325.0, tariff_rate=7.0, fixed_charge=60.0, tax_amount=136.5, estimated_amount=2471.5, actual_amount=2450.0, notes='Monsoon cooling'),
                BillRecord(user_id=1, billing_period='Aug 2026', prev_reading=2520.0, curr_reading=2815.0, units_consumed=295.0, tariff_rate=7.0, fixed_charge=60.0, tax_amount=123.9, estimated_amount=2248.9, actual_amount=2290.0, notes='Moderate usage'),
                BillRecord(user_id=1, billing_period='Sep 2026', prev_reading=2815.0, curr_reading=3090.0, units_consumed=275.0, tariff_rate=7.0, fixed_charge=60.0, tax_amount=115.5, estimated_amount=2100.5, actual_amount=2080.0, notes='Optimized fan and AC hours'),
                BillRecord(user_id=1, billing_period='Oct 2026', prev_reading=3090.0, curr_reading=3350.0, units_consumed=260.0, tariff_rate=7.0, fixed_charge=60.0, tax_amount=109.2, estimated_amount=1989.2, actual_amount=1970.0, notes='Mild weather, consistent savings')
            ]
            session.add_all(sample_bills)
            session.commit()
    finally:
        session.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully with URL:", DB_URL.split('@')[-1] if '@' in DB_URL else DB_URL)
