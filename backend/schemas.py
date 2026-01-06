from datetime import time
from  pydantic import BaseModel,Field
from datetime import datetime, date
from typing import Optional


# Define the base model for employee data
#default_factory=datetime.now ensures that the created_time and updated_time are automatically set to the current time when a new employee is created.
#if not this the datetime is not provided during creation, it will default to the current time.
#Field is used define the attribute.

#EmployeeBase model for both create and update operations
class EmployeeBase(BaseModel):
    employee_id: int
    employee_name: str
    employee_email: str
    employee_created_time: datetime = Field(default_factory=datetime.now)
    employee_updated_time: datetime = Field(default_factory=datetime.now)
    employee_password:str 
    employee_role: Optional[str] = None

class EmployeeCreate(BaseModel):
     employee_name: str
     employee_email: str
     employee_created_time: datetime = Field(default_factory=datetime.now)
     employee_updated_time: datetime = Field(default_factory=datetime.now)
     employee_password:str 

class EmployeeUpdate(BaseModel):
    employee_name: str
    employee_email: str


class EmployeeRead(EmployeeBase):
    employee_id: int
    employee_created_time: datetime
    employee_updated_time: datetime

model_config = {
        "from_attributes": True  # replaces orm_mode in Pydantic v2
    }

#role model for employee role
class RoleBase(BaseModel):
    role_name: str

class RoleCreate(RoleBase):
    pass 
class RoleUpdate(RoleBase):
    pass 

class RoleRead(RoleBase):
    role_id: int
    role_created_time: datetime
    role_updated_time: datetime

model_config = {
        "from_attributes": True  # replaces orm_mode in Pydantic v2
    }

#project model for employee project
class ProjectBase(BaseModel):
    project_name: str

class ProjectCreate(ProjectBase):
    pass 

class ProjectUpdate(ProjectBase):
    pass 

class ProjectRead(ProjectBase):
    project_id: int
    created_time: datetime
    updated_time: datetime

    model_config = {
        "from_attributes": True
    }

#Employee role relationship
class EmployeeRoleBase(BaseModel):
    employee_email: str
    role_id: int

class EmployeeRoleCreate(EmployeeRoleBase):
    pass

class EmployeeRoleUpdate(EmployeeRoleBase):
    pass

class EmployeeRoleRead(EmployeeRoleBase):
    employee_role_id: int
    assigned_time: datetime
    updated_time: datetime

model_config = {
        "from_attributes": True  # replaces orm_mode in Pydantic v2
    }

#employee project relationship
class EmployeeProjectBase(BaseModel):
    employee_email: str
    project_id: int


class EmployeeProjectCreate(EmployeeProjectBase):
    pass 

class EmployeeProjectUpdate(EmployeeProjectBase):
    pass

class EmployeeProjectRead(EmployeeProjectBase):
    employe_project_id: int    
    assigned_time: datetime
    updated_time: datetime

    model_config = {
        "from_attributes": True
    }



#profile model for employee profile
class ProfileBase(BaseModel):
    employee_id: int
    first_name: str
    last_name: str
    age: Optional[int] = None
    address: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    employee_profile_role: Optional[str] = None
    date_of_joining: date


class ProfileCreate(ProfileBase):
    pass 

class ProfileUpdate(ProfileBase):
    pass 

class ProfileRead(ProfileBase):
    employee_profile_id: int
    created_time: datetime
    updated_time: datetime

    model_config = {
        "from_attributes": True  # replaces orm_mode in Pydantic v2
    }

#checkin and checkout model for employee checkin and checkout

class CheckinCheckoutBase(BaseModel):
    employee_id: int
    checkin_time: Optional[datetime] = None
    checkout_time: Optional[datetime] = None
    work_duration: Optional[time] = None

class CheckinCheckoutCreate(CheckinCheckoutBase):
    pass

class CheckinCheckoutRead(CheckinCheckoutBase):
    employee_checincheckout_id: int

    model_config = {
        "from_attributes": True  # replaces orm_mode in Pydantic v2
    }