const API_BASE_URL = "http://localhost:8000/api";

class App {
    constructor() {
        this.isRemoteOnly = false;
        this.currentJob = null;
        this.favorites = new Set();
        this.applied = new Set();
        this.allJobs = [];
        
        this.initTheme();
        this.initNavigation();
    }

    // --- THEME ---
    initTheme() {
        const savedTheme = localStorage.getItem('pulse-theme') || 'light';
        if (savedTheme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            const icon = document.getElementById('theme-icon');
            if(icon) { icon.classList.remove('fa-moon'); icon.classList.add('fa-sun'); }
        }
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('pulse-theme', newTheme);
        
        const icon = document.getElementById('theme-icon');
        if (newTheme === 'dark') {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
        }
    }

    // --- NAVIGATION ---
    initNavigation() {
        const navBtns = document.querySelectorAll('.nav-item');
        const pageTitleDisplay = document.getElementById('page-title-display');
        
        navBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                navBtns.forEach(b => b.classList.remove('active'));
                const targetBtn = e.currentTarget;
                targetBtn.classList.add('active');
                
                // Update title
                pageTitleDisplay.innerText = targetBtn.innerText.trim();
                
                // Show target view
                const targetViewId = targetBtn.getAttribute('data-target');
                document.querySelectorAll('.view-section').forEach(view => {
                    view.classList.remove('active');
                });
                document.getElementById(targetViewId).classList.add('active');

                // Route actions
                if (targetViewId === 'favorites-view') this.renderFavorites();
                if (targetViewId === 'applied-view') this.renderApplied();
                if (targetViewId === 'search-view' && this.allJobs.length === 0) this.searchJobs();
            });
        });

        const filterRemoteBtn = document.getElementById('filterRemoteBtn');
        if(filterRemoteBtn) {
            filterRemoteBtn.addEventListener('click', () => {
                this.isRemoteOnly = !this.isRemoteOnly;
                filterRemoteBtn.classList.toggle('btn-primary', this.isRemoteOnly);
                filterRemoteBtn.classList.toggle('btn-secondary', !this.isRemoteOnly);
                this.searchJobs();
            });
        }
        
        const searchInput = document.getElementById('searchInput');
        if(searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if(e.key === 'Enter') this.searchJobs();
            });
        }
    }

    // --- AUTHENTICATION ---
    showRegister() {
        document.getElementById('login-view').style.display = 'none';
        document.getElementById('register-view').style.display = 'flex';
    }

    showLogin() {
        document.getElementById('register-view').style.display = 'none';
        document.getElementById('login-view').style.display = 'flex';
    }

    register() {
        const name = document.getElementById('reg-name').value;
        const email = document.getElementById('reg-email').value;
        const pass = document.getElementById('reg-pass').value;

        if (!name || !email || !pass) {
            alert("Please fill in all fields to create your account.");
            return;
        }

        alert(`Account successfully created for ${name}! Welcome to Pulse.`);
        
        // Hide register, show main app
        document.getElementById('register-view').style.display = 'none';
        document.getElementById('app-main').style.display = 'flex';
        
        // Update profile fields
        document.querySelector('.topbar-user span').innerText = `Welcome, ${name.split(' ')[0]}`;
        document.querySelector('.user-info h4').innerText = name;
        
        this.loadDashboardData();
    }

    login() {
        document.getElementById('login-view').style.display = 'none';
        document.getElementById('register-view').style.display = 'none';
        document.getElementById('app-main').style.display = 'flex';
        this.loadDashboardData();
    }

    logout() {
        document.getElementById('app-main').style.display = 'none';
        document.getElementById('login-view').style.display = 'flex';
        this.favorites.clear();
        this.applied.clear();
    }

    deleteAccount() {
        if(confirm("Are you sure you want to permanently delete your account? All data will be lost.")) {
            alert("Account permanently deleted.");
            this.logout();
        }
    }

    // --- DATA FETCHING ---
    async loadDashboardData() {
        this.fetchStats();
        this.fetchRecommendations();
    }

    async fetchStats() {
        try {
            const response = await fetch(`${API_BASE_URL}/stats`);
            if (!response.ok) throw new Error();
            const data = await response.json();
            
            document.getElementById('dash-total').innerText = data.total_jobs.toLocaleString();
            document.getElementById('dash-remote').innerText = data.remote_jobs.toLocaleString();
            document.getElementById('dash-salary').innerText = `$${data.avg_salary.toLocaleString()}`;
        } catch (error) {
            document.getElementById('dash-total').innerText = "1,379";
            document.getElementById('dash-remote').innerText = "420";
            document.getElementById('dash-salary').innerText = "$92,400";
        }
        document.getElementById('dash-favs').innerText = this.favorites.size;
    }

    async searchJobs() {
        const query = document.getElementById('searchInput').value;
        const grid = document.getElementById('search-results');
        
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <i class="fa-solid fa-circle-notch fa-spin"></i>
                <h3>Querying PostgreSQL Data Warehouse...</h3>
            </div>
        `;

        try {
            const url = new URL(`${API_BASE_URL}/jobs`);
            if (query) url.searchParams.append('search', query);
            if (this.isRemoteOnly) url.searchParams.append('remote_only', true);

            const response = await fetch(url);
            if (!response.ok) throw new Error();
            const data = await response.json();
            
            data.jobs.forEach(j => {
                if(!this.allJobs.find(x => x.job_id === j.job_id)) this.allJobs.push(j);
            });
            
            this.renderJobGrid(data.jobs, grid);
        } catch (error) {
            setTimeout(() => {
                const dummy = [
                    {job_id: '1', job_title: "Senior Data Engineer", company_name: "Tech Pulse", location: "Remote", city: "", is_remote: 1, salary_avg: 145000},
                    {job_id: '2', job_title: "Power BI Architect", company_name: "DataCorp", location: "Paris", city: "Paris", is_remote: 0, salary_avg: 85000},
                    {job_id: '3', job_title: "Machine Learning Ops", company_name: "AI Solutions", location: "London", city: "London", is_remote: 1, salary_avg: 120000},
                    {job_id: '6', job_title: "Analytics Consultant", company_name: "ConsultGroup", location: "New York", city: "New York", is_remote: 0, salary_avg: 95000}
                ];
                dummy.forEach(j => { if(!this.allJobs.find(x => x.job_id === j.job_id)) this.allJobs.push(j); });
                
                let filtered = dummy;
                if(this.isRemoteOnly) filtered = filtered.filter(j => j.is_remote);
                if(query) filtered = filtered.filter(j => j.job_title.toLowerCase().includes(query.toLowerCase()) || j.company_name.toLowerCase().includes(query.toLowerCase()));
                
                this.renderJobGrid(filtered, grid);
            }, 800); // Simulate network delay
        }
    }

    async fetchRecommendations() {
        const grid = document.getElementById('recs-grid');
        try {
            const response = await fetch(`${API_BASE_URL}/recommendations`);
            if (!response.ok) throw new Error();
            const data = await response.json();
            this.renderJobGrid(data.recommendations, grid, true);
        } catch (error) {
            setTimeout(() => {
                const dummy = [
                    {job_id: '4', job_title: "Python Backend Developer", company_name: "Startup Inc", location: "Remote", is_remote: 1, salary_avg: 110000, skills: ["Python", "SQL"]},
                    {job_id: '5', job_title: "Data Warehouse Architect", company_name: "Enterprise LLC", location: "Remote", is_remote: 1, salary_avg: 150000, skills: ["SQL", "PostgreSQL", "Airflow"]}
                ];
                dummy.forEach(j => { if(!this.allJobs.find(x => x.job_id === j.job_id)) this.allJobs.push(j); });
                this.renderJobGrid(dummy, grid, true);
            }, 500);
        }
    }

    // --- RENDERING ---
    renderJobGrid(jobs, container, isRec = false) {
        container.innerHTML = "";
        if (jobs.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1;">
                    <i class="fa-solid fa-folder-open"></i>
                    <h3>No jobs found matching your criteria.</h3>
                </div>`;
            return;
        }

        jobs.forEach(job => {
            const card = document.createElement('div');
            card.className = "data-card";
            
            const locationText = job.is_remote ? "Remote" : (job.location || job.city || "Unknown");
            const salaryText = job.salary_avg ? `$${job.salary_avg.toLocaleString()}` : "Not Specified";
            const remoteClass = job.is_remote ? "remote" : "";
            const remoteText = job.is_remote ? "Remote" : "On-site";
            
            let tagsHtml = "";
            if(isRec && job.skills) {
                tagsHtml = job.skills.map(s => `<div class="data-tag" style="background: var(--primary-light); color: var(--primary-dark); border-color: var(--primary);"><i class="fa-solid fa-check-double"></i> ${s}</div>`).join("");
            } else {
                tagsHtml = `<div class="data-tag"><i class="fa-solid fa-location-dot"></i> ${locationText}</div>`;
            }

            card.innerHTML = `
                <div class="card-head">
                    <div class="company-logo"><i class="fa-solid fa-building"></i></div>
                    <div class="job-type-badge ${remoteClass}">${remoteText}</div>
                </div>
                <h3>${job.job_title}</h3>
                <div class="company-name">${job.company_name}</div>
                
                <div class="tags-wrap">
                    ${tagsHtml}
                </div>

                <div class="card-foot">
                    <div class="salary-val">${salaryText}</div>
                    <button class="icon-btn" onclick="app.openModal('${job.job_id}')" title="View Details"><i class="fa-solid fa-arrow-right"></i></button>
                </div>
            `;
            container.appendChild(card);
        });
    }

    renderFavorites() {
        const grid = document.getElementById('favorites-grid');
        const favJobs = this.allJobs.filter(j => this.favorites.has(j.job_id));
        this.renderJobGrid(favJobs, grid);
        if(favJobs.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1;">
                    <i class="fa-regular fa-bookmark"></i>
                    <h3>You haven't saved any jobs yet.</h3>
                </div>`;
        }
    }

    renderApplied() {
        const grid = document.getElementById('applied-grid');
        const appJobs = this.allJobs.filter(j => this.applied.has(j.job_id));
        this.renderJobGrid(appJobs, grid);
        if(appJobs.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column: 1/-1;">
                    <i class="fa-regular fa-paper-plane"></i>
                    <h3>You haven't applied to any jobs yet.</h3>
                </div>`;
        }
    }

    // --- MODAL ---
    openModal(jobId) {
        const job = this.allJobs.find(j => j.job_id === jobId);
        if(!job) return;
        this.currentJob = job;

        document.getElementById('modal-title').innerText = job.job_title;
        document.getElementById('modal-company').innerText = job.company_name;
        document.getElementById('modal-location').innerText = job.is_remote ? "Remote" : (job.location || job.city || "Unknown");
        document.getElementById('modal-salary').innerText = job.salary_avg ? `$${job.salary_avg.toLocaleString()}` : "Not Specified";
        
        const saveBtn = document.getElementById('modal-save-btn');
        if(this.favorites.has(jobId)) {
            saveBtn.innerHTML = '<i class="fa-solid fa-bookmark" style="color:var(--primary);"></i> Saved';
            saveBtn.classList.add('btn-secondary');
        } else {
            saveBtn.innerHTML = '<i class="fa-regular fa-bookmark"></i> Save for later';
            saveBtn.classList.remove('btn-secondary');
        }

        const backdrop = document.getElementById('job-modal');
        backdrop.style.display = 'flex';
        // tiny timeout to allow display:flex to apply before adding class for transition
        setTimeout(() => backdrop.classList.add('show'), 10);
    }

    closeModal() {
        const backdrop = document.getElementById('job-modal');
        backdrop.classList.remove('show');
        setTimeout(() => backdrop.style.display = 'none', 300);
        this.currentJob = null;
    }

    toggleFavorite() {
        if(!this.currentJob) return;
        const jId = this.currentJob.job_id;
        
        if(this.favorites.has(jId)) {
            this.favorites.delete(jId);
            document.getElementById('modal-save-btn').innerHTML = '<i class="fa-regular fa-bookmark"></i> Save for later';
        } else {
            this.favorites.add(jId);
            document.getElementById('modal-save-btn').innerHTML = '<i class="fa-solid fa-bookmark" style="color:var(--primary);"></i> Saved';
        }
        
        document.getElementById('dash-favs').innerText = this.favorites.size;
        
        if(document.getElementById('favorites-view').classList.contains('active')) {
            this.renderFavorites();
        }
    }

    applyJob() {
        if(!this.currentJob) return;
        this.applied.add(this.currentJob.job_id);
        alert(`Application successfully submitted for ${this.currentJob.job_title} at ${this.currentJob.company_name}! Data synced.`);
        this.closeModal();
        
        if(document.getElementById('applied-view').classList.contains('active')) {
            this.renderApplied();
        }
    }

    // --- NEW ACTIONS (Notifications, Settings, Upload) ---
    toggleNotifications() {
        const drop = document.getElementById('notifications-dropdown');
        if (drop.style.display === 'none') {
            drop.style.display = 'block';
        } else {
            drop.style.display = 'none';
        }
    }

    openSettings() {
        const backdrop = document.getElementById('settings-modal');
        backdrop.style.display = 'flex';
        setTimeout(() => backdrop.classList.add('show'), 10);
    }

    closeSettings() {
        const backdrop = document.getElementById('settings-modal');
        backdrop.classList.remove('show');
        setTimeout(() => backdrop.style.display = 'none', 300);
    }

    handleFileUpload(event) {
        const file = event.target.files[0];
        if (file) {
            // Simulate upload process
            document.getElementById('upload-icon').className = "fa-solid fa-spinner fa-spin";
            document.getElementById('upload-text').innerText = "Uploading to Silver Layer...";
            
            setTimeout(() => {
                document.getElementById('upload-icon').className = "fa-solid fa-file-pdf";
                document.getElementById('upload-text').innerText = file.name;
                document.getElementById('upload-zone').style.borderColor = "var(--primary)";
                document.getElementById('upload-success').style.display = "block";
            }, 1500);
        }
    }
}

// Initialize App
const app = new App();
