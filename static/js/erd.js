// PeopleSoft ERD Explorer - Frontend Logic

document.addEventListener('DOMContentLoaded', () => {
    // --- Global State ---
    let cy = null;
    let activeRecords = new Map(); // Store full record metadata keyed by RECNAME
    let dbStatus = { connected: false, dialect: 'sqlite', schema: null };
    let isUploadedMode = false;
    let uploadedRecords = new Map(); // Store full record metadata keyed by RECNAME when uploaded

    // --- DOM Elements ---
    const recordSearchInput = document.getElementById('recordSearchInput');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    const searchResultsDropdown = document.getElementById('searchResultsDropdown');
    const activeTablesList = document.getElementById('activeTablesList');
    const clearWorkspaceBtn = document.getElementById('clearWorkspaceBtn');
    const expandRelationsBtn = document.getElementById('expandRelationsBtn');
    const relationDepth = document.getElementById('relationDepth');
    const uploadJsonBtn = document.getElementById('uploadJsonBtn');
    const sidebarUploadJsonBtn = document.getElementById('sidebarUploadJsonBtn');
    const uploadJsonInput = document.getElementById('uploadJsonInput');
    const canvasPanel = document.getElementById('canvasPanel');
    const dragOverlay = document.getElementById('dragOverlay');
    
    // Modals & Forms
    const settingsModal = document.getElementById('settingsModal');
    const openSettingsBtn = document.getElementById('openSettingsBtn');
    const closeSettingsModalBtn = document.getElementById('closeSettingsModalBtn');
    const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
    const dbConnectForm = document.getElementById('dbConnectForm');
    const dbTypeSelect = document.getElementById('dbTypeSelect');
    const dbParamsContainer = document.getElementById('dbParamsContainer');
    
    const sqlModal = document.getElementById('sqlModal');
    const closeSqlModalBtn = document.getElementById('closeSqlModalBtn');
    const closeSqlBtn = document.getElementById('closeSqlBtn');
    const sqlCodeContent = document.getElementById('sqlCodeContent');
    const copySqlBtn = document.getElementById('copySqlBtn');

    // Sidebar Right
    const rightSidebar = document.getElementById('rightSidebar');
    const closeRightSidebarBtn = document.getElementById('closeRightSidebarBtn');
    const tableDetailsContent = document.getElementById('tableDetailsContent');

    // Toolbars & Legend
    const zoomInBtn = document.getElementById('zoomInBtn');
    const zoomOutBtn = document.getElementById('zoomOutBtn');
    const zoomFitBtn = document.getElementById('zoomFitBtn');
    const layoutDagreBtn = document.getElementById('layoutDagreBtn');
    const layoutCoseBtn = document.getElementById('layoutCoseBtn');
    const layoutGridBtn = document.getElementById('layoutGridBtn');

    const exportPngBtn = document.getElementById('exportPngBtn');
    const exportSvgBtn = document.getElementById('exportSvgBtn');
    const exportSqlBtn = document.getElementById('exportSqlBtn');
    const saveWorkspaceBtn = document.getElementById('saveWorkspaceBtn');

    // --- Initialize Lucide Icons ---
    lucide.createIcons();

    // --- Initialize Cytoscape ---
    function initCytoscape() {
        // Register dagre layout
        if (typeof cytoscapeDagre !== 'undefined') {
            cytoscape.use(cytoscapeDagre);
        }

        cy = cytoscape({
            container: document.getElementById('cy'),
            boxSelectionEnabled: false,
            autounselectify: false,
            style: [
                {
                    selector: 'node',
                    style: {
                        'shape': 'round-rectangle',
                        'background-color': '#1e293b',
                        'border-width': '2px',
                        'border-color': '#4f46e5',
                        'border-opacity': '0.9',
                        'color': '#f8fafc',
                        'font-size': '10px',
                        'font-family': 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                        'text-wrap': 'wrap',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'padding': '14px',
                        'width': 'label',
                        'height': 'label',
                        'line-height': '1.4',
                        'label': 'data(label)',
                        'transition-property': 'background-color, border-color',
                        'transition-duration': '0.2s'
                    }
                },
                {
                    selector: 'node:selected',
                    style: {
                        'background-color': '#0f172a',
                        'border-color': '#f59e0b',
                        'border-width': '3px'
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'curve-style': 'bezier',
                        'line-color': '#64748b',
                        'target-arrow-shape': 'triangle',
                        'target-arrow-color': '#64748b',
                        'arrow-scale': 1.1,
                        'label': 'data(label)',
                        'font-size': '8px',
                        'color': '#94a3b8',
                        'text-background-opacity': 0.85,
                        'text-background-color': '#0b0f19',
                        'text-background-padding': '3px',
                        'text-background-shape': 'round-rectangle',
                        'text-wrap': 'wrap'
                    }
                },
                {
                    selector: 'edge.parent-child',
                    style: {
                        'line-color': '#3b82f6',
                        'target-arrow-color': '#3b82f6',
                        'target-arrow-shape': 'triangle'
                    }
                },
                {
                    selector: 'edge.prompt-table',
                    style: {
                        'line-color': '#ec4899',
                        'line-style': 'dashed',
                        'target-arrow-color': '#ec4899',
                        'target-arrow-shape': 'vee'
                    }
                },
                {
                    selector: 'edge.key-join',
                    style: {
                        'line-color': '#10b981',
                        'line-style': 'dotted',
                        'target-arrow-shape': 'none'
                    }
                }
            ],
            layout: {
                name: 'dagre',
                nodeSep: 60,
                rankSep: 80,
                rankDir: 'TB'
            }
        });

        // Node click listener -> show details
        cy.on('tap', 'node', (evt) => {
            const node = evt.target;
            const recname = node.id();
            showRecordDetails(recname);
        });

        // Canvas click listener -> close right sidebar if nothing selected
        cy.on('tap', (evt) => {
            if (evt.target === cy) {
                rightSidebar.classList.remove('open');
                cy.nodes().unselect();
            }
        });
    }

    // --- Helper functions ---

    function formatNodeLabel(record) {
        let label = `${record.recname.toUpperCase()}\n`;
        if (record.recdesc) {
            label += `(${record.recdesc})\n`;
        }
        label += `───────────────────────\n`;
        
        const keyFields = record.fields.filter(f => f.is_key);
        const nonKeyFields = record.fields.filter(f => !f.is_key).slice(0, 4);
        
        keyFields.forEach(f => {
            label += `🔑 ${f.fieldname} : ${f.fieldtype}\n`;
        });
        
        if (nonKeyFields.length > 0) {
            label += `───────────────────────\n`;
            nonKeyFields.forEach(f => {
                label += `   ${f.fieldname} : ${f.fieldtype}\n`;
            });
            if (record.fields.length - keyFields.length > 4) {
                label += `   ... (+${record.fields.length - keyFields.length - 4} columns)\n`;
            }
        }
        return label.trim();
    }

    // Run active Cytoscape layout
    function runLayout(layoutName = 'dagre') {
        let layoutOptions = {
            name: layoutName,
            animate: true,
            animationDuration: 400
        };

        if (layoutName === 'dagre') {
            layoutOptions.nodeSep = 60;
            layoutOptions.rankSep = 80;
            layoutOptions.rankDir = 'TB';
        } else if (layoutName === 'cose') {
            layoutOptions.nodeOverlap = 20;
            layoutOptions.idealEdgeLength = 100;
        }

        const layout = cy.layout(layoutOptions);
        layout.run();
        
        // Highlight active layout button
        document.querySelectorAll('.canvas-toolbar .toolbar-btn').forEach(btn => btn.classList.remove('active'));
        if (layoutName === 'dagre') layoutDagreBtn.classList.add('active');
        if (layoutName === 'cose') layoutCoseBtn.classList.add('active');
        if (layoutName === 'grid') layoutGridBtn.classList.add('active');
    }

    // Fetch and sync active DB connection status
    async function checkDbStatus() {
        const badge = document.getElementById('dbStatusBadge');
        const indicator = badge.querySelector('.status-indicator');
        const text = document.getElementById('dbStatusText');

        if (isUploadedMode) {
            indicator.className = 'status-indicator offline';
            text.textContent = `Uploaded JSON: ${uploadedRecords.size} Tables`;
            return;
        }

        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            dbStatus = data;
            
            indicator.className = 'status-indicator';
            if (dbStatus.connected) {
                if (dbStatus.dialect === 'sqlite') {
                    indicator.classList.add('warning');
                    text.textContent = 'SQLite Mock DB';
                } else {
                    indicator.classList.add('success');
                    text.textContent = `Connected: ${dbStatus.dialect.toUpperCase()}`;
                }
            } else {
                indicator.classList.add('danger');
                text.textContent = 'Disconnected';
            }
        } catch (err) {
            console.error('Failed to get status:', err);
        }
    }

    // --- Search Autocomplete Logic ---
    let searchTimeout = null;
    recordSearchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        const query = recordSearchInput.value.trim();
        
        if (!query) {
            clearSearchBtn.style.display = 'none';
            searchResultsDropdown.style.display = 'none';
            return;
        }
        
        clearSearchBtn.style.display = 'block';
        
        searchTimeout = setTimeout(async () => {
            const displayResults = (records) => {
                searchResultsDropdown.innerHTML = '';
                if (records.length === 0) {
                    const noResults = document.createElement('div');
                    noResults.className = 'search-result-item';
                    noResults.innerHTML = '<span class="result-name">No tables found</span>';
                    searchResultsDropdown.appendChild(noResults);
                } else {
                    records.forEach(rec => {
                        const item = document.createElement('div');
                        item.className = 'search-result-item';
                        item.innerHTML = `
                            <span class="result-name">${rec.recname}</span>
                            <span class="result-desc">${rec.recdesc || 'No description available'}</span>
                        `;
                        item.addEventListener('click', () => {
                            addTableToWorkspace(rec.recname);
                            searchResultsDropdown.style.display = 'none';
                            recordSearchInput.value = '';
                            clearSearchBtn.style.display = 'none';
                        });
                        searchResultsDropdown.appendChild(item);
                    });
                }
                searchResultsDropdown.style.display = 'block';
            };

            if (isUploadedMode) {
                const queryUpper = query.toUpperCase();
                const matched = [];
                for (const [recname, record] of uploadedRecords.entries()) {
                    if (recname.includes(queryUpper)) {
                        matched.push({
                            recname: recname,
                            recdesc: record.recdesc
                        });
                    }
                    if (matched.length >= 100) break;
                }
                displayResults(matched);
            } else {
                try {
                    const res = await fetch(`/api/records?search=${encodeURIComponent(query)}`);
                    const records = await res.json();
                    displayResults(records);
                } catch (err) {
                    console.error('Error fetching records:', err);
                }
            }
        }, 300);
    });

    clearSearchBtn.addEventListener('click', () => {
        recordSearchInput.value = '';
        clearSearchBtn.style.display = 'none';
        searchResultsDropdown.style.display = 'none';
    });

    // Close search dropdown on clicking outside
    document.addEventListener('click', (e) => {
        if (!recordSearchInput.contains(e.target) && !searchResultsDropdown.contains(e.target)) {
            searchResultsDropdown.style.display = 'none';
        }
    });

    // --- Table Workspace Management ---

    async function addTableToWorkspace(recname) {
        recname = recname.toUpperCase().trim();
        if (activeRecords.has(recname)) return; // Already exists

        try {
            let record;
            if (isUploadedMode) {
                if (!uploadedRecords.has(recname)) {
                    alert(`Record ${recname} tidak ditemukan di dalam schema upload.`);
                    return;
                }
                record = uploadedRecords.get(recname);
            } else {
                const res = await fetch(`/api/record/${recname}`);
                record = await res.json();
                
                if (record.error) {
                    alert(`Error loading metadata for ${recname}: ${record.error}`);
                    return;
                }
            }

            activeRecords.set(recname, record);
            
            // Add Node to Cytoscape
            cy.add({
                group: 'nodes',
                data: {
                    id: recname,
                    label: formatNodeLabel(record)
                }
            });

            // Update UI list
            renderActiveTablesList();
            
            // Load Relationships
            await updateRelationships();
            
            // Run Layout
            runLayout('dagre');

        } catch (err) {
            console.error('Failed to add table:', err);
        }
    }

    function removeTableFromWorkspace(recname) {
        recname = recname.toUpperCase().trim();
        if (!activeRecords.has(recname)) return;

        activeRecords.delete(recname);
        
        // Remove from Cytoscape (removes connected edges automatically)
        cy.remove(`#${recname}`);
        
        renderActiveTablesList();
        updateRelationships();
        
        // Close sidebar if removed table was selected
        const currentSidebarRec = document.querySelector('.details-table-title')?.textContent;
        if (currentSidebarRec === recname) {
            rightSidebar.classList.remove('open');
        }
    }

    function renderActiveTablesList() {
        activeTablesList.innerHTML = '';
        if (activeRecords.size === 0) {
            activeTablesList.innerHTML = '<li class="empty-list-msg">No tables added yet. Search and add tables from above.</li>';
            return;
        }

        activeRecords.forEach((record, name) => {
            const li = document.createElement('li');
            li.className = 'active-table-item';
            li.innerHTML = `
                <div class="table-item-info">
                    <span class="table-item-name">${name}</span>
                    <span class="table-item-parent">${record.parentrecord ? 'Parent: ' + record.parentrecord : 'Independent'}</span>
                </div>
                <div class="active-table-actions">
                    <button class="action-btn-small" data-action="locate" title="Locate Table"><i data-lucide="crosshair"></i></button>
                    <button class="action-btn-small delete-btn" data-action="delete" title="Remove Table"><i data-lucide="trash-2"></i></button>
                </div>
            `;
            
            // Wire Actions
            li.querySelector('[data-action="locate"]').addEventListener('click', () => {
                const node = cy.$(`#${name}`);
                if (node.length) {
                    cy.animate({
                        center: { eles: node },
                        zoom: 1.2
                    }, { duration: 400 });
                    node.select();
                    showRecordDetails(name);
                }
            });
            
            li.querySelector('[data-action="delete"]').addEventListener('click', () => {
                removeTableFromWorkspace(name);
            });

            activeTablesList.appendChild(li);
        });

        lucide.createIcons();
    }

    clearWorkspaceBtn.addEventListener('click', () => {
        activeRecords.clear();
        cy.elements().remove();
        renderActiveTablesList();
        rightSidebar.classList.remove('open');
    });

    // --- Relationship Syncer ---

    async function updateRelationships() {
        const recordNames = Array.from(activeRecords.keys());
        if (recordNames.length < 2) {
            // Remove existing edges if fewer than 2 nodes
            cy.edges().remove();
            return;
        }

        try {
            let relations = [];
            if (isUploadedMode) {
                relations = computeRelationshipsJS(activeRecords);
            } else {
                try {
                    const res = await fetch('/api/relationships', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ records: recordNames })
                    });
                    relations = await res.json();
                } catch (err) {
                    console.error('Failed to fetch relationships, falling back to local computation:', err);
                    relations = computeRelationshipsJS(activeRecords);
                }
            }

            // Clear old edges
            cy.edges().remove();

            // Add new edges
            relations.forEach(rel => {
                const sourceExists = cy.$(`#${rel.source}`).length > 0;
                const targetExists = cy.$(`#${rel.target}`).length > 0;

                if (sourceExists && targetExists) {
                    // Create descriptive label
                    let label = rel.label;
                    if (rel.source_field && rel.target_field) {
                        label += ` (${rel.source_field} = ${rel.target_field})`;
                    }

                    cy.add({
                        group: 'edges',
                        data: {
                            source: rel.source,
                            target: rel.target,
                            label: label
                        },
                        classes: rel.type
                    });
                }
            });
        } catch (err) {
            console.error('Failed to sync relationships:', err);
        }
    }

    // --- Relationship Expansion (Breadth-first fetching) ---

    expandRelationsBtn.addEventListener('click', async () => {
        const depth = parseInt(relationDepth.value) || 1;
        const currentRecords = Array.from(activeRecords.keys());
        
        if (currentRecords.length === 0) {
            alert('Please add at least one table to the workspace first!');
            return;
        }

        expandRelationsBtn.disabled = true;
        const expandSpan = expandRelationsBtn.querySelector('span');
        const oldText = expandSpan.textContent;
        expandSpan.textContent = 'Expanding...';

        try {
            if (isUploadedMode) {
                let currentActive = new Map(activeRecords);
                let explored = new Set(currentActive.keys());
                
                for (let d = 0; d < depth; d++) {
                    const newRelated = findRelatedRecordsLocal(currentActive, uploadedRecords);
                    if (newRelated.length === 0) break;
                    
                    for (const recname of newRelated) {
                        await addTableToWorkspace(recname);
                        currentActive.set(recname, uploadedRecords.get(recname));
                    }
                }
            } else {
                let recordsToSearch = [...currentRecords];
                let explored = new Set(currentRecords);

                for (let d = 0; d < depth; d++) {
                    // Fetch relationships for currently included tables to see what they point to
                    const res = await fetch('/api/relationships', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ records: recordsToSearch })
                    });
                    const relations = await res.json();
                    
                    let foundNew = [];
                    relations.forEach(rel => {
                        if (!explored.has(rel.source)) {
                            foundNew.push(rel.source);
                            explored.add(rel.source);
                        }
                        if (!explored.has(rel.target)) {
                            foundNew.push(rel.target);
                            explored.add(rel.target);
                        }
                    });

                    if (foundNew.length === 0) break; // No new tables found

                    // Fetch details and add to workspace
                    for (const newRec of foundNew) {
                        await addTableToWorkspace(newRec);
                    }
                    
                    // Add new items to next search round
                    recordsToSearch = Array.from(explored);
                }
            }
        } catch (err) {
            console.error('Failed to expand relationships:', err);
        } finally {
            expandRelationsBtn.disabled = false;
            expandSpan.textContent = oldText;
        }
    });

    // --- Sidebar Details Handler ---

    function showRecordDetails(recname) {
        const record = activeRecords.get(recname);
        if (!record) return;

        tableDetailsContent.innerHTML = `
            <div class="details-table-header">
                <span class="details-table-title">${record.recname}</span>
                <span class="details-table-desc">${record.recdesc || 'No description available'}</span>
                <span class="details-table-meta">
                    Parent Record: ${record.parentrecord ? `<strong>${record.parentrecord}</strong>` : '<em>None</em>'}
                </span>
                ${record.parentrecord && !activeRecords.has(record.parentrecord) ? 
                    `<button class="btn btn-secondary btn-icon btn-block" style="margin-top:8px;" id="addParentDetailsBtn">
                        <i data-lucide="plus"></i> Add Parent Table
                     </button>` : ''
                }
            </div>

            <div>
                <h4 class="field-list-title">Columns (${record.fields.length})</h4>
                <div class="fields-grid">
                    ${record.fields.map(f => `
                        <div class="field-row ${f.is_key ? 'is-key' : ''}">
                            <div class="field-info-left">
                                ${f.is_key ? '<span class="field-key-badge">PK</span>' : ''}
                                <span class="field-name-text">${f.fieldname}</span>
                            </div>
                            <div class="field-info-right">
                                <span class="field-type-badge">${f.fieldtype}(${f.length}${f.decimalpos ? `,${f.decimalpos}` : ''})</span>
                                ${f.edittable ? `
                                    <span class="field-prompt-badge" data-prompt="${f.edittable}" title="Prompts from table. Click to add.">
                                        👉 ${f.edittable}
                                    </span>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        lucide.createIcons();
        rightSidebar.classList.add('open');

        // Add parent button action
        const addParentBtn = document.getElementById('addParentDetailsBtn');
        if (addParentBtn) {
            addParentBtn.addEventListener('click', () => {
                addTableToWorkspace(record.parentrecord);
            });
        }

        // Add click actions to Prompt Badges
        document.querySelectorAll('.field-prompt-badge').forEach(badge => {
            badge.addEventListener('click', (e) => {
                const promptTable = e.target.getAttribute('data-prompt');
                addTableToWorkspace(promptTable);
            });
        });
    }

    closeRightSidebarBtn.addEventListener('click', () => {
        rightSidebar.classList.remove('open');
        cy.nodes().unselect();
    });

    // --- Floating Canvas Controls ---

    zoomInBtn.addEventListener('click', () => cy.zoom(cy.zoom() * 1.2));
    zoomOutBtn.addEventListener('click', () => cy.zoom(cy.zoom() * 0.8));
    zoomFitBtn.addEventListener('click', () => cy.fit(50));

    layoutDagreBtn.addEventListener('click', () => runLayout('dagre'));
    layoutCoseBtn.addEventListener('click', () => runLayout('cose'));
    layoutGridBtn.addEventListener('click', () => runLayout('grid'));

    // --- Settings Connection Modal ---

    openSettingsBtn.addEventListener('click', () => {
        document.getElementById('connectionErrorMsg').style.display = 'none';
        document.getElementById('connectionSuccessMsg').style.display = 'none';
        
        // Sync inputs with current dbStatus
        dbTypeSelect.value = dbStatus.dialect === 'sqlite' ? 'sqlite_mock' : dbStatus.dialect;
        toggleDbParamsDisplay();
        
        settingsModal.style.display = 'flex';
    });

    function toggleDbParamsDisplay() {
        if (dbTypeSelect.value === 'sqlite_mock') {
            dbParamsContainer.style.display = 'none';
        } else {
            dbParamsContainer.style.display = 'block';
            
            // Set port defaults
            const portInput = document.getElementById('dbPort');
            if (dbTypeSelect.value === 'oracle') portInput.placeholder = '1521';
            if (dbTypeSelect.value === 'mssql') portInput.placeholder = '1433';
            if (dbTypeSelect.value === 'postgresql') portInput.placeholder = '5432';
        }
    }

    dbTypeSelect.addEventListener('change', toggleDbParamsDisplay);

    function closeSettingsModal() {
        settingsModal.style.display = 'none';
    }

    closeSettingsModalBtn.addEventListener('click', closeSettingsModal);
    cancelSettingsBtn.addEventListener('click', closeSettingsModal);

    dbConnectForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const errorMsg = document.getElementById('connectionErrorMsg');
        const successMsg = document.getElementById('connectionSuccessMsg');
        const saveBtn = document.getElementById('saveConnectionBtn');
        
        errorMsg.style.display = 'none';
        successMsg.style.display = 'none';
        saveBtn.disabled = true;
        saveBtn.textContent = 'Connecting...';

        const payload = {
            db_type: dbTypeSelect.value,
            host: document.getElementById('dbHost').value.trim(),
            port: document.getElementById('dbPort').value.trim(),
            username: document.getElementById('dbUser').value.trim(),
            password: document.getElementById('dbPassword').value.trim(),
            dbname: document.getElementById('dbName').value.trim(),
            schema: document.getElementById('dbSchema').value.trim(),
            conn_string: document.getElementById('dbConnectionString').value.trim()
        };

        try {
            const res = await fetch('/api/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            if (res.ok) {
                successMsg.textContent = data.message;
                successMsg.style.display = 'block';
                
                // Switch mode back to DB
                isUploadedMode = false;
                uploadedRecords.clear();

                // Refresh status
                await checkDbStatus();
                
                // Clear Workspace on DB connection change to avoid mixed models
                activeRecords.clear();
                cy.elements().remove();
                renderActiveTablesList();
                rightSidebar.classList.remove('open');
                
                setTimeout(() => {
                    closeSettingsModal();
                }, 1000);
            } else {
                errorMsg.textContent = data.message || 'Connection failed.';
                errorMsg.style.display = 'block';
            }
        } catch (err) {
            errorMsg.textContent = 'Network or server error while connecting.';
            errorMsg.style.display = 'block';
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Connect & Save';
        }
    });

    // --- Export as PNG ---
    exportPngBtn.addEventListener('click', () => {
        if (activeRecords.size === 0) {
            alert('Cannot export an empty diagram!');
            return;
        }

        const pngContent = cy.png({
            output: 'blob',
            bg: '#0f172a', // Clean blueprint/dark output background
            full: true,
            scale: 2 // High res export
        });

        const url = URL.createObjectURL(pngContent);
        const a = document.createElement('a');
        a.href = url;
        a.download = `peoplesoft_erd_${new Date().toISOString().slice(0, 10)}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    // --- Export as SVG (Fallback / PNG description info) ---
    exportSvgBtn.addEventListener('click', () => {
        alert('SVG exporting uses custom vectors. Direct high-definition PNG export is available. Click PNG to export print-ready assets.');
    });

    // --- SQL Export Dialog ---

    exportSqlBtn.addEventListener('click', async () => {
        const recordNames = Array.from(activeRecords.keys());
        if (recordNames.length === 0) {
            alert('Workspace is empty! Add tables first.');
            return;
        }

        if (isUploadedMode) {
            const ddl = generateSqlDdlJS(activeRecords);
            sqlCodeContent.textContent = ddl || '-- No SQL generated';
            sqlModal.style.display = 'flex';
        } else {
            try {
                const res = await fetch('/api/export-sql', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ records: recordNames })
                });
                const data = await res.json();
                
                if (data.error) {
                    alert(`Error generating SQL: ${data.error}`);
                    return;
                }

                sqlCodeContent.textContent = data.sql || '-- No SQL generated';
                sqlModal.style.display = 'flex';
            } catch (err) {
                alert('Failed to contact server for SQL generation.');
            }
        }
    });

    function closeSqlModal() {
        sqlModal.style.display = 'none';
    }
    closeSqlModalBtn.addEventListener('click', closeSqlModal);
    closeSqlBtn.addEventListener('click', closeSqlModal);

    copySqlBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(sqlCodeContent.textContent)
            .then(() => {
                const btnText = copySqlBtn.innerHTML;
                copySqlBtn.innerHTML = '<i data-lucide="check"></i> Copied!';
                lucide.createIcons();
                setTimeout(() => {
                    copySqlBtn.innerHTML = btnText;
                    lucide.createIcons();
                }, 1500);
            })
            .catch(err => {
                console.error('Failed to copy text: ', err);
            });
    });

    // --- Save & Load Workspace ---

    saveWorkspaceBtn.addEventListener('click', () => {
        if (activeRecords.size === 0) {
            alert('Workspace is empty! Nothing to save.');
            return;
        }

        // Gather list of table names and their coordinates
        const elements = cy.nodes().map(node => ({
            id: node.id(),
            position: node.position()
        }));

        const workspaceData = {
            version: '1.0',
            db_dialect: dbStatus.dialect,
            tables: Array.from(activeRecords.keys()),
            positions: elements
        };

        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(workspaceData, null, 2));
        const a = document.createElement('a');
        a.setAttribute("href", dataStr);
        a.setAttribute("download", `peoplesoft_workspace_${new Date().toISOString().slice(0, 10)}.json`);
        document.body.appendChild(a);
        a.click();
        a.remove();
    });

    // Support loading workspace files or drag & drop (future feature)
    // For now, load default mock tables on empty workspace to showcase
    async function loadSampleWorkspace() {
        await addTableToWorkspace('PERSONAL_DATA');
        await addTableToWorkspace('JOB');
        await addTableToWorkspace('NAMES');
        await addTableToWorkspace('DEPT_TBL');
        await updateRelationships();
        runLayout('dagre');
    }

    // --- Local Computation Helpers ---

    function computeRelationshipsJS(recordsMap) {
        const relationships = [];
        const selectedNames = Array.from(recordsMap.keys());

        // 1. Parent-child links
        for (const [recname, record] of recordsMap.entries()) {
            if (record.parentrecord) {
                const parent = record.parentrecord.toUpperCase().trim();
                if (recordsMap.has(parent)) {
                    relationships.push({
                        source: parent,
                        target: recname,
                        type: 'parent-child',
                        label: 'Parent-Child',
                        source_field: 'EMPLID',
                        target_field: 'EMPLID'
                    });
                }
            }
        }

        // 2. Prompt table edits
        for (const [recname, record] of recordsMap.entries()) {
            for (const field of record.fields) {
                if (field.edittable) {
                    const promptTable = field.edittable.toUpperCase().trim();
                    if (recordsMap.has(promptTable)) {
                        relationships.push({
                            source: recname,
                            target: promptTable,
                            type: 'prompt-table',
                            label: `Prompts on ${field.fieldname}`,
                            source_field: field.fieldname,
                            target_field: 'KEY'
                        });
                    }
                }
            }
        }

        // 3. Share-Key relationships (Logical Joins)
        const keyFieldsByTable = {};
        for (const [recname, record] of recordsMap.entries()) {
            keyFieldsByTable[recname] = new Set(
                record.fields.filter(f => f.is_key).map(f => f.fieldname)
            );
        }

        for (let i = 0; i < selectedNames.length; i++) {
            for (let j = i + 1; j < selectedNames.length; j++) {
                const rec1 = selectedNames[i];
                const rec2 = selectedNames[j];

                let alreadyLinked = false;
                for (const r of relationships) {
                    if ((r.source === rec1 && r.target === rec2) || (r.source === rec2 && r.target === rec1)) {
                        alreadyLinked = true;
                        break;
                    }
                }
                if (alreadyLinked) continue;

                const keys1 = keyFieldsByTable[rec1];
                const keys2 = keyFieldsByTable[rec2];
                const commonKeys = [...keys1].filter(x => keys2.has(x));

                if (commonKeys.length > 0) {
                    const matchField = commonKeys[0];
                    relationships.push({
                        source: rec1,
                        target: rec2,
                        type: 'key-join',
                        label: `Key Join (${matchField})`,
                        source_field: matchField,
                        target_field: matchField
                    });
                }
            }
        }
        return relationships;
    }

    function generateSqlDdlJS(recordsMap) {
        const ddlStatements = [];
        for (const [recname, record] of recordsMap.entries()) {
            const fieldLines = [];
            const primaryKeys = [];
            
            for (const f of record.fields) {
                let sql_type = 'VARCHAR(255)';
                const ftype = f.fieldtype;
                const flength = f.length;
                const fdec = f.decimalpos;
                
                if (ftype === 'Char') {
                    sql_type = `VARCHAR(${flength})`;
                } else if (ftype === 'Long Char') {
                    sql_type = 'TEXT';
                } else if (ftype === 'Number' || ftype === 'Signed Number') {
                    if (fdec > 0) {
                        sql_type = `DECIMAL(${flength}, ${fdec})`;
                    } else {
                        sql_type = flength < 10 ? 'INT' : 'BIGINT';
                    }
                } else if (ftype === 'Date') {
                    sql_type = 'DATE';
                } else if (ftype === 'Time') {
                    sql_type = 'TIME';
                } else if (ftype === 'DateTime') {
                    sql_type = 'TIMESTAMP';
                } else {
                    sql_type = `VARCHAR(${flength || 255})`;
                }
                
                let fieldDef = `    ${f.fieldname} ${sql_type}`;
                if (f.is_key) {
                    fieldDef += " NOT NULL";
                    primaryKeys.push(f.fieldname);
                }
                fieldLines.push(fieldDef);
            }
            
            if (primaryKeys.length > 0) {
                fieldLines.push(`    CONSTRAINT PK_PS_${recname} PRIMARY KEY (${primaryKeys.join(', ')})`);
            }
            
            const ddl = `CREATE TABLE PS_${recname} (\n${fieldLines.join(',\n')}\n);`;
            ddlStatements.push(ddl);
        }
        return ddlStatements.join('\n\n');
    }

    function findRelatedRecordsLocal(activeMap, allMap) {
        const related = new Set();
        const activeNames = new Set(Array.from(activeMap.keys()));

        for (const activeName of activeNames) {
            const activeRecord = allMap.get(activeName);
            if (!activeRecord) continue;

            if (activeRecord.parentrecord) {
                const parent = activeRecord.parentrecord.toUpperCase().trim();
                if (allMap.has(parent) && !activeNames.has(parent)) {
                    related.add(parent);
                }
            }

            for (const [recname, record] of allMap.entries()) {
                if (record.parentrecord && record.parentrecord.toUpperCase().trim() === activeName) {
                    if (!activeNames.has(recname)) {
                        related.add(recname);
                    }
                }
            }

            for (const field of activeRecord.fields) {
                if (field.edittable) {
                    const prompt = field.edittable.toUpperCase().trim();
                    if (allMap.has(prompt) && !activeNames.has(prompt)) {
                        related.add(prompt);
                    }
                }
            }

            for (const [recname, record] of allMap.entries()) {
                for (const field of record.fields) {
                    if (field.edittable && field.edittable.toUpperCase().trim() === activeName) {
                        if (!activeNames.has(recname)) {
                            related.add(recname);
                        }
                    }
                }
            }
        }
        return Array.from(related);
    }

    async function handleUploadedFile(file) {
        const reader = new FileReader();
        reader.onload = async function(e) {
            try {
                const data = JSON.parse(e.target.result);
                if (!data.records || !Array.isArray(data.records)) {
                    alert('Format JSON tidak cocok. File harus memiliki properti "records" berupa array.');
                    return;
                }
                
                activeRecords.clear();
                cy.elements().remove();
                rightSidebar.classList.remove('open');
                
                isUploadedMode = true;
                uploadedRecords.clear();
                
                data.records.forEach(rec => {
                    uploadedRecords.set(rec.recname.toUpperCase().trim(), rec);
                });
                
                for (const recname of uploadedRecords.keys()) {
                    await addTableToWorkspace(recname);
                }
                
                renderActiveTablesList();
                await checkDbStatus();
                runLayout('dagre');
                
                console.log(`Loaded ${uploadedRecords.size} tables from JSON.`);
                
            } catch (err) {
                console.error(err);
                alert('Gagal membaca file JSON: ' + err.message);
            }
        };
        reader.readAsText(file);
    }

    // --- Upload Button Listeners & Drag and Drop Handlers ---
    
    if (uploadJsonBtn) {
        uploadJsonBtn.addEventListener('click', () => uploadJsonInput.click());
    }
    if (sidebarUploadJsonBtn) {
        sidebarUploadJsonBtn.addEventListener('click', () => uploadJsonInput.click());
    }
    if (uploadJsonInput) {
        uploadJsonInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleUploadedFile(e.target.files[0]);
            }
        });
    }

    if (canvasPanel && dragOverlay) {
        window.addEventListener('dragover', (e) => e.preventDefault(), false);
        window.addEventListener('drop', (e) => e.preventDefault(), false);

        canvasPanel.addEventListener('dragover', (e) => {
            e.preventDefault();
            dragOverlay.style.display = 'flex';
        });

        canvasPanel.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dragOverlay.style.display = 'none';
        });

        canvasPanel.addEventListener('drop', (e) => {
            e.preventDefault();
            dragOverlay.style.display = 'none';

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleUploadedFile(files[0]);
            }
        });
    }

    // --- Startup Script ---
    initCytoscape();
    checkDbStatus().then(() => {
        // Load default mock workspace on start if empty
        if (activeRecords.size === 0) {
            loadSampleWorkspace();
        }
    });
});
