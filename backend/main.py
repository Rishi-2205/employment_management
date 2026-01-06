from fastapi import FastAPI,Depends,HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal,engine
from model import Base,Role,Employee_Role_Relationship
import schemas,model
from authpassword import hash_password,verify_password
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt,JWTError
from datetime import timedelta, datetime
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)  # Creates tables in Docker PostgreSQL
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8086) 


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],  # Allow both frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Generate JWT token
SECRET_KEY = "MYSECRETKEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")



def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + expires_delta})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

#get the user from the JWT token
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        role = payload.get("role")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(model.Employee).filter(model.Employee.employee_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Attach role for reference
    user.role = role
    return user


def require_admin(user: model.Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    role_rel = db.query(model.Employee_Role_Relationship).filter(model.Employee_Role_Relationship.employee_id == user.employee_id).first()
    if not role_rel:
        raise HTTPException(status_code=403, detail="No role assigned")
    
    role = db.query(model.Role).filter(model.Role.role_id == role_rel.role_id).first()
    if not role or role.role_name.lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

#loging in endpoint
@app.post("/login")
def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(model.Employee).filter(model.Employee.employee_email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.employee_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    # Get user role
    role_rel = db.query(model.Employee_Role_Relationship).filter_by(employee_id=user.employee_id).first()
    role = db.query(model.Role).filter_by(role_id=role_rel.role_id).first() if role_rel else None
    role_name = role.role_name.lower() if role else "user"

    # Add role to token
    access_token = create_access_token(data={
        "sub": str(user.employee_id),
        "role": role_name
    })

    return {"access_token": access_token, "token_type": "bearer"}


#EMPLOYEE CRUD 
@app.post("/employees", response_model=schemas.EmployeeRead)
def create_employee(employee: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    db_employee=db.query(model.Employee).filter(model.Employee.employee_email == employee.employee_email).first()
    if db_employee:
        raise HTTPException(status_code=400, detail="Employee already exists")
    new_employee=model.Employee(
        employee_name=employee.employee_name,
        employee_email=employee.employee_email,
        employee_password=hash_password(employee.employee_password)
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee

@app.get("/employees", response_model=list[schemas.EmployeeRead], dependencies=[Depends(require_admin)])
def read_employees(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(model.Employee).offset(skip).limit(limit).all()


@app.get("/employees/{employee_id}", response_model=schemas.EmployeeRead)
def read_employee(employee_id: int, db: Session = Depends(get_db), user: model.Employee = Depends(get_current_user)):
    if user.employee_id != employee_id:
        require_admin(user, db)
    employee = db.query(model.Employee).filter(model.Employee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee

@app.put("/employees/{employee_id}", response_model=schemas.EmployeeRead)
def update_employee(employee_id: int, emp_update: schemas.EmployeeUpdate, db: Session = Depends(get_db), user: model.Employee = Depends(get_current_user)):
    if user.employee_id != employee_id:
        require_admin(user, db)
    employee = db.query(model.Employee).filter(model.Employee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    employee.employee_name = emp_update.employee_name
    employee.employee_email = emp_update.employee_email
    db.commit()
    db.refresh(employee)
    return employee

@app.delete("/employees/{employee_id}", dependencies=[Depends(require_admin)])
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    employee = db.query(model.Employee).filter(model.Employee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(employee)
    db.commit()
    return {"detail": "Employee deleted"}


#PROJECT-CRUD
@app.post("/projects", response_model=schemas.ProjectRead, dependencies=[Depends(require_admin)])
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db)):
    new_project = model.Project(project_name=project.project_name)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

@app.get("/projects", response_model=list[schemas.ProjectRead], dependencies=[Depends(require_admin)])
def read_projects(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    projects=db.query(model.Project).offset(skip).limit(limit).all()
    return projects

@app.get("/projects", response_model=list[schemas.ProjectRead], dependencies=[Depends(require_admin)])
def read_projects(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(model.Project).offset(skip).limit(limit).all()

@app.post("/projects/assign", response_model=schemas.EmployeeProjectRead, dependencies=[Depends(require_admin)])
def assign_project(ep: schemas.EmployeeProjectCreate, db: Session = Depends(get_db)):
    # Step 1 & 2: Find employee by email
    employee = db.query(model.Employee).filter(model.Employee.employee_email == ep.employee_email).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Step 3: Check if relationship already exists for this employee and project
    existing_rel = db.query(model.Employee_Project_Relationship).filter(
        model.Employee_Project_Relationship.employee_id == employee.employee_id,
        model.Employee_Project_Relationship.project_id == ep.project_id
    ).first()

    if existing_rel:
        raise HTTPException(status_code=400, detail="This employee is already assigned to this project")

    # Step 4: Create new relationship
    new_ep_rel = model.Employee_Project_Relationship(
        employee_id=employee.employee_id,
        project_id=ep.project_id
    )
    db.add(new_ep_rel)
    db.commit()
    db.refresh(new_ep_rel)

    # Return data 
    return {
        "employe_project_id": new_ep_rel.employe_project_id,
        "employee_id": employee.employee_id,
        "project_id": ep.project_id,
        "employee_email": employee.employee_email,
        "assigned_time": new_ep_rel.assigned_time,
        "updated_time": new_ep_rel.updated_time,
    }

@app.get("/projects/{employee_id}", response_model=list[schemas.ProjectRead])
def get_projects_for_employee(employee_id: int, db: Session = Depends(get_db), user: model.Employee = Depends(get_current_user)):
    if user.employee_id != employee_id:
        require_admin(user, db)
    
    projects = db.query(model.Project).join(model.Employee_Project_Relationship).filter(
        model.Employee_Project_Relationship.employee_id == employee_id
    ).all()
    
    return projects
@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), user: model.Employee = Depends(require_admin)):
    project = db.query(model.Project).filter(model.Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # delete relationships
    db.query(model.Employee_Project_Relationship).filter_by(project_id=project_id).delete()

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}


#PROFILE-CRUD
@app.get("/profiles",response_model=list[schemas.ProfileRead], dependencies=[Depends(require_admin)])
def get_all_profiles(db: Session=Depends(get_db)):
    return db.query(model.Profile).all()

@app.post("/profiles",response_model=schemas.ProfileRead)
def create_profiles(profile: schemas.ProfileCreate, db: Session=Depends(get_db),user: model.Employee=Depends(get_current_user)  ):
    if user.employee_id!= profile.employee_id:
        require_admin(user, db)
    new_profile=model.Profile(**profile.dict())
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile

@app.get("/profiles/{employee_id}", response_model=schemas.ProfileRead)
def get_profile(employee_id: int, db: Session=Depends(get_db),user: model.Employee=Depends(get_current_user)):
    if user.employee_id!= employee_id:
        require_admin(user, db)
    profile=db.query(model.Profile).filter(model.Profile.employee_id==employee_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
    
#ROLES-CRUD
@app.get("/roles",response_model=list[schemas.RoleRead], dependencies=[Depends(get_current_user)])
def get_all_roles(db:Session=Depends(get_db)):
    return db.query(model.Role).all()

@app.post("/roles",response_model=schemas.RoleRead, dependencies=[Depends(get_current_user)])
def create_roles(roles: schemas.RoleCreate, db: Session=Depends(get_db)):
    new_role=model.Role(**roles.dict())
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role

@app.post("/roles/assign", response_model=schemas.EmployeeRoleRead, dependencies=[Depends(get_current_user)])
def assign_role(er: schemas.EmployeeRoleCreate, db: Session = Depends(get_db)):
    # Step 1: Find employee
    employee = db.query(model.Employee).filter(model.Employee.employee_email == er.employee_email).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Step 2: Find role
    role = db.query(model.Role).filter(model.Role.role_id == er.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Step 3: Check if relationship exists
    existing = db.query(model.Employee_Role_Relationship).filter(
        model.Employee_Role_Relationship.employee_id == employee.employee_id
    ).first()

    if existing:
        existing.role_id = er.role_id
        db.commit()
        db.refresh(existing)

        return {
            "employee_role_id": existing.employee_role_id,
            "employee_email": employee.employee_email,
            "role_id": existing.role_id,
            "assigned_time": existing.assigned_time,
            "updated_time": existing.updated_time,
        }

    # Step 4: Create new relationship
    new_assignment = model.Employee_Role_Relationship(
        employee_id=employee.employee_id,
        role_id=er.role_id
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)

    return {
        "employee_role_id": new_assignment.employee_role_id,
        "employee_email": employee.employee_email,
        "role_id": er.role_id,
        "assigned_time": new_assignment.assigned_time,
        "updated_time": new_assignment.updated_time,
    }


@app.get("/roles/{employee_id}", response_model=list[schemas.RoleRead])
def get_roles_for_employee(employee_id: int, db: Session=Depends(get_db), user: model.Employee = Depends(get_current_user)):
    if user.employee_id != employee_id:
        require_admin(user, db)
    roles=db.query(model.Role).join(model.Employee_Role_Relationship).filter(model.Employee_Role_Relationship.employee_id==employee_id).all()
    if not roles:
        raise HTTPException(status_code=404, detail="Roles not found for employee")
    return roles


@app.delete("/roles/{role_id}")
def delete_role(role_id: int, db:Session=Depends(get_db), user: model.Employee = Depends(get_current_user)):
    role=db.query(model.Role).filter(model.Role.role_id==role_id).first()
    db.query(model.Employee_Role_Relationship).filter_by(role_id=role_id).delete()
    db.delete(role)
    db.commit()
    return {"detail": "Role successfully deleted"}

#check-IN-CHECKOUT

@app.post("/checkin", response_model=schemas.CheckinCheckoutRead)
def checkin(user: model.Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    today = datetime.utcnow().date()

    # Look for any check-in today without a corresponding checkout
    existing = db.query(model.CheckinCheckout).filter(
        model.CheckinCheckout.employee_id == user.employee_id,
        model.CheckinCheckout.checkin_time >= datetime.combine(today, datetime.min.time()),
        model.CheckinCheckout.checkin_time <= datetime.combine(today, datetime.max.time()),
        model.CheckinCheckout.checkout_time == None
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Already checked in and not checked out today.")

    new_entry = model.CheckinCheckout(
        employee_id=user.employee_id,
        checkin_time=datetime.utcnow() 
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry



@app.post("/checkout", response_model=schemas.CheckinCheckoutRead)
def checkout(user: model.Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    # Find today's check-in without checkout
    entry = db.query(model.CheckinCheckout).filter(
        model.CheckinCheckout.employee_id == user.employee_id,
        model.CheckinCheckout.checkout_time == None
    ).order_by(model.CheckinCheckout.checkin_time.desc()).first()
    
    if not entry:
        raise HTTPException(status_code=400, detail="No active check-in found")
    
    entry.checkout_time = datetime.utcnow()

    # Calculate duration
    checkin_time = entry.checkin_time.replace(tzinfo=None)
    checkout_time = entry.checkout_time.replace(tzinfo=None)
    duration = checkout_time - checkin_time
    entry.work_duration = (datetime.min + duration).time()

    db.commit()
    db.refresh(entry)
    return entry


@app.get("/attendance/me", response_model=schemas.CheckinCheckoutRead | None)
def get_my_latest_attendance(user: model.Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    latest = db.query(model.CheckinCheckout).filter(
        model.CheckinCheckout.employee_id == user.employee_id
    ).order_by(model.CheckinCheckout.checkin_time.desc()).first()
    return latest
