import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from model import Base, Employee, Role, Employee_Role_Relationship
from authpassword import hash_password
from main import app, get_db

# Your test database URL (make sure test_employe_db exists)
TEST_DATABASE_URL = "postgresql://postgres:Abhi%402003@localhost:5432/test_employe_db"

# Create SQLAlchemy engine for the test DB
engine = create_engine(TEST_DATABASE_URL)

# Create a configured "Session" class
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables in test DB before running tests
Base.metadata.create_all(bind=engine)

# Dependency override: use the test DB session instead of production DB session
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override the dependency in the FastAPI app
app.dependency_overrides[get_db] = override_get_db

# Pytest fixture for FastAPI TestClient
@pytest.fixture(scope="module")  #scope=module to define that we have to create only one client for all the test functions i am going to write
def client():
    with TestClient(app) as c:
        yield c

# Fixture to setup a test user with role
@pytest.fixture(scope="module")
def setup_test_user():
    db = TestingSessionLocal()
    try:
        # Clean up existing data for clean test run
        db.query(Employee_Role_Relationship).delete()
        db.query(Employee).delete()
        db.query(Role).delete()
        db.commit()

        # Create admin role
        role = Role(role_name="admin")
        db.add(role)
        db.commit()
        db.refresh(role)

        # Create test user
        user = Employee(
            employee_name="Test User",
            employee_email="testuser@example.com",
            employee_password=hash_password("password123")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Assign role to user
        rel = Employee_Role_Relationship(
            employee_id=user.employee_id,
            role_id=role.role_id
        )
        db.add(rel)
        db.commit()

        return {"email": user.employee_email, "password": "password123"}
    finally:
        db.close()

@pytest.fixture(scope="module")
def setup_test_admin_user():
    db = TestingSessionLocal()
    try:
        # Clean slate
       

        # Create admin role
        role = Role(role_name="admin")
        db.add(role)
        db.commit()
        db.refresh(role)

        # Create admin user
        admin_user = Employee(
            employee_name="Admin User",
            employee_email="admin@example.com",
            employee_password=hash_password("adminpass")
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # Assign admin role
        rel = Employee_Role_Relationship(
            employee_id=admin_user.employee_id,
            role_id=role.role_id
        )
        db.add(rel)
        db.commit()

        return {"email": admin_user.employee_email, "password": "adminpass"}
    finally:
        db.close()


def test_login_success(client: TestClient, setup_test_user):
    response = client.post(
        "/login",
        data={
            "username": setup_test_user["email"],
            "password": setup_test_user["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_failure_wrong_password(client: TestClient, setup_test_user):
    response = client.post(
        "/login",
        data={
            "username": setup_test_user["email"],
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect username or password"

#employeePost

def test_create_employee_success(client: TestClient):
    # First creation should succeed
    response = client.post(
        "/employees",
        json={
            "employee_name": "Abi",
            "employee_email": "abi@example.com",
            "employee_password": "abipassword"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["employee_email"] == "abi@example.com"
    assert "employee_id" in data

def test_create_employee_duplicate_email(client: TestClient):
    # Try to create the same employee again
    response = client.post(
        "/employees",
        json={
            "employee_name": "Abi",
            "employee_email": "abi@example.com",
            "employee_password": "abipassword"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Employee already exists"

#employeeGet
def test_read_employee_self_access(client: TestClient, setup_test_user):
    # Login and get token
    login_response = client.post(
        "/login",
        data={
            "username": setup_test_user["email"],
            "password": setup_test_user["password"]
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Decode token to get user ID (or fetch by email)
    from database import SessionLocal
    from model import Employee

    db = SessionLocal()
    user = db.query(Employee).filter(Employee.employee_email == setup_test_user["email"]).first()
    db.close()

    # Now request the employee's own record
    user_response = client.get(
        f"/employees/{user.employee_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert user_response.status_code == 200
    data = user_response.json()
    assert data["employee_email"] == setup_test_user["email"]

def test_read_employee_unauthorized_other_user(client: TestClient):
    # Create second user (non-admin)
    response = client.post(
        "/employees",
        json={
            "employee_name": "Bob",
            "employee_email": "bob@example.com",
            "employee_password": "bobpass"
        }
    )
    assert response.status_code == 200
    bob_id = response.json()["employee_id"]

    # Login as Bob
    login_response = client.post(
        "/login",
        data={"username": "bob@example.com", "password": "bobpass"}
    )
    token = login_response.json()["access_token"]

    # Bob tries to access Test User (employee_id = 1)
    response = client.get(
        "/employees/1",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "No role assigned"

def test_read_employee_not_found(client: TestClient, setup_test_user):
    # Login as admin again
    login_response = client.post(
        "/login",
        data={
            "username": setup_test_user["email"],
            "password": setup_test_user["password"]
        }
    )
    token = login_response.json()["access_token"]

    # Try to fetch a non-existent employee
    response = client.get(
        "/employees/99999",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found"

def test_update_employee_self(client: TestClient, setup_test_user):
    # Login as test user
    login_response = client.post(
        "/login",
        data={"username": setup_test_user["email"], "password": setup_test_user["password"]}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Get employee ID from DB
    from database import SessionLocal
    from model import Employee
    db = SessionLocal()
    user = db.query(Employee).filter(Employee.employee_email == setup_test_user["email"]).first()
    db.close()

    # Update self
    response = client.put(
        f"/employees/{user.employee_id}",
        json={"employee_name": "Updated User", "employee_email": "updated@example.com"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["employee_name"] == "Updated User"
    assert data["employee_email"] == "updated@example.com"

def test_delete_employee_as_admin(client: TestClient, setup_test_admin_user):
    # setup_test_admin_user should create and return an admin user credentials

    # Login as admin
    login_response = client.post(
        "/login",
        data={
            "username": setup_test_admin_user["email"],
            "password": setup_test_admin_user["password"]
        }
    )
    token = login_response.json()["access_token"]

    # Create a new employee to delete
    create_response = client.post(
        "/employees",
        json={
            "employee_name": "ToDelete",
            "employee_email": "todelete@example.com",
            "employee_password": "deletepass"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    employee_id = create_response.json()["employee_id"]

    # Delete the employee
    delete_response = client.delete(
        f"/employees/{employee_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["detail"] == "Employee deleted"

    # Confirm employee no longer exists
    get_response = client.get(
        f"/employees/{employee_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_response.status_code == 404


#Roles crud
def test_get_all_roles_requires_auth(client):
    # Unauthenticated should be denied
    response = client.get("/roles")
    assert response.status_code == 401  # missing token

def test_create_role_and_get_all(client, setup_test_admin_user):
    # Login as admin with correct keys
    login = client.post("/login", data={
        "username": setup_test_admin_user["email"],
        "password": setup_test_admin_user["password"]
    })
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]

    role_name = "tester"
    resp = client.post("/roles", json={"role_name": role_name},
                       headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    created = resp.json()
    assert created["role_name"] == role_name

    resp2 = client.get("/roles", headers={"Authorization": f"Bearer {token}"})
    names = [r["role_name"] for r in resp2.json()]
    assert role_name in names

def login_and_get_token(client, user_credentials):
    response = client.post(
        "/login",
        data={
            "username": user_credentials["email"],
            "password": user_credentials["password"]
        }
    )
    assert response.status_code == 200
    return response.json()["access_token"]


import uuid
def test_create_role_success(client,setup_test_admin_user):
    token=login_and_get_token(client,setup_test_admin_user)
    unique_role=f"Role_{uuid.uuid4().hex[:6]}"
    response=client.post(
        "/roles",
        json={"role_name":unique_role},
        headers={"Authorization":f"Bearer {token}"}
    )

    assert response.status_code==200
    data=response.json()
    assert data["role_name"]==unique_role
    assert "role_id" in data

def test_create_role_unauth(client):
    response=client.post(
        "/roles",
        json={"role_name": "HackerRole"}
    )
    assert response.status_code==401

def test_create_role_unnamed(client,setup_test_admin_user):
    token=login_and_get_token(client,setup_test_admin_user)

    response=client.post(
        "/roles",
        json={},
        headers={"Authorization":f"Bearer {token}"}
    )
    assert response.status_code==422

def test_create_project_success(client,setup_test_admin_user):
    login_resp=client.post(
        "/login",
        data={
            "username":setup_test_admin_user["email"],
            "password":setup_test_admin_user["password"]
        }
    )
    assert login_resp.status_code==200
    token=login_resp.json()["access_token"]

    response=client.post(
        "/projects",
        json={
            "project_name":"first project"
        },
        headers={
            "Authorization":f"Bearer {token}"
        }
    )
    assert response.status_code==200
    data=response.json()
    assert data["project_name"]=="first project"
    assert "project_id" in data

def test_unauth_project_post(client):
    response=client.post(
        "/projects",
        json={
            "project_name":"first_project"
        }
    )
    assert response.status_code==401

def test_project_get_success(client,setup_test_admin_user):
    login_resp=client.post(
        "/login",
        data={
            "username":setup_test_admin_user["email"],
            "password":setup_test_admin_user["password"]
        }
    )
    assert login_resp.status_code==200
    token=login_resp.json()["access_token"]

    for i in range(3):
        response=client.post(
            "projects",
            json={
                "project_name":f"project no {i}"
            },
            headers={
                "Authorization":f"Bearer {token}"
            }
        )
        assert response.status_code==200

    response=client.get(
        "/projects",
        headers={
            "Authorization":f"Bearer {token}"
        }
    )
    assert response.status_code==200
    data=response.json()
    assert isinstance(data, list)
    assert len(data) >= 3  # more than 3 if already tested
    for project in data:
        assert "project_id" in project
        assert "project_name" in project

def test_delete_role_success(client, setup_test_admin_user):
    token = login_and_get_token(client, setup_test_admin_user)

    # Create a role to delete
    response = client.post(
        "/roles",
        json={"role_name": "TempRoleToDelete"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    role_id = response.json()["role_id"]

    # Delete the role
    del_response = client.delete(
        f"/roles/{role_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert del_response.status_code == 200
    assert del_response.json()["detail"] == "Role successfully deleted"

def test_delete_project_success(client, setup_test_admin_user):
    token = login_and_get_token(client, setup_test_admin_user)

    # Create a project to delete
    create_resp = client.post(
        "/projects",
        json={"project_name": "Temporary Project"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert create_resp.status_code == 200
    project_id = create_resp.json()["project_id"]

    # Now delete the project
    delete_resp = client.delete(
        f"/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["message"] == "Project deleted successfully"

    # Confirm it no longer exists
    get_resp = client.get(
        "/projects",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert all(p["project_id"] != project_id for p in get_resp.json())

from datetime import date

def test_get_all_profiles_as_admin(client, setup_test_admin_user):
    token = login_and_get_token(client, setup_test_admin_user)

    response = client.get(
        "/profiles",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for profile in data:
        assert "employee_profile_id" in profile
        assert "first_name" in profile
        assert "last_name" in profile
        assert "created_time" in profile
        assert "updated_time" in profile


def test_get_all_profiles_unauth(client):
    response = client.get("/profiles")
    assert response.status_code == 401


from authpassword import hash_password  # your hashing function

def test_checkin_checkout_flow(client: TestClient, setup_test_user):
    db = TestingSessionLocal()
    try:
        user = db.query(Employee).filter_by(employee_email=setup_test_user["email"]).first()
        if not user:
            hashed_pw = hash_password(setup_test_user["password"])  
            user = Employee(
                employee_email=setup_test_user["email"],
                employee_password=hashed_pw,
                employee_name="Test User"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        role = db.query(Role).filter_by(role_name="user").first()
        if not role:
            role = Role(role_name="user")
            db.add(role)
            db.commit()
            db.refresh(role)

       
        rel = db.query(Employee_Role_Relationship).filter_by(
            employee_id=user.employee_id,
            role_id=role.role_id
        ).first()

        if not rel:
            rel = Employee_Role_Relationship(
                employee_id=user.employee_id,
                role_id=role.role_id
            )
            db.add(rel)
            db.commit()
    finally:
        db.close()


    login_resp = client.post("/login", data={
        "username": setup_test_user["email"],
        "password": setup_test_user["password"]
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # --- 5. Perform Check-In ---
    checkin_resp = client.post("/checkin", headers=headers)
    assert checkin_resp.status_code == 200
    checkin_data = checkin_resp.json()
    assert checkin_data["checkin_time"] is not None
    assert checkin_data["checkout_time"] is None

    # --- 6. Repeat Check-In (should fail) ---
    repeat_checkin = client.post("/checkin", headers=headers)
    assert repeat_checkin.status_code == 400
    assert repeat_checkin.json()["detail"] == "Already checked in and not checked out today."

    # --- 7. Perform Checkout ---
    checkout_resp = client.post("/checkout", headers=headers)
    assert checkout_resp.status_code == 200
    checkout_data = checkout_resp.json()
    assert checkout_data["checkout_time"] is not None
    assert checkout_data["work_duration"] is not None

    # --- 8. Repeat Checkout (should fail) ---
    repeat_checkout = client.post("/checkout", headers=headers)
    assert repeat_checkout.status_code == 400
    assert repeat_checkout.json()["detail"] == "No active check-in found"

    # --- 9. Get Latest Attendance ---
    attendance = client.get("/attendance/me", headers=headers)
    assert attendance.status_code == 200
    latest = attendance.json()
    assert latest["employee_id"] == checkin_data["employee_id"]
    assert latest["checkout_time"] == checkout_data["checkout_time"]