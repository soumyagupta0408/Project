import re
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import hash_password, verify_password
from app.schemas.auth import RegisterRequest


def _is_email(contact: str) -> bool:
    return bool(re.match(r"^[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}$", contact.strip()))


def get_user_by_contact(db: Session, contact: str):
    contact = contact.strip()
    if _is_email(contact):
        return db.query(User).filter(User.email == contact).first()
    return db.query(User).filter(User.phone == contact).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, req: RegisterRequest) -> User:
    contact = req.contact.strip()
    if _is_email(contact):
        if db.query(User).filter(User.email == contact).first():
            raise ValueError("An account with this email already exists.")
        email, phone = contact, None
    else:
        if db.query(User).filter(User.phone == contact).first():
            raise ValueError("An account with this phone number already exists.")
        email, phone = None, contact

    user = User(
        full_name=req.full_name.strip(),
        email=email,
        phone=phone,
        hashed_password=hash_password(req.password),
        address=req.address,
        latitude=req.latitude,
        longitude=req.longitude,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, contact: str, password: str):
    user = get_user_by_contact(db, contact)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def update_alert_threshold(db: Session, user_id: int, threshold: int):
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    user.alert_threshold = max(50, min(500, threshold))
    db.commit()
    db.refresh(user)
    return user