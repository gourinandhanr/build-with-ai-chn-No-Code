document.addEventListener('DOMContentLoaded', () => {
    // Basic Navigation Logic
    const menuItems = document.querySelectorAll('.menu-item');
    const views = document.querySelectorAll('.view');
    const topNavTitle = document.querySelector('.top-nav h1');
    
    // Set today's date in weight form
    const wDate = document.getElementById('w_date');
    if (wDate) {
        wDate.valueAsDate = new Date();
    }

    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = item.getAttribute('data-target');
            
            // Update Menu
            menuItems.forEach(m => m.classList.remove('active'));
            item.classList.add('active');
            
            // Update Title
            topNavTitle.textContent = item.textContent;

            // Show target view
            views.forEach(v => v.classList.remove('active'));
            const targetView = document.getElementById(targetId);
            if (targetView) targetView.classList.add('active');
            
            if (targetId === 'overview') {
                loadPickups();
            }
        });
    });

    // Load initial data
    loadPickups();

    // Add User Form
    const formAddUser = document.getElementById('form-add-user');
    if (formAddUser) {
        formAddUser.addEventListener('submit', async (e) => {
            e.preventDefault();
            const alertBox = document.getElementById('user-alert');
            const user_id = document.getElementById('u_identifier').value;
            const address = document.getElementById('u_address').value;
            
            try {
                const res = await fetch('/add-user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id, address })
                });
                const data = await res.json();
                if (res.ok) {
                    showAlert(alertBox, 'success', `User ${data.user_id} added successfully!`);
                    e.target.reset();
                } else {
                    showAlert(alertBox, 'error', data.detail || 'Failed to add user');
                }
            } catch (err) {
                showAlert(alertBox, 'error', 'Network error occurred');
            }
        });
    }

    // Log Daily Weight Form
    const formAddWeight = document.getElementById('form-add-weight');
    if (formAddWeight) {
        formAddWeight.addEventListener('submit', async (e) => {
            e.preventDefault();
            const alertBox = document.getElementById('weight-alert');
            const user_id = document.getElementById('w_user_id').value;
            const date = document.getElementById('w_date').value;
            const weight = parseFloat(document.getElementById('w_weight').value);
            
            try {
                const res = await fetch('/add-weight', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id, date, weight })
                });
                let data = {};
                try { data = await res.json(); } catch(e) {}
                
                if (res.ok) {
                    showAlert(alertBox, 'success', `Weight logged for ${data.user_id || user_id}!`);
                    document.getElementById('w_weight').value = '';
                } else {
                    showAlert(alertBox, 'error', data.detail || 'Failed to log weight');
                }
            } catch (err) {
                showAlert(alertBox, 'error', 'Network error occurred');
            }
        });
    }
});

async function loadPickups() {
    const list = document.getElementById('pickups-list');
    if (!list) return;
    list.innerHTML = '<li class="loading">Loading routes & pickup optimizations...</li>';
    
    try {
        const res = await fetch('/pickup-locations-today');
        const data = await res.json();
        
        if (!data || data.length === 0) {
            list.innerHTML = '<li style="color: var(--text-secondary)">No pickups scheduled for today. TimesFM models indicate stable weights.</li>';
            return;
        }
        
        list.innerHTML = data.map(route => `
            <li class="pickup-item">
                <div class="p-header">
                    <span class="p-id">${route.user_id}</span>
                    <span class="p-priority">Priority ${route.priority}</span>
                </div>
                <div class="p-address">📍 ${route.address}</div>
                <div class="p-weight">Latest Record: <strong>${route.latest_weight.toFixed(1)} kg</strong></div>
            </li>
        `).join('');

    } catch (err) {
        list.innerHTML = '<li style="color: var(--danger)">Error loading pickups. Please try again later.</li>';
    }
}

function showAlert(el, type, msg) {
    el.className = `form-alert ${type}`;
    el.textContent = msg;
    setTimeout(() => { el.className = 'form-alert'; el.textContent = ''; }, 4000);
}
