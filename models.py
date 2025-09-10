from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Date, BigInteger, ForeignKey, TIMESTAMP, func

Base = declarative_base()


class Holiday(AsyncAttrs, Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True)
    day = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    scope = Column(String, default="kz")
    type = Column(String, default="regular") # regular/birthday


    translations = relationship("HolidayTranslation", back_populates="holiday", cascade="all, delete")
    notifications = relationship("Notification", back_populates="holiday")


class HolidayTranslation(AsyncAttrs, Base):
    __tablename__ = "holiday_translations"

    id = Column(Integer, primary_key=True)
    holiday_id = Column(Integer, ForeignKey("holidays.id", ondelete="CASCADE"))
    lang = Column(String(5), nullable=False)  # "ru", "kk", "en"
    name = Column(String, nullable=False)

    holiday = relationship("Holiday", back_populates="translations")


class User(AsyncAttrs, Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, nullable=False)
    name = Column(String, nullable=False)
    birthday = Column(Date, nullable=True)
    lang = Column(String(5), default="ru")

    notifications = relationship("Notification", back_populates="user")


class Notification(AsyncAttrs, Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'))
    holiday_id = Column(Integer, ForeignKey("holidays.id", ondelete='CASCADE'))
    sent_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")
    holiday = relationship("Holiday", back_populates="notifications")
