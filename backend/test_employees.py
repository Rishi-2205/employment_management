from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta,timezone
from main import app, get_db,require_admin,get_current_user
from model import Employee, Employee_Role_Relationship, Role
from jose import jwt
from fastapi import HTTPException
client = TestClient(app)
def override_require_admin():
    class AdminUser:
        employee_id = 1
        employee_email = "admin@example.com"
        employee_role = "admin"
    return AdminUser()

# Create a fixture for the mock DB session
@pytest.fixture
def mock_db_session():
    return MagicMock()

# Dependency override for get_db
def override_get_db(mock_db):
    def _override():
        yield mock_db
    return _override

def test_create_employee_success(mock_db_session):
    # Simulate employee not existing
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None
    mock_db_session.query.return_value = mock_query

    fake_employee = Employee(
        employee_id=1,
        employee_name="Abhi",
        employee_email="abhi@example.com",
        employee_password="hashed_password123",
        employee_created_time=datetime.utcnow(),
        employee_updated_time=datetime.utcnow()
    )

    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    def refresh_side_effect(emp_obj):
        emp_obj.employee_id = fake_employee.employee_id
        emp_obj.employee_created_time = fake_employee.employee_created_time
        emp_obj.employee_updated_time = fake_employee.employee_updated_time

    mock_db_session.refresh.side_effect = refresh_side_effect

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)

    response = client.post(
        "/employees",
        json={
            "employee_name": "Abhi",
            "employee_email": "abhi@example.com",
            "employee_password": "password123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["employee_name"] == "Abhi"
    assert data["employee_email"] == "abhi@example.com"
    assert isinstance(data["employee_id"], int)

    app.dependency_overrides = {}

def test_create_employee_already_exists(mock_db_session):
    existing_employee = Employee(
        employee_id=2,
        employee_name="Bob",
        employee_email="bob@example.com",
        employee_password="hashed123",
        employee_created_time=datetime.utcnow(),
        employee_updated_time=datetime.utcnow()
    )

    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = existing_employee
    mock_db_session.query.return_value = mock_query

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)

    response = client.post(
        "/employees",
        json={
            "employee_name": "Bob",
            "employee_email": "bob@example.com",
            "employee_password": "password456"
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Employee already exists"

    app.dependency_overrides = {}

def test_login_success(mock_db_session):
    user = Employee(
        employee_id=1,
        employee_name="Abhi",
        employee_email="abhi@gmail.com",
        employee_password="hashedPass",
        employee_created_time=datetime.utcnow(),
        employee_updated_time=datetime.utcnow()
    )
    role_rel = Employee_Role_Relationship(employee_id=1, role_id=1)
    role = Role(role_id=1, role_name="Admin")

    # Create a mock query object that returns different results on subsequent calls to .first()
    mock_filter = MagicMock()
    mock_filter.first.side_effect = [user, role_rel, role]

    # Mock the query object to return our mock_filter when filter or filter_by is called
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_query.filter_by.return_value = mock_filter

    # Mock the session's query() method to return our mock_query
    mock_db_session.query.return_value = mock_query

    # Override the FastAPI dependency to use our mocked session
    app.dependency_overrides[get_db] = override_get_db(mock_db_session)

    # Patch verify_password to always return True
    with patch("main.verify_password", return_value=True):
        response = client.post(
            "/login",
            data={
                "username": "abhi@gmail.com",
                "password": "hashedpass"
            }
        )

    # Clean up overrides after test
    app.dependency_overrides = {}

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_user_not_found(mock_db_session):
    mock_filter=MagicMock()
    mock_filter.first.return_value=None

    mock_query=MagicMock()
    mock_query.filter.return_value=mock_filter
    mock_query.filter.return_value=mock_filter

    mock_db_session.query.return_value=mock_query

    app.dependency_overrides[get_db]=override_get_db(mock_db_session)
    response=client.post(
        "/login",
        data={
            "username":"notexists@gmail.com",
            "password":"anything"
        }
    )
    app.dependency_overrides={}
    assert response.status_code == 400
    assert response.json()["detail"]=="Incorrect username or password"

def test_login_wrong_password(mock_db_session):
    user=Employee(
        employee_id=1,
        employee_name="Abhi",
        employee_email="abhi@gmail.com",
        employee_password="hashedpass",
        employee_created_time=datetime.utcnow(),
        employee_updated_time=datetime.utcnow()
    )
    mock_filter=MagicMock()
    mock_filter.first.return_value=user

    mock_query=MagicMock()
    mock_query.filter.return_value=mock_filter
    mock_query.filter_by.return_value=mock_filter

    mock_db_session.query.return_value=mock_query

    app.dependency_overrides[get_db]=override_get_db(mock_db_session)

    with patch("main.verify_password",return_value=False):
        response = client.post(
            "/login",
            data={
                "username":"abhi@gmail.com",
                "password":"wrongpassword"
            }
        )

    app.dependency_overrides={}
    assert response.status_code==400
    assert response.json()["detail"]=="Incorrect username or password"

SECRET_KEY="MYSECRETKEY"
ALGORITHM="HS256"
def generate_token(employee_id: int, role:str):
    expire=datetime.utcnow()+timedelta(minutes=30)
    payload={
        "sub":str(employee_id),
        "role":role,
        "exp":expire
    }
    return jwt.encode(payload,SECRET_KEY,algorithm=ALGORITHM)

def test_read_employees_success_as_admin(mock_db_session):
    from model import Employee, Employee_Role_Relationship, Role
    from datetime import datetime

    # Mock employee returned by the /employees query
    mock_employee = MagicMock(spec=Employee)
    mock_employee.employee_id = 1
    mock_employee.employee_name = "Admin user"
    mock_employee.employee_email = "admin@gmail.com"
    mock_employee.employee_password = "hashed"
    mock_employee.employee_created_time = datetime.utcnow()
    mock_employee.employee_updated_time = datetime.utcnow()

    # Mock role relationship 
    mock_role_rel = MagicMock(spec=Employee_Role_Relationship)
    mock_role_rel.employee_id = 1
    mock_role_rel.role_id = 1

    # Mock role object 
    mock_role = MagicMock(spec=Role)
    mock_role.role_id = 1
    mock_role.role_name = "admin"

    # This mock_query will return different things based on filter criteria:
    def query_side_effect(model):
        query_mock = MagicMock()

        # When filtering employees for /employees endpoint
        if model == Employee:
            query_mock.offset.return_value.limit.return_value.all.return_value = [mock_employee]
        
        # When querying Employee_Role_Relationship inside require_admin
        elif model == Employee_Role_Relationship:
            query_mock.filter.return_value.first.return_value = mock_role_rel

        # When querying Role inside require_admin
        elif model == Role:
            query_mock.filter.return_value.first.return_value = mock_role
        
        else:
            query_mock.filter.return_value.first.return_value = None

        return query_mock

    mock_db_session.query.side_effect = query_side_effect

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)

    token = generate_token(1, "admin")
    response = client.get(
        "/employees",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert result[0]["employee_email"] == "admin@gmail.com"

    app.dependency_overrides = {}

def test_read_their_employee_record(mock_db_session):
    employee=Employee(
        employee_id=1,
        employee_name="Test User",
        employee_email="test@gmail.com",
        employee_password="hashedpass",
        employee_created_time=datetime.utcnow(),
        employee_updated_time=datetime.utcnow()
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value=employee
    app.dependency_overrides[get_db]=override_get_db(mock_db_session)

    token=generate_token(1,"user")

    response=client.get(
        "/employees/1",
        headers={"Authorization":f"Bearer {token}"}
    )
    assert response.status_code==200
    data=response.json()
    assert data["employee_email"]=="test@gmail.com"
    app.dependency_overrides={}

def test_delete_employee_success_as_admin(mock_db_session):
    # Mock the employee to be deleted
    employee = Employee(
        employee_id=1,
        employee_name="Test User",
        employee_email="test@example.com",
        employee_password="hashedpass",
        employee_created_time=datetime.utcnow(),
        employee_updated_time=datetime.utcnow()
    )

    # Role resolution logic inside require_admin
    role_rel = Employee_Role_Relationship(employee_id=1, role_id=1)
    role = Role(role_id=1, role_name="admin")

    def query_side_effect(model):
        query_mock = MagicMock()

        if model == Employee:
            query_mock.filter.return_value.first.return_value = employee
        elif model == Employee_Role_Relationship:
            query_mock.filter.return_value.first.return_value = role_rel
        elif model == Role:
            query_mock.filter.return_value.first.return_value = role
        else:
            query_mock.filter.return_value.first.return_value = None

        return query_mock

    mock_db_session.query.side_effect = query_side_effect

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)

    token = generate_token(1, "admin")

    response = client.delete(
        "/employees/1",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"detail": "Employee deleted"}

    app.dependency_overrides = {}

def test_delete_employee_not_found(mock_db_session):
    # Simulate no employee found
    def query_side_effect(model):
        query_mock = MagicMock()

        if model == Employee:
            query_mock.filter.return_value.first.return_value = None  # No employee
        elif model == Employee_Role_Relationship:
            query_mock.filter.return_value.first.return_value = Employee_Role_Relationship(employee_id=1, role_id=1)
        elif model == Role:
            query_mock.filter.return_value.first.return_value = Role(role_id=1, role_name="admin")
        else:
            query_mock.filter.return_value.first.return_value = None

        return query_mock

    mock_db_session.query.side_effect = query_side_effect

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)

    token = generate_token(1, "admin")

    response = client.delete(
        "/employees/999",  # ID that doesn't exist
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}

    app.dependency_overrides = {}

    #--project section--

def test_create_project_success(mock_db_session):
    from model import Project
    from datetime import datetime, timezone

    mock_project = Project(
        project_id=1,
        project_name="First project",
        created_time=datetime.now(timezone.utc),
        updated_time=datetime.now(timezone.utc)
    )

    def refresh_side_effect(proj):
        proj.project_id = mock_project.project_id
        proj.created_time = mock_project.created_time
        proj.updated_time = mock_project.updated_time

    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.side_effect = refresh_side_effect

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)
    app.dependency_overrides[require_admin] = lambda: None

    token = generate_token(1, "admin")

    response = client.post(
        "/projects",
        headers={"Authorization": f"Bearer {token}"},
        json={"project_name": "First project"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "First project"
    assert "project_id" in data
    assert isinstance(data["project_id"], int)

    app.dependency_overrides = {}

def test_nonAdmin_access(mock_db_session):
    app.dependency_overrides[get_db]=override_get_db(mock_db_session)

    app.dependency_overrides[require_admin]=lambda:(_ for _ in ()).throw(
        HTTPException(status_code=403,detail="Admin privileges required")
    )
    token=generate_token(2,"user")

    response=client.post(
        "/projects",
        headers={"Authorization":f"Bearer {token}"},
        json={"project_name":"Unauthorized project"}
    )
    assert response.status_code==403
    assert response.json()["detail"]=="Admin privileges required"

    app.dependency_overrides={}

def test_read_projects_success_admin(mock_db_session):
    from model import Project
    mock_projects=[
        Project(
            project_id=1,
            project_name="First project",
            created_time=datetime.now(timezone.utc),
            updated_time=datetime.now(timezone.utc)
        ),
        Project(
            project_id=2,
            project_name="Second project",
            created_time=datetime.now(timezone.utc),
            updated_time=datetime.now(timezone.utc)
        )
    ]

    mock_db_session.query.return_value.offset.return_value.limit.return_value.all.return_value=mock_projects
    app.dependency_overrides[get_db]=override_get_db(mock_db_session)
    app.dependency_overrides[require_admin]=lambda:None

    token=generate_token(1,"admin")

    response=client.get(
        "/projects",
        headers={"Authorization":f"Bearer {token}"}
    )

def test_project_nonAdmin_access(mock_db_session):
    app.dependency_overrides[get_db]=override_get_db(mock_db_session)
    app.dependency_overrides[require_admin]=lambda: (_ for _ in ()).throw(
        HTTPException(status_code=403, detail="Admin privileges required")
    )
    token=generate_token(2,"user")

    response=client.get(
        "/projects",
        headers={
            "Authorization":f"Bearer {token}"
        }
    )
    assert response.status_code==403
    assert response.json()["detail"]=="Admin privileges required"

    app.dependency_overrides={}

def test_own_access_for_theirOwn_project(mock_db_session):
    import model
    from model import Project
    employee_id=2
    mock_projects=[
        Project(
            project_id=1,
            project_name="First project",
            created_time=datetime.now(timezone.utc),
            updated_time=datetime.now(timezone.utc)
        ),
        Project(
            project_id=2,
            project_name="Second project",
            created_time=datetime.now(timezone.utc),
            updated_time=datetime.now(timezone.utc)
        )

    ]
    mock_db_session.query.return_value.join.return_value.filter.return_value.all.return_value=mock_projects
    app.dependency_overrides[get_db]=override_get_db(mock_db_session)

    app.dependency_overrides[get_current_user]=lambda: model.Employee(employee_id=2)

    token=generate_token(2,"user")
    response=client.get(
        f"/projects/{employee_id}",
        headers={"Authorization":f"Bearer {token}"}
    )
    assert response.status_code==200
    data=response.json()
    assert len(data)==2
    assert data[0]["project_name"]=="First project"
    assert data[1]["project_name"]=="Second project"

    app.dependency_overrides={}

def test_nonAdmin_project_access(mock_db_session):
    import model
    app.dependency_overrides[get_db]=override_get_db(mock_db_session)

    app.dependency_overrides[get_current_user]=lambda:model.Employee(employee_id=2)
    app.dependency_overrides[require_admin]=lambda user,db:(_ for _ in ()).throw(
        HTTPException(status_code=403,detail="Admin privileges required")
    )

    token=generate_token(2,"user")
    response=client.get(
        "/projects/3",
        headers={"Authorization":f"Bearer {token}"}
    )

    assert response.status_code==403
    assert response.json()
def test_assign_project_success(mock_db_session):
    from model import Employee, Employee_Project_Relationship
    from datetime import datetime, timezone

    # Setup test data
    employee = Employee(
        employee_id=1,
        employee_name="Abi",
        employee_email="abi@gmail.com",
        employee_password="hashedpass",
        employee_created_time=datetime.now(timezone.utc),
        employee_updated_time=datetime.now(timezone.utc)
    )

    # Mock the DB query behavior
    def query_side_effect(model):
        query_mock = MagicMock()

        if model.__name__ == "Employee":
            query_mock.filter.return_value.first.return_value = employee
        elif model.__name__ == "Employee_Project_Relationship":
            query_mock.filter.return_value.first.return_value = None
        return query_mock

    mock_db_session.query.side_effect = query_side_effect
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    def refresh_side_effect(rel):
        rel.employe_project_id = 123
        rel.assigned_time = datetime.now(timezone.utc)
        rel.updated_time = datetime.now(timezone.utc)

    mock_db_session.refresh.side_effect = refresh_side_effect

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)
    app.dependency_overrides[require_admin] = lambda: None

    token = generate_token(1, "admin")

    response = client.post(
        "/projects/assign",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_email": "abi@gmail.com",
            "project_id": 101
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "employe_project_id" in data
    assert "assigned_time" in data
    assert "updated_time" in data

    app.dependency_overrides = {}

def test_assign_project_employee_not_found(mock_db_session):
    def query_side_effect(model):
        query_mock = MagicMock()
        if model.__name__ == "Employee":
            query_mock.filter.return_value.first.return_value = None
        return query_mock

    mock_db_session.query.side_effect = query_side_effect

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)
    app.dependency_overrides[require_admin] = lambda: None

    token = generate_token(1, "admin")

    response = client.post(
        "/projects/assign",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_email": "nonexistent@example.com",
            "project_id": 101
        }
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found"

    app.dependency_overrides = {}

def test_assign_project_already_exists(mock_db_session):
    from model import Employee, Employee_Project_Relationship
    employee = Employee(employee_id=1, employee_email="abi@example.com")
    relationship = Employee_Project_Relationship(employee_id=1, project_id=101)

    def query_side_effect(model):
        query_mock = MagicMock()
        if model.__name__ == "Employee":
            query_mock.filter.return_value.first.return_value = employee
        elif model.__name__ == "Employee_Project_Relationship":
            query_mock.filter.return_value.first.return_value = relationship
        return query_mock

    mock_db_session.query.side_effect = query_side_effect

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)
    app.dependency_overrides[require_admin] = lambda: None

    token = generate_token(1, "admin")

    response = client.post(
        "/projects/assign",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "employee_email": "abi@example.com",
            "project_id": 101
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "This employee is already assigned to this project"

    app.dependency_overrides = {}

def test_deleteProject_success(mock_db_session):
    import model
    from model import Project,Employee_Project_Relationship
    
    project_id=11
    project_obj=Project(
        project_id=project_id,
        project_name="FirstProject"
    )
    def query_side_effect(model):
        query_mock=MagicMock()
        if model==Project:
            query_mock.filter.return_value.first.return_value=project_obj
        elif model==Employee_Project_Relationship:
            query_mock.filter.return_value.delete.return_value=3
        return query_mock
    mock_db_session.query.side_effect=query_side_effect
    mock_db_session.delete.return_value=None
    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[require_admin] = override_require_admin
    token = generate_token(1, "admin")

    response = client.delete(
        f"/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Project deleted successfully"}

    # Clean up
    app.dependency_overrides = {}
def test_delete_project_not_found(mock_db_session):
    import model
    from model import Project
    project_id = 999
    # Mock query returns None => project not found
    def query_side_effect(model):
        query_mock = MagicMock()
        if model == Project:
            query_mock.filter.return_value.first.return_value = None
        return query_mock

    mock_db_session.query.side_effect = query_side_effect

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[require_admin] = override_require_admin

    response = client.delete(f"/projects/{project_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}

    app.dependency_overrides = {}

def test_delete_project_unauthorized(mock_db_session):
    project_id = 42

    # Override require_admin to raise HTTPException simulating unauthorized access
    from fastapi import HTTPException

    def unauthorized_admin():
        raise HTTPException(status_code=403, detail="Not authorized")

    app.dependency_overrides[get_db] = lambda: mock_db_session
    app.dependency_overrides[require_admin] = unauthorized_admin

    response = client.delete(f"/projects/{project_id}")

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized"}

    app.dependency_overrides = {}

#--Roles--
def test_create_role_success(mock_db_session):
    from model import Role

    mock_role = Role(
    role_id=1,
    role_name="Manager",
    role_created_time=datetime.now(timezone.utc),
    role_updated_time=datetime.now(timezone.utc),
    )

    def refresh_side_effect(role_obj):
       role_obj.role_id = mock_role.role_id
       role_obj.role_created_time = mock_role.role_created_time
       role_obj.role_updated_time = mock_role.role_updated_time
 

    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.side_effect = refresh_side_effect

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)
    app.dependency_overrides[require_admin] = override_require_admin

    token = generate_token(1, "admin")

    response = client.post(
        "/roles",
        headers={"Authorization": f"Bearer {token}"},
        json={"role_name": "Manager"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["role_name"] == "Manager"
    assert "role_id" in data

    app.dependency_overrides = {}

def test_get_roles_success(mock_db_session):
    from model import Role
    mock_roles=[
        Role(
            role_id=1,
            role_name="Admin",
            role_created_time=datetime.now(timezone.utc),
            role_updated_time=datetime.now(timezone.utc)
        ),
        Role(
            role_id=2,
            role_name="Manager",
            role_created_time=datetime.now(timezone.utc),
            role_updated_time=datetime.now(timezone.utc)
        )
    ]
    mock_db_session.query.return_value.all.return_value=mock_roles

    app.dependency_overrides[get_db]=override_get_db(mock_db_session)
    app.dependency_overrides[override_require_admin]=override_require_admin

    token=generate_token(1,"admin")
    response = client.get(
        "/roles",
         headers={"Authorization": f"Bearer {token}"}
     )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["role_name"] == "Admin"
    assert data[1]["role_name"] == "Manager"

    app.dependency_overrides = {}

def test_assign_role_to_user_success(mock_db_session):
    from model import Employee, Role, Employee_Role_Relationship

    employee = Employee(employee_id=2, employee_email="jane@example.com")
    role = Role(role_id=3, role_name="Manager")

    # Define what the DB query should return for each model
    def query_side_effect(model):
        query_mock = MagicMock()
        if model == Employee:
            query_mock.filter.return_value.first.return_value = employee
        elif model == Role:
            query_mock.filter.return_value.first.return_value = role
        elif model == Employee_Role_Relationship:
            query_mock.filter.return_value.first.return_value = None
        return query_mock

    mock_db_session.query.side_effect = query_side_effect
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    # This object is what gets returned by the endpoint as response
    def refresh_side_effect(obj):
        obj.employee_role_id = 1001
        obj.role_id = role.role_id
        obj.employee_email = employee.employee_email
        obj.assigned_time = datetime.now(timezone.utc)
        obj.updated_time = datetime.now(timezone.utc)

    mock_db_session.refresh.side_effect = refresh_side_effect

    # Set up FastAPI overrides
    app.dependency_overrides[get_db] = override_get_db(mock_db_session)
    app.dependency_overrides[require_admin] = override_require_admin

    token = generate_token(1, "admin")

    response = client.post(
        "/roles/assign",
        headers={"Authorization": f"Bearer {token}"},
        json={"employee_email": "jane@example.com", "role_id": 3}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["employee_email"] == "jane@example.com"
    assert data["role_id"] == 3
    assert isinstance(data["employee_role_id"], int)
    assert isinstance(data["assigned_time"], str)
    assert isinstance(data["updated_time"], str)

    # Clean up overrides
    app.dependency_overrides = {}

def test_get_roles_as_self_success():
    mock_db_session = MagicMock()

    # Sample roles with required datetime fields
    now = datetime.now(timezone.utc)
    role1 = Role(role_id=1, role_name="Admin", role_created_time=now, role_updated_time=now)
    role2 = Role(role_id=2, role_name="Manager", role_created_time=now, role_updated_time=now)
    roles = [role1, role2]

    mock_user = Employee(employee_id=1, employee_email="user@example.com")

    query_mock = MagicMock()
    query_mock.join.return_value.filter.return_value.all.return_value = roles
    mock_db_session.query.return_value = query_mock

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    token = generate_token(1, "Admin")

    response = client.get(
        "/roles/1",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["role_id"] == 1
    assert data[0]["role_name"] == "Admin"
    assert "role_created_time" in data[0]
    assert "role_updated_time" in data[0]

    app.dependency_overrides = {}

def test_get_roles_as_admin_success():
    mock_db_session = MagicMock()

    now = datetime.now(timezone.utc)
    role = Role(role_id=1, role_name="Admin", role_created_time=now, role_updated_time=now)
    mock_user = Employee(employee_id=99, employee_email="admin@example.com")  # Admin user

    query_mock = MagicMock()
    query_mock.join.return_value.filter.return_value.all.return_value = [role]
    mock_db_session.query.return_value = query_mock

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    token = generate_token(99, "Admin")

    # Patch the require_admin used *inside the module where the route is defined*
    with patch("main.require_admin", return_value=None):  # 👈 adjust "main" to your route module name
        response = client.get(
            "/roles/1",
            headers={"Authorization": f"Bearer {token}"}
        )

    assert response.status_code == 200
    assert response.json()[0]["role_id"] == 1

    app.dependency_overrides = {}
def test_get_roles_not_found():
    mock_db_session = MagicMock()
    mock_user = Employee(employee_id=1, employee_email="user@example.com")

    query_mock = MagicMock()
    query_mock.join.return_value.filter.return_value.all.return_value = []
    mock_db_session.query.return_value = query_mock

    app.dependency_overrides[get_db] = override_get_db(mock_db_session)
    app.dependency_overrides[get_current_user] = lambda: mock_user

    token = generate_token(1, "Admin")

    response = client.get(
        "/roles/1",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Roles not found for employee"

    app.dependency_overrides = {}

def test_checkin_success():
    from model import CheckinCheckout
    now = datetime.now(timezone.utc)

    mock_user = Employee(employee_id=1, employee_email="test@example.com")

    # Mock the DB query to return no existing check-in for today
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.first.return_value = None

    mock_db = MagicMock()
    mock_db.query.return_value = query_mock

    # Mock CheckinCheckout instance
    new_checkin = CheckinCheckout(employee_id=1, checkin_time=now)
    
    # Simulate refresh setting the ID (to pass validation)
    def fake_refresh(obj):
        obj.employee_checincheckout_id = 123  # Must be int, not None
        return obj

    mock_db.add.side_effect = lambda x: None
    mock_db.commit.side_effect = lambda: None
    mock_db.refresh.side_effect = fake_refresh

    # Override FastAPI dependencies
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    token = generate_token(1, "Employee")

    response = client.post(
        "/checkin",
        headers={"Authorization": f"Bearer {token}"}
    )

    print("Response JSON:", response.json())

    assert response.status_code == 200
    assert response.json()["employee_id"] == 1
    assert response.json()["employee_checincheckout_id"] == 123

def test_checkin_already_exists():
    from model import CheckinCheckout
    mock_user = Employee(employee_id=1, employee_email="test@example.com")

    existing_checkin = CheckinCheckout(
        employee_id=1,
        checkin_time=datetime.now(timezone.utc)
    )

    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.first.return_value = existing_checkin  # Already checked in

    mock_db = MagicMock()
    mock_db.query.return_value = query_mock

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    token = generate_token(1, "Employee")

    response = client.post(
        "/checkin",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Already checked in and not checked out today."

def test_checkout_success():
    from model import CheckinCheckout
    from datetime import datetime, timedelta, timezone

    mock_user = Employee(employee_id=1, employee_email="test@example.com")

    # Mock existing check-in entry without checkout
    checkin_time = datetime.now(timezone.utc) - timedelta(hours=8)
    existing_entry = CheckinCheckout(
        employee_id=1,
        checkin_time=checkin_time,
        checkout_time=None,
        work_duration=None
    )
    existing_entry.employee_checincheckout_id = 123  # Add a fake ID

    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.first.return_value = existing_entry

    mock_db = MagicMock()
    mock_db.query.return_value = query_mock
    mock_db.commit.side_effect = lambda: None
    mock_db.refresh.side_effect = lambda x: x

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    token = generate_token(1, "Employee")

    response = client.post(
        "/checkout",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["employee_id"] == 1
    assert data["checkout_time"] is not None
    assert data["work_duration"] is not None

def test_checkout_no_active_checkin():
    mock_user = Employee(employee_id=2, employee_email="test2@example.com")

    # Simulate no check-in found
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.first.return_value = None

    mock_db = MagicMock()
    mock_db.query.return_value = query_mock

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    token = generate_token(2, "Employee")

    response = client.post(
        "/checkout",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "No active check-in found"

def test_get_my_latest_attendance_success():
    from model import CheckinCheckout
    from datetime import datetime, timezone

    mock_user = Employee(employee_id=1, employee_email="test@example.com")

    attendance_record = CheckinCheckout(
        employee_checincheckout_id=101,
        employee_id=1,
        checkin_time=datetime.now(timezone.utc),
        checkout_time=datetime.now(timezone.utc),
        work_duration=(datetime.min + timedelta(hours=8)).time()
    )

    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.first.return_value = attendance_record

    mock_db = MagicMock()
    mock_db.query.return_value = query_mock

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    token = generate_token(1, "Employee")

    response = client.get(
        "/attendance/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["employee_id"] == 1
    assert data["checkin_time"] is not None

def test_get_my_latest_attendance_none():
    mock_user = Employee(employee_id=2, employee_email="test2@example.com")

    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.order_by.return_value = query_mock
    query_mock.first.return_value = None  # No records

    mock_db = MagicMock()
    mock_db.query.return_value = query_mock

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user

    token = generate_token(2, "Employee")

    response = client.get(
        "/attendance/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json() is None

def test_get_all_profiles_admin_success():
    from model import Profile
    from datetime import date, datetime, timezone
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    # Mock admin user
    mock_user = SimpleNamespace(
        employee_id=1,
        employee_email="admin@gmail.com",
        employee_role="Admin"
    )

    # Mock profiles returned by the DB
    profiles = [
        Profile(
            employee_profile_id=1,
            employee_id=1,
            first_name="Abi",
            last_name="Shek",
            date_of_joining=date.today(),
            created_time=datetime.now(timezone.utc),
            updated_time=datetime.now(timezone.utc)
        )
    ]

    # Mock database session
    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = profiles

    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: None  # ✅ Bypass admin check

    # Auth token
    token = generate_token(1, "Admin")

    # Make the GET request
    response = client.get("/profiles", headers={"Authorization": f"Bearer {token}"})

    # Assertions
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["first_name"] == "Abi"

    # Clean up dependency overrides
    app.dependency_overrides.clear()

def test_create_profile_success_user_own_profile():
    from datetime import date, datetime, timezone
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    mock_user = SimpleNamespace(employee_id=2, employee_email="user@gmail.com", employee_role="User")

    profile_data = {
        "employee_id": 2,
        "first_name": "John",
        "last_name": "Doe",
        "age": 30,
        "address": "123 Street",
        "father_name": "Father Doe",
        "mother_name": "Mother Doe",
        "employee_profile_role": "Developer",
        "date_of_joining": str(date.today())
    }

    # Define dummy profile to simulate ORM response after refresh
    class DummyProfile:
        def __init__(self):
            self.employee_profile_id = 101
            self.employee_id = 2
            self.first_name = "John"
            self.last_name = "Doe"
            self.age = 30
            self.address = "123 Street"
            self.father_name = "Father Doe"
            self.mother_name = "Mother Doe"
            self.employee_profile_role = "Developer"
            self.date_of_joining = date.today()
            self.created_time = datetime.now(timezone.utc)
            self.updated_time = datetime.now(timezone.utc)

    dummy_profile = DummyProfile()

    # DB mock
    mock_db = MagicMock()
    mock_db.add.return_value = None
    mock_db.commit.return_value = None

    # Patch db.refresh to mutate the object as if DB had populated the fields
    def mock_refresh(obj):
        for attr in vars(dummy_profile):
            setattr(obj, attr, getattr(dummy_profile, attr))
        return obj

    mock_db.refresh.side_effect = mock_refresh

    # Dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    token = generate_token(2, "User")

    response = client.post(
        "/profiles",
        json=profile_data,
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    response_json = response.json()
    assert response_json["employee_profile_id"] == 101
    assert response_json["first_name"] == "John"

def test_create_profile_for_another_user_denied():
    from types import SimpleNamespace
    from datetime import date
    from unittest.mock import MagicMock

    mock_user = SimpleNamespace(employee_id=2, employee_email="user@gmail.com", employee_role="User")

    profile_data = {
        "employee_id": 3,  # Different from mock_user.employee_id
        "first_name": "Jane",
        "last_name": "Smith",
        "age": 28,
        "address": "456 Street",
        "father_name": "Father Smith",
        "mother_name": "Mother Smith",
        "employee_profile_role": "Analyst",
        "date_of_joining": str(date.today())
    }

    mock_db = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    token = generate_token(2, "User")
    response = client.post("/profiles", json=profile_data, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403  # Forbidden

    app.dependency_overrides.clear()

def test_get_own_profile_success():
    from model import Profile
    from datetime import date, datetime, timezone
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    mock_user = SimpleNamespace(employee_id=5, employee_email="user5@gmail.com", employee_role="User")

    profile = Profile(
        employee_profile_id=99,
        employee_id=5,
        first_name="Sam",
        last_name="Patel",
        date_of_joining=date.today(),
        created_time=datetime.now(timezone.utc),
        updated_time=datetime.now(timezone.utc)
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = profile

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    token = generate_token(5, "User")
    response = client.get("/profiles/5", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["first_name"] == "Sam"

    app.dependency_overrides.clear()

def test_get_other_user_profile_denied():
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    mock_user = SimpleNamespace(employee_id=10, employee_email="user10@gmail.com", employee_role="User")

    mock_db = MagicMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    token = generate_token(10, "User")
    response = client.get("/profiles/11", headers={"Authorization": f"Bearer {token}"})  # Different ID

    assert response.status_code == 403

    app.dependency_overrides.clear()

