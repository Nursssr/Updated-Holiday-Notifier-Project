from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Date, BigInteger, ForeignKey, TIMESTAMP, func


Base = declarative_base()


class Holiday(AsyncAttrs, Base):
    __tablename__ = "holidays"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    day = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)

    notifications = relationship("Notification", back_populates="holiday")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, nullable=False)
    name = Column(String, nullable=False)
    birthday = Column(Date, nullable=True)

    notifications = relationship("Notification", back_populates="user")


class Notification(AsyncAttrs, Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    holiday_id = Column(Integer, ForeignKey("holidays.id"))
    sent_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")
    holiday = relationship("Holiday", back_populates="notifications")