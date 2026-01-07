const API = window.location.hostname === 'localhost'
  ? 'http://127.0.0.1:8086'
  : 'https://employment-management-api.onrender.com';

let accessToken=localStorage.getItem('token');

document.addEventListener('DOMContentLoaded',()=>{
    if(accessToken) showDashboard();
    else showLogin();
});

function showLogin(){
    document.getElementById('login-section').style.display='block';
    document.getElementById('dashboard').style.display='none';
}

function showDashboard() {
  document.getElementById('login-section').style.display = 'none';
  document.getElementById('dashboard').style.display = 'block';

  const role = getUserRole();

  // Hide admin-only tabs for non-admins
  document.querySelector('[data-tab="employees"]').style.display = role === 'admin' ? 'inline-block' : 'none';
  document.querySelector('[data-tab="roles"]').style.display = role === 'admin' ? 'inline-block' : 'none';
  document.querySelector('[data-tab="projects"]').style.display = role === 'admin' ? 'inline-block' : 'none';
}
function checkAdminAccess() {
  if (getUserRole() !== 'admin') {
    alert('You are not authorized to perform this action');
    return false;
  }
  return true;
}

function getUserRole() {
  const payload = JSON.parse(atob(accessToken.split('.')[1]));
  return payload.role;  // e.g., 'admin', 'user', 'manager'
}

async function login(){
    const email=document.getElementById('login-email').value;
    const pw=document.getElementById('login-password').value;
    const resp=await fetch(`${API}/login`,{
        method:'POST',
        headers:{'Content-Type':'application/x-www-form-urlencoded' },
        body: new URLSearchParams({username: email,password: pw})
    });
    const data=await resp.json();
    if(!resp.ok){
        alert('Login failed');
        return;
    }
    accessToken=data.access_token;
    localStorage.setItem('token',accessToken);
    showDashboard();
}
 function logout(){
    accessToken=null;
    localStorage.removeItem('token');
    showLogin();
 }

 // changing the button style on hover
function openTab(tab) {
  // Guard clause for admin-only sections
  if (['employees', 'roles', 'projects'].includes(tab) && !checkAdminAccess()) return;

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });

  const Content = document.getElementById('tab-content');
  Content.innerHTML = `<p>Loading ${tab}...</p>`;

  if (tab === 'profile') loadProfile(Content);
  if (tab === 'attendance') loadAttendance(Content);
  if (tab === 'employees') loadEmployees(Content);
  if (tab === 'roles') loadRoles(Content);
  if (tab === 'projects') loadProjects(Content);
  if (tab === 'myinfo') loadMyInfo(Content);
}


async function apiGet(path){
    const resp=await fetch(API+path,{
        headers:{Authorization: `Bearer ${accessToken}` }
    })
    if(!resp.ok) throw new Error(await resp.json().error || 'Error');
    return resp.json();
}

async function apiPost(path,data){
    const resp=await fetch(API+path,{
        method:'POST',
        headers:{Authorization: `Bearer ${accessToken}`, 'Content-Type':'application/json' },
        body: JSON.stringify(data)
    })
    if(!resp.ok) throw new Error(await resp.json().error || 'Error');
    return resp.json();
}

//profile section
async function loadProfile(container){
    try{
    const userInfo=await apiGet('/profiles/'+ (await getCurrentUserId()));
    container.innerHTML =`
    <h2>Profile</h2>
    <p>ID: ${userInfo.employee_profile_id}</p>
    <p>FirstName: ${userInfo.first_name}</p>
    <p>LastName: ${userInfo.last_name}</p>
    <p>Age: ${userInfo.age}</p>
    <p>Address: ${userInfo.address}</p>
    <p>Father's Name: ${userInfo.father_name}</p>
    <p>Mother's Name: ${userInfo.mother_name}</p>
    <p>Role: ${userInfo.employee_profile_role}</p>
    <p>Date Of Joining: ${userInfo.date_of_joining}</p>
    `;
    }catch(err){
        container.innerHTML+=`<p>Error: ${err.message}</p>`;
    }
}
async function getCurrentUserId() {
  const payload = JSON.parse(atob(accessToken.split('.')[1]));
  return payload.sub;
}

//attendance section
async function loadAttendance(container) {
  container.innerHTML = `
    <h3>Attendance</h3>
    <button id="checkin-btn" onclick="doCheckin()">Check In</button>
    <button id="checkout-btn" onclick="doCheckout()">Check Out</button>
    <div id="att-msg" style="margin-top: 10px;"></div>
  `;

  try {
    const latest = await apiGet('/attendance/me');
    const checkinBtn = document.getElementById('checkin-btn');
    const checkoutBtn = document.getElementById('checkout-btn');
    const msg = document.getElementById('att-msg');

    if (!latest) {
      checkinBtn.disabled = false;
      checkoutBtn.disabled = true;
      msg.textContent = "You haven't checked in yet.";
      return;
    }

    const checkInTime = new Date(latest.checkin_time).toLocaleString();
    if (!latest.checkout_time) {
      // Checked in but not yet checked out
      checkinBtn.disabled = true;
      checkoutBtn.disabled = false;
      msg.innerHTML = `
         <strong>Checked In</strong><br/>
         Check-in Time: ${checkInTime}
      `;
    } else {
      // Already checked out
      const checkOutTime = new Date(latest.checkout_time).toLocaleString();
      checkinBtn.disabled = false;
      checkoutBtn.disabled = true;
      msg.innerHTML = `
         <strong>Last Attendance Record:</strong><br/>
         Check-in Time: ${checkInTime}<br/>
         Check-out Time: ${checkOutTime}<br/>
         Duration Worked: ${latest.work_duration || "N/A"}
      `;
    }
  } catch (err) {
    document.getElementById('att-msg').textContent = `Error: ${err.message}`;
  }
}

async function doCheckin() {
  try {
    await apiPost('/checkin', {});
    loadAttendance(document.getElementById('tab-content'));
  } catch (e) {
    document.getElementById('att-msg').textContent = e.message;
  }
}

async function doCheckout() {
  try {
    await apiPost('/checkout', {});
    loadAttendance(document.getElementById('tab-content'));
  } catch (e) {
    document.getElementById('att-msg').textContent = e.message;
  }
}

 //only admin can access this section
 async function loadEmployees(container) {
  container.innerHTML = `
    <div id="employee-tabs">
      <div class="sub-tab-bar">
        <button class="sub-tab-btn active" onclick="showEmployeeTab('view')">View</button>
        <button class="sub-tab-btn" onclick="showEmployeeTab('add')">Add</button>
        <button class="sub-tab-btn" onclick="showEmployeeTab('update')">Update</button>
        <button class="sub-tab-btn" onclick="showEmployeeTab('delete')">Delete</button>
        <button class="sub-tab-btn" onclick="showEmployeeTab('profile')">Create Profile</button>
      </div>
      <div id="employee-tab-content"></div>
    </div>
  `;

  showEmployeeTab('view'); // Default
}

async function showEmployeeTab(tab) {
  const content = document.getElementById('employee-tab-content');
  document.querySelectorAll('.sub-tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelector(`.sub-tab-btn[onclick*="${tab}"]`).classList.add('active');

  switch (tab) {
    case 'view':
      try {
        const list = await apiGet('/employees');
        const rows = list.map(e =>
          `<tr><td>${e.employee_id}</td><td>${e.employee_name}</td><td>${e.employee_email}</td></tr>`
        ).join('');
        content.innerHTML = `
          <h3>All Employees</h3>
          <table><tr><th>ID</th><th>Name</th><th>Email</th></tr>${rows}</table>
        `;
      } catch (err) {
        content.innerHTML = `<p>Error: ${err.message}</p>`;
      }
      break;

    case 'add':
      content.innerHTML = `
        <h3>Add Employee</h3>
        <input id="add-name" placeholder="Name" />
        <input id="add-email" placeholder="Email" />
        <input id="add-pass" type="password" placeholder="Password" />
        <button onclick="addEmployee()">Add</button>
        <div id="add-msg"></div>
      `;
      break;

    case 'update':
      content.innerHTML = `
        <h3>Update Employee</h3>
        <input id="update-id" placeholder="Employee ID" />
        <input id="update-name" placeholder="New Name" />
        <input id="update-email" placeholder="New Email" />
        <button onclick="updateEmployee()">Update</button>
        <div id="update-msg"></div>
      `;
      break;

    case 'delete':
      content.innerHTML = `
        <h3>Delete Employee</h3>
        <input id="delete-id" placeholder="Employee ID" />
        <button onclick="deleteEmployee()">Delete</button>
        <div id="delete-msg"></div>
      `;
      break;

    case 'profile':
      content.innerHTML = `
        <h3>Create Profile</h3>
        <input id="profile-emp-id" placeholder="Employee ID" />
        <input id="profile-first" placeholder="First Name" />
        <input id="profile-last" placeholder="Last Name" />
        <input id="profile-age" placeholder="Age" />
        <input id="profile-address" placeholder="Address" />
        <input id="profile-father" placeholder="Father's Name" />
        <input id="profile-mother" placeholder="Mother's Name" />
        <input id="profile-role" placeholder="Role" />
        <input id="profile-doj" placeholder="Date of Joining (YYYY-MM-DD)" />
        <button onclick="createProfile()">Create Profile</button>
        <div id="profile-msg"></div>
      `;
      break;
  }
}

async function addEmployee(){
    const data={
        employee_name:document.getElementById('add-name').value,
        employee_email:document.getElementById('add-email').value,
        employee_password:document.getElementById('add-pass').value
    }
    try {
    await apiPost('/employees', data);
    document.getElementById('add-msg').textContent = 'Employee added successfully!';
    openTab('employees'); // reload the tab
  } catch (e) {
    document.getElementById('add-msg').textContent = e.message;
  }
}
async function updateEmployee() {
  const id = document.getElementById('update-id').value;

  //  Only send the required fields
  const data = {
    employee_name: document.getElementById('update-name').value,
    employee_email: document.getElementById('update-email').value
  };

  try {
    const resp = await fetch(`${API}/employees/${id}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Update failed');
    }

    document.getElementById('update-msg').textContent = 'Employee updated successfully!';
    openTab('employees'); // refresh list
  } catch (e) {
    document.getElementById('update-msg').textContent = 'Error: ' + e.message;
  }
}

async function deleteEmployee() {
  const id = document.getElementById('delete-id').value;

  try {
    await fetch(`${API}/employees/${id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${accessToken}`
      }
    });
    document.getElementById('delete-msg').textContent = 'Employee deleted successfully!';
    openTab('employees');
  } catch (e) {
    document.getElementById('delete-msg').textContent = 'Error: ' + e.message;
  }
}

async function createProfile() {
  const profileData = {
    employee_id: parseInt(document.getElementById('profile-emp-id').value),
    first_name: document.getElementById('profile-first').value,
    last_name: document.getElementById('profile-last').value,
    age: parseInt(document.getElementById('profile-age').value),
    address: document.getElementById('profile-address').value,
    father_name: document.getElementById('profile-father').value,
    mother_name: document.getElementById('profile-mother').value,
    employee_profile_role: document.getElementById('profile-role').value,
    date_of_joining: document.getElementById('profile-doj').value
  };

  try {
    await apiPost('/profiles', profileData);
    document.getElementById('profile-msg').textContent = 'Profile created successfully!';
  } catch (e) {
    document.getElementById('profile-msg').textContent = `Error: ${e.message}`;
  }
}

async function loadRoles(container) {
  container.innerHTML = `
    <div id="role-tabs">
      <div class="sub-tab-bar">
        <button class="sub-tab-btn active" onclick="showRoleTab('view')">View</button>
        <button class="sub-tab-btn" onclick="showRoleTab('add')">Add</button>
        <button class="sub-tab-btn" onclick="showRoleTab('assign')">Assign</button>
        <button class="sub-tab-btn" onclick="showRoleTab('delete')">Delete</button>
      </div>
      <div id="role-tab-content"></div>
    </div>
  `;
  showRoleTab('view');
}

async function showRoleTab(tab) {
  const content = document.getElementById('role-tab-content');
  document.querySelectorAll('.sub-tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelector(`.sub-tab-btn[onclick*="${tab}"]`).classList.add('active');

  switch (tab) {
    case 'view':
      try {
        const roles = await apiGet('/roles');
        const rows = roles.map(r => `<tr><td>${r.role_id}</td><td>${r.role_name}</td></tr>`).join('');
        content.innerHTML = `
          <h3>All Roles</h3>
          <table>
            <tr><th>ID</th><th>Name</th></tr>
            ${rows}
          </table>
        `;
      } catch (err) {
        content.innerHTML = `<p>Error: ${err.message}</p>`;
      }
      break;

    case 'add':
      content.innerHTML = `
        <h3>Add Role</h3>
        <input id="new-role-input" placeholder="New Role Name" />
        <button onclick="addRole()">Add Role</button>
        <div id="role-msg"></div>
      `;
      break;

    case 'assign':
      content.innerHTML = `
        <h3>Assign Role to Employee</h3>
        <input id="assign-role-emp" placeholder="Employee Email" />
        <input id="assign-role-id" placeholder="Role ID" />
        <button onclick="assignRole()">Assign Role</button>
        <div id="role-msg"></div>
      `;
      break;

    case 'delete':
      content.innerHTML = `
        <h3>Delete Role</h3>
        <input id="delete-role-id" placeholder="Role ID" />
        <button onclick="deleteRole()">Delete Role</button>
        <div id="role-msg"></div>
      `;
      break;
  }
}

async function assignRole() {
  const empEmail = document.getElementById('assign-role-emp').value;
  const roleId = document.getElementById('assign-role-id').value;

  try {
    await apiPost('/roles/assign', {
      employee_email: empEmail,
      role_id: parseInt(roleId),
    });
    document.getElementById('role-msg').textContent = 'Role assigned successfully!';
  } catch (e) {
    document.getElementById('role-msg').textContent = e.message;
  }
}

async function addRole() {
  const name = document.getElementById('new-role-input').value;
  try {
    await apiPost('/roles', { role_name: name });
    document.getElementById('role-msg').textContent = 'Role added!';
    openTab('roles');
  } catch (e) {
    document.getElementById('role-msg').textContent = e.message;
  }
}
async function deleteRole() {
  const roleId = document.getElementById('delete-role-id').value;
  try {
    await fetch(`${API}/roles/${roleId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${accessToken}` }
    });
    document.getElementById('role-msg').textContent = 'Role deleted successfully!';
    openTab('roles'); // Refresh the list
  } catch (e) {
    document.getElementById('role-msg').textContent = `Error: ${e.message}`;
  }
}

async function loadProjects(container) {
  container.innerHTML = `
    <div id="project-tabs">
      <div class="sub-tab-bar">
        <button class="sub-tab-btn active" onclick="showProjectTab('view')">View</button>
        <button class="sub-tab-btn" onclick="showProjectTab('add')">Add</button>
        <button class="sub-tab-btn" onclick="showProjectTab('assign')">Assign</button>
        <button class="sub-tab-btn" onclick="showProjectTab('delete')">Delete</button>
      </div>
      <div id="project-tab-content"></div>
    </div>
  `;
  showProjectTab('view'); // load default
}

async function showProjectTab(tab) {
  const content = document.getElementById('project-tab-content');
  document.querySelectorAll('.sub-tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelector(`.sub-tab-btn[onclick*="${tab}"]`).classList.add('active');

  switch (tab) {
    case 'view':
      try {
        const projs = await apiGet('/projects');
        const rows = projs.map(p => `<tr><td>${p.project_id}</td><td>${p.project_name}</td></tr>`).join('');
        content.innerHTML = `
          <h3>All Projects</h3>
          <table>
            <tr><th>ID</th><th>Name</th></tr>
            ${rows}
          </table>
        `;
      } catch (err) {
        content.innerHTML = `<p>Error: ${err.message}</p>`;
      }
      break;

    case 'add':
      content.innerHTML = `
        <h3>Add Project</h3>
        <input id="new-project-input" placeholder="New Project Name" />
        <button onclick="addProject()">Add Project</button>
        <div id="proj-msg"></div>
      `;
      break;

    case 'assign':
      content.innerHTML = `
        <h3>Assign Project to Employee</h3>
        <input id="assign-project-emp" placeholder="Employee Email" />
        <input id="assign-project-proj" placeholder="Project ID" />
        <button onclick="assignProject()">Assign Project</button>
        <div id="proj-msg"></div>
      `;
      break;

    case 'delete':
      content.innerHTML = `
        <h3>Delete Project</h3>
        <input id="delete-project-id" placeholder="Project ID" />
        <button onclick="deleteProject()">Delete Project</button>
        <div id="proj-msg"></div>
      `;
      break;
  }
}

async function assignProject() {
  const empMail = document.getElementById('assign-project-emp').value;
  const projId = document.getElementById('assign-project-proj').value;

  try {
    await apiPost('/projects/assign', {
      employee_email: empMail,
      project_id: parseInt(projId),
    });
    document.getElementById('proj-msg').textContent = 'Project assigned successfully!';
  } catch (e) {
    document.getElementById('proj-msg').textContent = e.message;
  }
}

async function addProject() {
  const name = document.getElementById('new-project-input').value;
  try {
    await apiPost('/projects', { project_name: name });
    document.getElementById('proj-msg').textContent = 'Project added!';
    openTab('projects');
  } catch (e) {
    document.getElementById('proj-msg').textContent = e.message;
  }
}
async function deleteProject() {
  const projectId = document.getElementById('delete-project-id').value;

  try {
    await fetch(`${API}/projects/${projectId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${accessToken}` }
    });
    document.getElementById('proj-msg').textContent = 'Project deleted successfully!';
    openTab('projects'); // Refresh the list
  } catch (e) {
    document.getElementById('proj-msg').textContent = `Error: ${e.message}`;
  }
}



async function loadMyInfo(container) {
  try {
    const userId = await getCurrentUserId();
    console.log('User ID:', userId);

    const roles = await apiGet('/roles/' + userId);
    console.log('Roles response:', roles);

    const roleList = Array.isArray(roles)
      ? roles.map(r => `<li>${r.role_name}</li>`).join('')
      : '<li>No roles found</li>';

    const projects = await apiGet('/projects/' + userId);
    console.log('Projects response:', projects);

    const projectList = Array.isArray(projects)
      ? projects.map(p => `<li>${p.project_name}</li>`).join('')
      : '<li>No projects found</li>';

    container.innerHTML = `
      <h3>My Roles:</h3>
      <ul>${roleList}</ul>
      <h3>My Projects:</h3>
      <ul>${projectList}</ul>
    `;
  } catch (err) {
    console.error('Error loading info:', err);
    container.innerHTML = `<p>Error loading your information: ${err.message}</p>`;
  }
}




