from . import db
from flask_login import UserMixin
from datetime import datetime
import pytz

# ✅ ZAMBIAN TIME (ONLY ADDITION)
ZAMBIA_TZ = pytz.timezone("Africa/Lusaka")

def zambia_now():
    return datetime.now(ZAMBIA_TZ).replace(second=0, microsecond=0)

# =========================
# USER MODEL
# =========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # "admin" or "employee"

    def __repr__(self):
        return f"<User {self.username}>"


# =========================
# PIG MODEL
# =========================
class Pig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(100), unique=True, nullable=False)
    breed = db.Column(db.String(100), nullable=False)
    weight = db.Column(db.Float, nullable=True)
    age = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(50), default="Available")  # Available / Sold
    photo = db.Column(db.String(200), nullable=True)
    entered_by = db.Column(db.String(150), nullable=True)
    date = db.Column(db.Date, default=lambda: zambia_now().date())
    time = db.Column(db.Time, default=lambda: zambia_now().time())

    def __repr__(self):
        return f"<Pig {self.tag}>"


# =========================
# SALE MODEL
# =========================
class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pig_id = db.Column(db.Integer, db.ForeignKey('pig.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    entered_by = db.Column(db.String(150), nullable=True)
    date = db.Column(db.Date, default=lambda: zambia_now().date())
    time = db.Column(db.Time, default=lambda: zambia_now().time())

    pig = db.relationship('Pig', backref=db.backref('sales', lazy=True))

    def __repr__(self):
        return f"<Sale Pig {self.pig_id}>"


# =========================
# EXPENSE MODEL
# =========================
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    entered_by = db.Column(db.String(150), nullable=True)
    date = db.Column(db.Date, default=lambda: zambia_now().date())
    time = db.Column(db.Time, default=lambda: zambia_now().time())

    def __repr__(self):
        return f"<Expense {self.description}>"


# =========================
# PIG WEIGHT MODEL
# =========================
class PigWeight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pig_id = db.Column(db.String(100), db.ForeignKey('pig.tag'), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=lambda: zambia_now().date())
    time = db.Column(db.Time, default=lambda: zambia_now().time())

    pig = db.relationship('Pig', backref=db.backref('weights', lazy=True, uselist=True), foreign_keys=[pig_id])

    def __repr__(self):
        return f"<PigWeight {self.pig_id} - {self.weight}>"


# =========================
# VACCINATION MODEL
# =========================
class Vaccination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pig_id = db.Column(db.String(100), db.ForeignKey('pig.tag'), nullable=False)
    vaccine = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False)
    next_due = db.Column(db.Date, nullable=False)

    pig = db.relationship('Pig', backref=db.backref('vaccinations', lazy=True, uselist=True), foreign_keys=[pig_id])

    def __repr__(self):
        return f"<Vaccination {self.pig_id} - {self.vaccine}>"


# =========================
# BREEDING MODEL
# =========================
class Breeding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sow_id = db.Column(db.String(100), db.ForeignKey('pig.tag'), nullable=False)
    boar_id = db.Column(db.String(100), db.ForeignKey('pig.tag'), nullable=False)
    mating_date = db.Column(db.Date, nullable=False)
    expected_birth = db.Column(db.Date, nullable=False)

    sow = db.relationship('Pig', foreign_keys=[sow_id], backref=db.backref('sow_breedings', lazy=True))
    boar = db.relationship('Pig', foreign_keys=[boar_id], backref=db.backref('boar_breedings', lazy=True))

    def __repr__(self):
        return f"<Breeding Sow {self.sow_id} x Boar {self.boar_id}>"