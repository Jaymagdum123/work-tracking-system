const API = '/api';

async function api(path, options={}) {
  const opts={...options, headers:{'Content-Type':'application/json', ...(options.headers||{})}, credentials:'same-origin'};
  const res=await fetch(API+path,opts);
  let data={}; try{data=await res.json();}catch(e){}
  if(!res.ok) throw new Error(data.message||'Request failed');
  return data;
}

function showToast(message){
  const box=document.getElementById('toastBox');
  if(!box){alert(message);return;}
  box.innerHTML=`<div class="toast show align-items-center text-bg-dark" role="alert"><div class="d-flex"><div class="toast-body">${escapeHtml(message)}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.closest('.toast').remove()"></button></div></div>`;
  setTimeout(()=>{const t=box.querySelector('.toast');if(t)t.remove()},2800);
}
function escapeHtml(v){return String(v??'').replace(/[&<>'"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[m]));}
function initials(name){return String(name||'').split(' ').map(x=>x[0]).slice(0,2).join('').toUpperCase();}
function statusClass(s){s=String(s||'').toLowerCase();if(s.includes('complete')||s==='active'||s==='present')return 'green-status';if(s.includes('late')||s.includes('leave'))return 'yellow-status';if(s.includes('absent'))return 'red-status';if(s.includes('progress'))return 'orange-status';return 'blue-status';}
function badgePriority(p){let c=String(p||'').toLowerCase();return `<span class="badge-soft ${c==='high'?'red':c==='medium'?'yellow':'gray'}">${escapeHtml(p)}</span>`;}

async function login(e){
 e.preventDefault(); const u=document.getElementById('loginUser').value.trim(), p=document.getElementById('loginPass').value;
 try{await api('/login',{method:'POST',body:JSON.stringify({username:u,password:p})});localStorage.setItem('worktrack_logged_in','1');location.href='dashboard.html';}
 catch(err){showToast(err.message);}
}

function protectPage(){ if(location.pathname.endsWith('index.html')||location.pathname==='/' ) return; api('/me').catch(()=>location.href='index.html'); }
function logout(){api('/logout',{method:'POST'}).finally(()=>{localStorage.removeItem('worktrack_logged_in');location.href='index.html';});}

async function loadEmployees(){
 const tb=document.querySelector('#employeeTable tbody'); if(!tb)return;
 try{const r=await api('/employees'); tb.innerHTML=r.data.map(e=>`<tr><td><div class="person"><span class="table-avatar">${initials(e.full_name)}</span><div><strong>${escapeHtml(e.full_name)}</strong><small>${escapeHtml(e.email||'')}</small></div></div></td><td>${escapeHtml(e.employee_code)}</td><td>${escapeHtml(e.department)}</td><td>${escapeHtml(e.role)}</td><td>${escapeHtml(e.phone||'')}</td><td><span class="status ${statusClass(e.status)}">${escapeHtml(e.status)}</span></td><td><button class="icon-btn-sm" onclick="deleteEmployee(${e.id})"><i class="bi bi-trash"></i></button></td></tr>`).join('');
 document.querySelector('.panel-head p').textContent=`${r.data.length} employees in the system`;
 }catch(err){showToast(err.message)}
}
async function deleteEmployee(id){if(!confirm('Delete this employee?'))return;try{await api('/employees/'+id,{method:'DELETE'});showToast('Employee deleted');loadEmployees();}catch(e){showToast(e.message)}}
async function saveDemo(){
 const m=document.getElementById('employeeModal'); if(!m)return;
 const inputs=m.querySelectorAll('input'), select=m.querySelector('select');
 const d={full_name:inputs[0].value.trim(),employee_code:inputs[1].value.trim(),department:select.value,role:inputs[2].value.trim(),phone:inputs[3].value.trim()};
 try{await api('/employees',{method:'POST',body:JSON.stringify(d)});bootstrap.Modal.getInstance(m)?.hide();m.querySelectorAll('input').forEach(x=>x.value='');showToast('Employee added successfully');loadEmployees();}catch(e){showToast(e.message)}
}

async function loadDepartments(){const box=document.getElementById('departmentTable');if(!box)return;try{const r=await api('/departments');box.innerHTML=r.data.map((d,i)=>`<div class="col-lg-4 col-md-6"><div class="dept-card"><div class="dept-icon blue"><i class="bi bi-diagram-3"></i></div><div><h5>${escapeHtml(d.name)}</h5><p>${d.employee_count} employees</p></div><span class="dept-number">${String(i+1).padStart(2,'0')}</span><div class="progress mt-3"><div class="progress-bar" style="width:70%"></div></div><small class="muted">Operational department</small></div></div>`).join('');}catch(e){showToast(e.message)}}
async function addDepartment(){const name=prompt('Department name:');if(!name)return;try{await api('/departments',{method:'POST',body:JSON.stringify({name})});showToast('Department added');loadDepartments()}catch(e){showToast(e.message)}}

async function loadWork(){const tb=document.querySelector('.table tbody');if(!tb||!location.pathname.includes('work.html'))return;try{const r=await api('/work');tb.innerHTML=r.data.map(w=>`<tr><td><strong>${escapeHtml(w.title)}</strong><small class="d-block muted">${escapeHtml(w.description||'')}</small></td><td>${escapeHtml(w.employee||'')}</td><td>${escapeHtml(w.department||'')}</td><td>${w.deadline?new Date(w.deadline).toLocaleString():'—'}</td><td>${badgePriority(w.priority)}</td><td><span class="status ${statusClass(w.status)}">${escapeHtml(w.status)}</span></td><td></td></tr>`).join('')}catch(e){showToast(e.message)}}
async function addWork(){showToast('Use the Work API to add assignments; employee ID is required.');}

async function loadProgress(){if(!location.pathname.includes('progress.html'))return;const table=document.querySelector('table');if(!table)return;try{const r=await api('/progress');const tb=table.querySelector('tbody');if(tb)tb.innerHTML=r.data.map(w=>`<tr><td>${escapeHtml(w.title)}</td><td>${escapeHtml(w.employee||'')}</td><td>${escapeHtml(w.department||'')}</td><td><div class="progress"><div class="progress-bar" style="width:${w.progress||0}%"></div></div><small>${w.progress||0}%</small></td><td><span class="status ${statusClass(w.status)}">${escapeHtml(w.status)}</span></td></tr>`).join('')}catch(e){showToast(e.message)}}

async function loadAttendance(){if(!location.pathname.includes('attendance.html'))return;const d=document.querySelector('input[type=date]')?.value||new Date().toISOString().slice(0,10);try{const r=await api('/attendance?date='+encodeURIComponent(d));const table=document.querySelector('table tbody');if(table)table.innerHTML=r.data.map(a=>`<tr><td><div class="person"><span class="table-avatar">${initials(a.employee)}</span><strong>${escapeHtml(a.employee)}</strong></div></td><td>${escapeHtml(a.department||'')}</td><td>${escapeHtml(a.check_in||'—')}</td><td>${escapeHtml(a.check_out||'—')}</td><td><span class="status ${statusClass(a.status)}">${escapeHtml(a.status)}</span></td></tr>`).join('')}catch(e){showToast(e.message)}}
async function markAttendance(){const employee_id=prompt('Enter Employee ID (database numeric ID):');if(!employee_id)return;try{await api('/attendance',{method:'POST',body:JSON.stringify({employee_id:Number(employee_id),attendance_date:document.querySelector('input[type=date]')?.value,status:'Present',check_in:new Date().toTimeString().slice(0,8)})});showToast('Attendance saved');loadAttendance()}catch(e){showToast(e.message)}}

async function loadProduction(){if(!location.pathname.includes('production.html'))return;try{const r=await api('/production');const table=document.querySelector('table tbody');if(table)table.innerHTML=r.data.map(p=>`<tr><td>${new Date(p.production_date).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'})}</td><td><strong>${escapeHtml(p.product)}</strong></td><td>${escapeHtml(p.department||'')}</td><td>${p.quantity}</td><td>${p.good_units}</td><td>${p.defective}</td><td><span class="status ${statusClass(p.status)}">${escapeHtml(p.status)}</span></td></tr>`).join('')}catch(e){showToast(e.message)}}
async function addProduction(){const product=prompt('Product name:');if(!product)return;const quantity=Number(prompt('Quantity:')||0);if(!quantity)return;const defective=Number(prompt('Defective units:')||0);try{await api('/production',{method:'POST',body:JSON.stringify({product,quantity,defective,good_units:quantity-defective,status:'Completed'})});showToast('Production added');loadProduction()}catch(e){showToast(e.message)}}

async function loadDashboard(){if(!location.pathname.includes('dashboard.html'))return;try{const r=await api('/dashboard');const cards=document.querySelectorAll('.stat-card h3');if(cards.length>=4){cards[0].textContent=r.data.employees;cards[1].textContent=r.data.present;cards[2].textContent=r.data.active_work;cards[3].textContent=Number(r.data.today_output).toLocaleString();}}catch(e){showToast(e.message)}}

async function loadProfile(){if(!location.pathname.includes('profile.html'))return;try{const r=await api('/profile');const u=r.user;const inputs=document.querySelectorAll('form input, form textarea');if(inputs[0])inputs[0].value=u.full_name||'';if(inputs[1])inputs[1].value=u.email||'';if(inputs[2])inputs[2].value=u.phone||'';if(inputs[4])inputs[4].value=u.address||'';}catch(e){showToast(e.message)}}
async function updateProfile(e){e.preventDefault();const i=e.target.querySelectorAll('input,textarea');try{await api('/profile',{method:'PUT',body:JSON.stringify({full_name:i[0].value,email:i[1].value,phone:i[2].value,address:i[4]?.value||''})});showToast('Profile updated successfully')}catch(err){showToast(err.message)}}

function openModal(id){const el=document.getElementById(id);if(el&&window.bootstrap)new bootstrap.Modal(el).show()}

document.addEventListener('DOMContentLoaded',()=>{
 const menuBtn=document.getElementById('menuBtn'),sidebar=document.getElementById('sidebar');if(menuBtn&&sidebar)menuBtn.onclick=()=>sidebar.classList.toggle('open');
 const loginForm=document.getElementById('loginForm');if(loginForm)loginForm.addEventListener('submit',login);
 document.querySelectorAll('.logout').forEach(a=>{a.addEventListener('click',e=>{e.preventDefault();logout()})});
 document.querySelectorAll('[data-filter]').forEach(input=>input.addEventListener('input',()=>{const t=document.getElementById(input.dataset.filter);if(!t)return;const q=input.value.toLowerCase();t.querySelectorAll('tbody tr,.dept-card').forEach(x=>x.style.display=x.innerText.toLowerCase().includes(q)?'':'none')}));
 if(!location.pathname.endsWith('index.html')&&location.pathname!=='/')protectPage();
 loadDashboard();loadEmployees();loadDepartments();loadWork();loadProgress();loadAttendance();loadProduction();loadProfile();
 const pf=document.querySelector('form');if(location.pathname.includes('profile.html')&&pf)pf.onsubmit=updateProfile;
});


