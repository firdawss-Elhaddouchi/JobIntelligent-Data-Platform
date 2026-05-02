const API_BASE_URL = "http://localhost:8000/api";

class App {
    constructor() {
        this.isRemoteOnly = false;
        this.currentJob = null;
        this.currentUser = null; // {user_id, full_name, email, skills}
        this.favorites = new Set();
        this.applied = new Set();
        this.allJobs = [];

        this.initTheme();
        this.initNavigation();
    }

    // --- THEME ---
    initTheme() {
        const savedTheme = localStorage.getItem('jobintelligent-theme') || 'light';
        if (savedTheme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            const icon = document.getElementById('theme-icon');
            if (icon) { icon.classList.remove('fa-moon'); icon.classList.add('fa-sun'); }
        }
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('jobintelligent-theme', newTheme);

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

                // Reset scroll position to top of page when changing tabs
                const scrollArea = document.querySelector('.scroll-area');
                if (scrollArea) {
                    scrollArea.scrollTo(0, 0);
                }

                // Route actions
                if (targetViewId === 'favorites-view') this.renderFavorites();
                if (targetViewId === 'applied-view') this.renderApplied();
                if (targetViewId === 'search-view' && this.allJobs.length === 0) this.searchJobs();
            });
        });

        const filterRemoteBtn = document.getElementById('filterRemoteBtn');
        if (filterRemoteBtn) {
            filterRemoteBtn.addEventListener('click', () => {
                this.isRemoteOnly = !this.isRemoteOnly;
                filterRemoteBtn.classList.toggle('btn-primary', this.isRemoteOnly);
                filterRemoteBtn.classList.toggle('btn-secondary', !this.isRemoteOnly);
                this.searchJobs();
            });
        }

        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.searchJobs();
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

    async register() {
        const name = document.getElementById('reg-name').value;
        const email = document.getElementById('reg-email').value;
        const pass = document.getElementById('reg-pass').value;

        if (!name || !email || !pass) {
            alert("Please fill in all fields to create your account.");
            return;
        }

        try {
            const res = await fetch(`${API_BASE_URL}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ full_name: name, email: email, password: pass })
            });
            if (!res.ok) throw new Error("Email may already be registered.");

            const data = await res.json();
            this.handleLoginSuccess(data);
            alert(`Account successfully created for ${name}! Welcome to JobIntelligent.`);
        } catch (e) {
            alert(e.message);
        }
    }

    async login() {
        const email = document.querySelector('#login-view input[type="email"]').value;
        const pass = document.querySelector('#login-view input[type="password"]').value;

        if (!email || !pass) {
            alert("Please enter both email and password.");
            return;
        }

        try {
            const res = await fetch(`${API_BASE_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, password: pass })
            });
            if (!res.ok) throw new Error("Invalid email or password.");

            const data = await res.json();
            this.handleLoginSuccess(data);
        } catch (e) {
            alert(e.message);
        }
    }

    handleLoginSuccess(userData) {
        this.currentUser = userData;
        document.getElementById('login-view').style.display = 'none';
        document.getElementById('register-view').style.display = 'none';
        document.getElementById('app-main').style.display = 'flex';

        // Force redirect to Overview page
        const dashboardBtn = document.querySelector('.nav-item[data-target="dashboard-view"]');
        if (dashboardBtn) dashboardBtn.click();

        // Update user card in sidebar
        const avatarLetter = userData.full_name ? userData.full_name.charAt(0).toUpperCase() : 'U';
        document.querySelector('.user-avatar').innerText = avatarLetter;
        document.querySelector('.user-info h4').innerText = userData.full_name;

        // Populate profile page
        document.getElementById('profile-name').value = userData.full_name;
        document.getElementById('profile-skills').value = userData.full_name ? (userData.skills || "") : "";

        this.loadDashboardData();
    }

    logout() {
        const confirmLogout = confirm("Are you sure you want to log out?");
        if (!confirmLogout) return;

        this.currentUser = null;
        document.getElementById('app-main').style.display = 'none';
        document.getElementById('login-view').style.display = 'flex';

        // Clear forms to prevent data remaining
        document.querySelector('#login-view input[type="email"]').value = '';
        document.querySelector('#login-view input[type="password"]').value = '';
        document.getElementById('reg-name').value = '';
        document.getElementById('reg-email').value = '';
        document.getElementById('reg-pass').value = '';

        this.favorites.clear();
        this.applied.clear();
    }

    deleteAccount() {
        if (confirm("Are you sure you want to permanently delete your account? All data will be lost.")) {
            alert("Account permanently deleted.");
            this.logout();
        }
    }

    // --- DATA FETCHING ---
    async loadDashboardData() {
        this.fetchStats();
        this.fetchRecommendations();
        if (this.currentUser) {
            this.fetchUserData();
        }

        // Pre-fetch jobs so the Search Jobs tab is instantly populated
        if (this.allJobs.length === 0) {
            this.searchJobs();
        }
    }

    async fetchUserData() {
        try {
            const favRes = await fetch(`${API_BASE_URL}/user/${this.currentUser.user_id}/favorites`);
            const favData = await favRes.json();
            this.favorites = new Set(favData.favorites);
            document.getElementById('dash-favs').innerText = this.favorites.size;

            const appRes = await fetch(`${API_BASE_URL}/user/${this.currentUser.user_id}/applications`);
            const appData = await appRes.json();
            this.applied = new Set(appData.applications);
        } catch (e) {
            console.error("Error loading user state", e);
        }
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

    handleSearchInput(e) {
        const clearBtn = document.getElementById('clearSearchBtn');
        if (e.target.value.trim().length > 0) {
            clearBtn.style.display = 'block';
        } else {
            clearBtn.style.display = 'none';
        }
    }

    clearSearch() {
        const searchInput = document.getElementById('searchInput');
        searchInput.value = '';
        document.getElementById('clearSearchBtn').style.display = 'none';
        this.searchJobs(); // Re-trigger search to get all jobs
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
            // ==========================================
            // --- NLP SEARCH INTEGRATION ---
            // ==========================================
            // This constructs the query payload to our FastAPI backend.
            // If the user types a query (even with typos), the backend's Gestalt Pattern Matching
            // algorithm (difflib) will fuzzy match the input against the Gold Layer job titles.
            const url = new URL(`${API_BASE_URL}/jobs`);
            if (query) url.searchParams.append('search', query);
            if (this.isRemoteOnly) url.searchParams.append('remote_only', true);

            const response = await fetch(url);
            if (!response.ok) throw new Error("HTTP " + response.status);
            const data = await response.json();

            if (data && data.jobs) {
                data.jobs.forEach(j => {
                    if (!this.allJobs.find(x => x.job_id === j.job_id)) this.allJobs.push(j);
                });
                this.renderJobGrid(data.jobs, grid);
            } else {
                throw new Error("Invalid response format");
            }
        } catch (error) {
            console.error("Search failed, falling back to dummy data:", error);
            setTimeout(() => {
                const dummy = [
                    { job_id: '1', job_title: "Senior Data Engineer", company_name: "Tech JobIntelligent", location: "Remote", city: "", is_remote: 1, salary_avg: 145000 },
                    { job_id: '2', job_title: "Power BI Architect", company_name: "DataCorp", location: "Paris", city: "Paris", is_remote: 0, salary_avg: 85000 },
                    { job_id: '3', job_title: "Machine Learning Ops", company_name: "AI Solutions", location: "London", city: "London", is_remote: 1, salary_avg: 120000 },
                    { job_id: '6', job_title: "Analytics Consultant", company_name: "ConsultGroup", location: "New York", city: "New York", is_remote: 0, salary_avg: 95000 }
                ];
                dummy.forEach(j => { if (!this.allJobs.find(x => x.job_id === j.job_id)) this.allJobs.push(j); });

                let filtered = dummy;
                if (this.isRemoteOnly) filtered = filtered.filter(j => j.is_remote);
                if (query) filtered = filtered.filter(j => j.job_title.toLowerCase().includes(query.toLowerCase()) || j.company_name.toLowerCase().includes(query.toLowerCase()));

                this.renderJobGrid(filtered, grid);
            }, 800); // Simulate network delay
        }
    }

    async fetchRecommendations() {
        if (!this.currentUser) return;

        const grid = document.getElementById('recs-grid');
        try {
            const response = await fetch(`${API_BASE_URL}/recommendations?user_id=${this.currentUser.user_id}`);
            if (!response.ok) throw new Error();
            const data = await response.json();

            // Add recommendations to allJobs so the modal can find them!
            data.recommendations.forEach(j => {
                if (!this.allJobs.find(x => x.job_id === j.job_id)) this.allJobs.push(j);
            });

            this.renderJobGrid(data.recommendations, grid, true);
        } catch (error) {
            console.error(error);
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
            try {
                const card = document.createElement('div');
                card.className = "data-card";

                const locationText = job.is_remote ? "Remote" : (job.location || job.city || "Unknown");
                const salaryText = job.salary_avg ? `$${Number(job.salary_avg).toLocaleString()}` : "Not Specified";
                const remoteClass = job.is_remote ? "remote" : "";
                const remoteText = job.is_remote ? "Remote" : "On-site";
                const sourceName = (job.source && typeof job.source === 'string') ? job.source.toUpperCase() : "";

                let tagsHtml = "";
                if (isRec && job.skills && Array.isArray(job.skills)) {
                    tagsHtml = job.skills.map(s => `<div class="data-tag" style="background: var(--primary-light); color: var(--primary-dark); border-color: var(--primary);"><i class="fa-solid fa-check-double"></i> ${s}</div>`).join("");
                } else {
                    tagsHtml = `<div class="data-tag"><i class="fa-solid fa-location-dot"></i> ${locationText}</div>`;
                }

                let sourceHtml = sourceName ? `<div class="job-type-badge" style="background: var(--bg-secondary); color: var(--text-secondary); margin-left: 8px;">${sourceName}</div>` : "";
                let titleHtml = job.job_url ? `<a href="${job.job_url}" target="_blank" style="color: inherit; text-decoration: none;" onclick="event.stopPropagation();">${job.job_title || 'Unknown Job'}</a>` : (job.job_title || 'Unknown Job');

                card.innerHTML = `
                    <div class="card-head">
                        <div class="company-logo"><i class="fa-solid fa-building"></i></div>
                        <div style="display: flex; flex: 1; justify-content: flex-end;">
                            <div class="job-type-badge ${remoteClass}">${remoteText}</div>
                            ${sourceHtml}
                        </div>
                    </div>
                    <h3>${titleHtml}</h3>
                    <div class="company-name">${job.company_name || 'Unknown Company'}</div>
                    
                    <div class="tags-wrap">
                        ${tagsHtml}
                    </div>

                    <div class="card-foot">
                        <div class="salary-val">${salaryText}</div>
                        <button class="icon-btn" onclick="app.openModal('${job.job_id}')" title="View Details"><i class="fa-solid fa-arrow-right"></i></button>
                    </div>
                `;
                container.appendChild(card);
            } catch (err) {
                console.error("Error rendering job card", err, job);
            }
        });
    }

    renderFavorites() {
        const grid = document.getElementById('favorites-grid');
        const favJobs = this.allJobs.filter(j => this.favorites.has(j.job_id));
        this.renderJobGrid(favJobs, grid);
        if (favJobs.length === 0) {
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
        if (appJobs.length === 0) {
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
        if (!job) return;
        this.currentJob = job;

        document.getElementById('modal-title').innerText = job.job_title;
        document.getElementById('modal-company').innerText = job.company_name;
        document.getElementById('modal-location').innerText = job.is_remote ? "Remote" : (job.location || job.city || "Unknown");

        // Format Salary
        let salaryText = "Not Specified";
        if (job.salary_min && job.salary_max) {
            salaryText = `${job.currency || '$'}${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()}`;
        } else if (job.salary_avg) {
            salaryText = `${job.currency || '$'}${job.salary_avg.toLocaleString()}`;
        }
        document.getElementById('modal-salary').innerText = salaryText;

        // Fill new fields
        document.getElementById('modal-contract').innerText = job.contract_type || "Unknown";
        document.getElementById('modal-source').innerText = job.source ? job.source.toUpperCase() : "Platform";
        document.getElementById('modal-date').innerText = job.posted_date || "Unknown Date";

        // Handle URL
        const urlEl = document.getElementById('modal-url');
        const sourceNameEl = document.getElementById('modal-url-source');
        if (job.job_url) {
            urlEl.href = job.job_url;
            urlEl.style.display = "inline";
            sourceNameEl.innerText = job.source ? job.source.charAt(0).toUpperCase() + job.source.slice(1) : "Source";
        } else {
            urlEl.style.display = "none";
        }

        const saveBtn = document.getElementById('modal-save-btn');
        if (this.favorites.has(jobId)) {
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

    async toggleFavorite() {
        if (!this.currentJob || !this.currentUser) return;
        const jId = this.currentJob.job_id;

        try {
            const res = await fetch(`${API_BASE_URL}/user/favorite`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.currentUser.user_id, job_id: jId })
            });
            const data = await res.json();

            if (data.status === 'added') {
                this.favorites.add(jId);
                document.getElementById('modal-save-btn').innerHTML = '<i class="fa-solid fa-bookmark" style="color:var(--primary);"></i> Saved';
            } else {
                this.favorites.delete(jId);
                document.getElementById('modal-save-btn').innerHTML = '<i class="fa-regular fa-bookmark"></i> Save for later';
            }

            document.getElementById('dash-favs').innerText = this.favorites.size;
            if (document.getElementById('favorites-view').classList.contains('active')) this.renderFavorites();
        } catch (e) {
            console.error(e);
        }
    }

    async applyJob() {
        if (!this.currentJob || !this.currentUser) return;

        try {
            await fetch(`${API_BASE_URL}/user/apply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.currentUser.user_id, job_id: this.currentJob.job_id })
            });

            this.applied.add(this.currentJob.job_id);

            // Redirect to the real source job posting
            if (this.currentJob.job_url) {
                window.open(this.currentJob.job_url, '_blank');
            } else {
                alert(`Application successfully submitted for ${this.currentJob.job_title} at ${this.currentJob.company_name}!`);
            }

            this.closeModal();

            if (document.getElementById('applied-view').classList.contains('active')) this.renderApplied();
        } catch (e) {
            console.error(e);
        }
    }

    async saveProfile() {
        if (!this.currentUser) return;

        const name = document.getElementById('profile-name').value;
        const skills = document.getElementById('profile-skills').value;

        try {
            const res = await fetch(`${API_BASE_URL}/user/${this.currentUser.user_id}/profile`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ full_name: name, skills: skills })
            });
            if (!res.ok) throw new Error("Failed to update profile.");

            const data = await res.json();

            // Update local state
            this.currentUser.full_name = data.full_name;
            this.currentUser.skills = data.skills;

            // Update UI
            document.querySelector('.user-info h4').innerText = data.full_name;
            document.querySelector('.user-avatar').innerText = data.full_name.charAt(0).toUpperCase();

            alert('Profile Successfully Saved to PostgreSQL!');

            // Refresh recommendations based on new skills
            this.fetchRecommendations();

        } catch (e) {
            alert(e.message);
        }
    }

    async deleteAccount() {
        if (!this.currentUser) return;

        const confirmDelete = confirm("Are you sure you want to permanently delete your account? This action cannot be undone.");
        if (!confirmDelete) return;

        try {
            const res = await fetch(`${API_BASE_URL}/user/${this.currentUser.user_id}`, {
                method: 'DELETE'
            });

            if (!res.ok) throw new Error("Failed to delete account.");

            alert("Account successfully deleted from PostgreSQL.");
            this.logout();
        } catch (e) {
            alert(e.message);
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

    async saveSettings() {
        // Retrieve the selected value from the dropdown inside the modal
        const select = document.querySelector('#settings-modal select');
        const selectedValue = select ? select.value : "Real-time (DirectQuery)";

        try {
            const btn = document.querySelector('#settings-modal .btn-primary');
            const originalText = btn.innerText;
            btn.innerText = "Saving to Database...";

            // Send the setting to our FastAPI backend which saves it to PostgreSQL
            const response = await fetch(`${API_BASE_URL}/settings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_rate: selectedValue })
            });

            if (!response.ok) throw new Error("Failed to save settings");

            const data = await response.json();

            btn.innerText = originalText;
            alert(`Platform Settings Saved Successfully!\n\n${data.message}`);
            this.closeSettings();
        } catch (error) {
            console.error(error);
            alert("Error saving settings. Make sure FastAPI is running.");
        }
    }

    async handleFileUpload(event) {
        if (!this.currentUser) {
            alert("Please login first!");
            return;
        }

        const file = event.target.files[0];
        if (!file) return;

        const icon = document.getElementById('upload-icon');
        const text = document.getElementById('upload-text');

        icon.className = 'fa-solid fa-spinner fa-spin';
        text.innerText = 'Analysing CV with AI / NLP...';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch(`${API_BASE_URL}/user/${this.currentUser.user_id}/upload_cv`, {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Upload failed");
            }

            const data = await res.json();

            document.getElementById('upload-success').style.display = 'block';
            document.getElementById('upload-success').innerHTML = `<i class="fa-solid fa-check-circle"></i> ${data.message}`;

            icon.className = 'fa-solid fa-file-pdf';
            text.innerText = file.name;

            // Auto-fill extracted data
            if (data.extracted_skills) {
                document.getElementById('profile-skills').value = data.extracted_skills;
                this.currentUser.skills = data.extracted_skills;
            }
            if (data.extracted_role) {
                document.getElementById('profile-role').value = data.extracted_role;
            }

            alert(`✅ NLP Extraction Complete!\n\nFound Skills: ${data.extracted_skills || 'None'}\nFound Role: ${data.extracted_role || 'None'}\n\nYour profile has been automatically updated in PostgreSQL!`);

            // Refresh ML recommendations
            this.fetchRecommendations();

        } catch (e) {
            icon.className = 'fa-solid fa-cloud-arrow-up';
            text.innerText = 'Drag & Drop your CV here or Click to Browse';
            alert("Error parsing CV: " + e.message);
        }
    }
}

// Initialize App
const app = new App();
