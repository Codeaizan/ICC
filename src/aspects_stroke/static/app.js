document.addEventListener('DOMContentLoaded', () => {
    let cases = [];
    let currentCaseId = null;

    const dom = {
        caseList: document.getElementById('case-list'),
        searchInput: document.getElementById('case-search'),
        emptyState: document.getElementById('empty-state'),
        dashboard: document.getElementById('dashboard'),
        currentCaseId: document.getElementById('current-case-id'),
        statusBadge: document.getElementById('status-badge'),
        overlayImg: document.getElementById('overlay-img'),
        aspectsScore: document.getElementById('aspects-score'),
        scoreCard: document.getElementById('score-card'),
        warningBanner: document.getElementById('warning-banner'),
        warningReason: document.getElementById('warning-reason'),
        regionsGrid: document.getElementById('regions-grid'),
        regionsPanel: document.getElementById('regions-panel'),
        metadataContent: document.getElementById('metadata-content')
    };

    // Initialize
    fetchCases();

    dom.searchInput.addEventListener('input', (e) => {
        renderCaseList(e.target.value);
    });

    async function fetchCases() {
        try {
            const res = await fetch('/api/cases');
            cases = await res.json();
            renderCaseList();
        } catch (err) {
            console.error("Failed to fetch cases:", err);
            dom.caseList.innerHTML = `<li style="padding:16px; color:#ef4444;">Error loading cases</li>`;
        }
    }

    function renderCaseList(filter = '') {
        dom.caseList.innerHTML = '';
        const filtered = cases.filter(c => c.case_id.toLowerCase().includes(filter.toLowerCase()));
        
        filtered.forEach(c => {
            const li = document.createElement('li');
            li.className = `case-item ${c.case_id === currentCaseId ? 'active' : ''}`;
            
            let statusClass = 'status-error';
            if (c.status === 'scored') statusClass = 'status-scored';
            if (c.status === 'abstained') statusClass = 'status-abstained';

            li.innerHTML = `
                <span class="case-id">${c.case_id}</span>
                <span class="case-status ${statusClass}">${c.status}</span>
            `;
            li.addEventListener('click', () => loadCase(c.case_id, c.status));
            dom.caseList.appendChild(li);
        });
    }

    async function loadCase(caseId, statusHint) {
        currentCaseId = caseId;
        renderCaseList(dom.searchInput.value);
        
        dom.emptyState.style.display = 'none';
        dom.dashboard.style.display = 'grid';
        dom.dashboard.classList.remove('fade-in');
        void dom.dashboard.offsetWidth; // trigger reflow
        dom.dashboard.classList.add('fade-in');

        dom.currentCaseId.textContent = caseId;
        
        // Reset UI
        dom.statusBadge.className = 'badge';
        dom.regionsGrid.innerHTML = '';
        dom.metadataContent.innerHTML = '';
        dom.overlayImg.src = '';
        
        try {
            const res = await fetch(`/api/case/${caseId}`);
            const data = await res.json();
            renderCaseDetails(caseId, data);
        } catch (err) {
            console.error(err);
            showWarning("Failed to load case data");
        }
    }

    function renderCaseDetails(caseId, data) {
        // Status Badge
        let statusClass = 'status-error';
        if (data.status === 'scored') statusClass = 'status-scored';
        if (data.status === 'abstained') statusClass = 'status-abstained';
        dom.statusBadge.textContent = data.status;
        dom.statusBadge.classList.add(statusClass);

        // Image
        dom.overlayImg.src = `/data/${caseId}/overlay.png?t=${new Date().getTime()}`;

        if (data.status === 'scored') {
            dom.scoreCard.style.display = 'flex';
            dom.warningBanner.style.display = 'none';
            dom.regionsPanel.style.display = 'block';
            
            dom.aspectsScore.textContent = data.aspects;

            // Regions
            if (data.regions) {
                data.regions.forEach(r => {
                    const healthy = !r.affected;
                    const evidenceFormat = r.evidence ? r.evidence.replace('_', ' ').toUpperCase() : 'N/A';
                    
                    const card = document.createElement('div');
                    card.className = 'region-card';
                    card.innerHTML = `
                        <div class="region-header">
                            <span class="region-name">${r.name.replace('_', ' ')}</span>
                            <div class="region-status ${healthy ? 'healthy' : 'affected'}"></div>
                        </div>
                        <div class="region-evidence">
                            ${!healthy ? `<span class="evidence-badge">${evidenceFormat}</span>` : ''}
                        </div>
                    `;
                    dom.regionsGrid.appendChild(card);
                });
            }
        } else {
            dom.scoreCard.style.display = 'none';
            dom.regionsPanel.style.display = 'none';
            dom.warningBanner.style.display = 'flex';
            dom.warningReason.textContent = data.reason || data.error || 'Unknown reason';
        }

        // Metadata
        const meta = {
            "Midline Shift (x)": data.preprocessing?.midline_x?.toFixed(2) || 'N/A',
            "Brain Mask Vol": data.preprocessing?.brain_mask_fraction?.toFixed(3) || 'N/A',
            "Preproc Flags": (data.preprocessing?.quality_flags || []).join(', ') || 'None',
        };
        if (data.registration) {
            meta["Reg Mode"] = data.registration.mode || 'N/A';
            meta["Passed QA"] = data.registration.passed ? "Yes" : "No";
            meta["Regions Found"] = data.registration.regions_present || '0';
        }

        Object.entries(meta).forEach(([k, v]) => {
            const row = document.createElement('div');
            row.className = 'meta-row';
            row.innerHTML = `<span class="meta-label">${k}</span><span class="meta-value">${v}</span>`;
            dom.metadataContent.appendChild(row);
        });
    }

    function showWarning(msg) {
        dom.scoreCard.style.display = 'none';
        dom.regionsPanel.style.display = 'none';
        dom.warningBanner.style.display = 'flex';
        dom.warningReason.textContent = msg;
    }
});
