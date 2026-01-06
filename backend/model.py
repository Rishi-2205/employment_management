from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, TIMESTAMP, Date, Time
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Employee(Base):
    __tablename__ = 'employee'
    employee_id = Column(Integer, primary_key=True, index=True ,autoincrement=True)
    employee_name = Column(String(50))
    employee_email = Column(String(50), unique=True, index=True)
    employee_created_time = Column(TIMESTAMP, default=datetime.datetime.now(datetime.timezone.utc))
    employee_updated_time = Column(TIMESTAMP, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))
    employee_password = Column(String(128), nullable=False)  


    roles = relationship("Employee_Role_Relationship", backref="employee")
    projects = relationship("Employee_Project_Relationship", backref="employee")
    profile = relationship("Profile", uselist=False, backref="employee")  # One-to-One
    checkins = relationship("CheckinCheckout", backref="employee")


class Role(Base):
    __tablename__ = 'rolee'  
    role_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    role_name = Column(String(50))
    role_created_time = Column(TIMESTAMP, default=datetime.datetime.now(datetime.timezone.utc))
    role_updated_time = Column(TIMESTAMP, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))


    employees = relationship("Employee_Role_Relationship", backref="rolee")


class Employee_Role_Relationship(Base):
    __tablename__ = 'employee_role_relationship'
    employee_role_id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employee.employee_id'))
    role_id = Column(Integer, ForeignKey('rolee.role_id'))
    assigned_time = Column(TIMESTAMP, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_time = Column(TIMESTAMP, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))


class Project(Base):
    __tablename__ = 'project'
    project_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_name = Column(String(50))
    created_time = Column(TIMESTAMP, default=datetime.datetime.now(datetime.timezone.utc))
    updated_time = Column(TIMESTAMP, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))

    employees = relationship("Employee_Project_Relationship", backref="project")


class Employee_Project_Relationship(Base):
    __tablename__ = 'emp_project_relationship'
    employe_project_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employee.employee_id'))
    project_id = Column(Integer, ForeignKey('project.project_id'))
    assigned_time = Column(TIMESTAMP, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_time = Column(TIMESTAMP, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))


class Profile(Base):
    __tablename__ = 'profile'
    employee_profile_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employee.employee_id'), unique=True)  # One-to-One
    first_name = Column(String(20))
    last_name = Column(String(20))
    age = Column(Integer)
    address = Column(String(100))
    father_name = Column(String(50))
    mother_name = Column(String(50))
    employee_profile_role = Column(String(20))
    date_of_joining = Column(Date)
    created_time = Column(TIMESTAMP, default=datetime.datetime.now(datetime.timezone.utc))
    updated_time = Column(TIMESTAMP, default=datetime.datetime.now(datetime.timezone.utc), onupdate=datetime.datetime.now(datetime.timezone.utc))


class CheckinCheckout(Base):
    __tablename__ = 'checkincheckout'
    employee_checincheckout_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey('employee.employee_id'))
    checkin_time = Column(TIMESTAMP, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    checkout_time = Column(TIMESTAMP, nullable=True)
    work_duration = Column(Time)
