from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)  # Telegram user ID
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    selected_profile_id = Column(Integer, ForeignKey('profiles.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    selected_profile = relationship("Profile", foreign_keys=[selected_profile_id])
    custom_profiles = relationship("Profile", back_populates="owner",
                                   foreign_keys="Profile.user_id")
    usage_logs = relationship("UsageLog", back_populates="user")

class Profile(Base):
    __tablename__ = 'profiles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    system_prompt = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)  # True for system defaults
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)  # NULL for defaults
    parent_id = Column(Integer, ForeignKey('profiles.id'), nullable=True)  # For copy-on-write
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="custom_profiles",
                        foreign_keys=[user_id])
    parent = relationship("Profile", remote_side=[id], foreign_keys=[parent_id])

class UsageLog(Base):
    __tablename__ = 'usage_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    profile_id = Column(Integer, ForeignKey('profiles.id'), nullable=False)
    audio_duration_seconds = Column(Integer, nullable=True)
    transcription_length = Column(Integer, nullable=True)  # Characters
    formatted_length = Column(Integer, nullable=True)  # Characters
    formatted_text = Column(Text, nullable=True)  # Saved formatted result
    processing_time_seconds = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="usage_logs")
