// State management
let uploadedDocuments = [];
let analysisResults = null;

// DOM elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const contextInput = document.getElementById('context-input');
const documentsList = document.getElementById('documents-list');
const documentsContainer = document.getElementById('documents-container');
const analyzeBtn = document.getElementById('analyze-btn');
const progressSection = document.getElementById('progress-section');
const progressText = document.getElementById('progress-text');
const resultsSection = document.getElementById('results-section');
const resultsContainer = document.getElementById('results-container');
const errorSection = document.getElementById('error-section');
const errorMessage = document.getElementById('error-message');
const dismissErrorBtn = document.getElementById('dismiss-error-btn');
const exportMarkdownBtn = document.getElementById('export-markdown-btn');
const exportTxtBtn = document.getElementById('export-txt-btn');

// Event listeners
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', handleDragOver);
dropZone.addEventListener('dragleave', handleDragLeave);
dropZone.addEventListener('drop', handleDrop);
fileInput.addEventListener('change', handleFileSelect);
analyzeBtn.addEventListener('click', analyzeDocuments);
dismissErrorBtn.addEventListener('click', hideError);
exportMarkdownBtn.addEventListener('click', () => exportAnalysis('markdown'));
exportTxtBtn.addEventListener('click', () => exportAnalysis('txt'));

// Drag and drop handlers
function handleDragOver(e) {
    e.preventDefault();
    dropZone.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    uploadFiles(files);
}

function handleFileSelect(e) {
    const files = e.target.files;
    uploadFiles(files);
}

// Upload files
async function uploadFiles(files) {
    hideError();
    
    for (let file of files) {
        // Validate file type
        const validTypes = ['.pdf', '.docx', '.txt'];
        const fileName = file.name.toLowerCase();
        const isValid = validTypes.some(type => fileName.endsWith(type));
        
        if (!isValid) {
            showError(`"${file.name}" is not a supported file type. Please upload PDF, DOCX, or TXT files.`);
            continue;
        }
        
        // Upload file
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            progressText.textContent = `Uploading ${file.name}...`;
            progressSection.style.display = 'block';
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            progressSection.style.display = 'none';
            
            if (!response.ok) {
                const error = await response.json();
                showError(error.detail || `Failed to upload ${file.name}`);
                continue;
            }
            
            const docInfo = await response.json();
            uploadedDocuments.push(docInfo);
            updateDocumentsList();
            
        } catch (error) {
            progressSection.style.display = 'none';
            showError(`Error uploading ${file.name}: ${error.message}`);
        }
    }
    
    // Reset file input
    fileInput.value = '';
}

// Update documents list UI
function updateDocumentsList() {
    if (uploadedDocuments.length === 0) {
        documentsList.style.display = 'none';
        analyzeBtn.style.display = 'none';
        return;
    }
    
    documentsList.style.display = 'block';
    analyzeBtn.style.display = 'block';
    
    documentsContainer.innerHTML = uploadedDocuments.map(doc => `
        <div class="document-item">
            <div class="document-info">
                <div class="document-name">${escapeHtml(doc.filename)}</div>
                <div class="document-meta">
                    ${doc.pages ? `${doc.pages} pages • ` : ''}
                    ${doc.word_count.toLocaleString()} words • 
                    ${formatFileSize(doc.file_size)}
                </div>
            </div>
            <button class="remove-btn" onclick="removeDocument('${doc.doc_id}')">Remove</button>
        </div>
    `).join('');
}

// Remove document
async function removeDocument(docId) {
    try {
        const response = await fetch(`/api/documents/${docId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            uploadedDocuments = uploadedDocuments.filter(doc => doc.doc_id !== docId);
            updateDocumentsList();
            
            // Hide results if we removed all documents
            if (uploadedDocuments.length === 0) {
                resultsSection.style.display = 'none';
            }
        }
    } catch (error) {
        showError(`Error removing document: ${error.message}`);
    }
}

// Analyze documents
async function analyzeDocuments() {
    if (uploadedDocuments.length === 0) {
        showError('Please upload at least one document before analyzing.');
        return;
    }
    
    hideError();
    resultsSection.style.display = 'none';
    progressSection.style.display = 'block';
    progressText.textContent = 'Analyzing documents with AI...';
    analyzeBtn.disabled = true;
    
    try {
        const requestBody = {
            doc_ids: uploadedDocuments.map(doc => doc.doc_id),
            context: contextInput.value.trim() || null
        };
        
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        progressSection.style.display = 'none';
        analyzeBtn.disabled = false;
        
        if (!response.ok) {
            const error = await response.json();
            showError(error.detail || 'Failed to analyze documents');
            return;
        }
        
        analysisResults = await response.json();
        displayResults();
        
    } catch (error) {
        progressSection.style.display = 'none';
        analyzeBtn.disabled = false;
        showError(`Error analyzing documents: ${error.message}`);
    }
}

// Display results
function displayResults() {
    if (!analysisResults) return;
    
    resultsContainer.innerHTML = '';
    
    // Display each document's analysis
    for (let doc of analysisResults.documents) {
        const analysis = analysisResults.analyses[doc.doc_id];
        const docElement = createDocumentAnalysisElement(doc, analysis);
        resultsContainer.appendChild(docElement);
    }
    
    // Display cross-document analysis if available
    if (analysisResults.cross_document_analysis) {
        const crossDocElement = createCrossDocumentAnalysisElement(analysisResults.cross_document_analysis);
        resultsContainer.appendChild(crossDocElement);
    }
    
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Create document analysis element
function createDocumentAnalysisElement(doc, analysis) {
    const div = document.createElement('div');
    div.className = 'document-analysis';
    
    div.innerHTML = `
        <h3>${escapeHtml(doc.filename)}</h3>
        
        <div class="analysis-section">
            <h4>Executive Summary</h4>
            <p>${escapeHtml(analysis.executive_summary)}</p>
        </div>
        
        <div class="analysis-section">
            <h4>Key Data Points & Statistics</h4>
            ${createList(analysis.key_data_points)}
        </div>
        
        <div class="analysis-section">
            <h4>Action Items & Recommendations</h4>
            ${createList(analysis.action_items)}
        </div>
        
        <div class="analysis-section">
            <h4>Risks & Gaps</h4>
            ${createList(analysis.risks_and_gaps)}
        </div>
        
        <div class="analysis-section">
            <h4>Critical Quotes & Passages</h4>
            ${createList(analysis.critical_quotes)}
        </div>
    `;
    
    return div;
}

// Create cross-document analysis element
function createCrossDocumentAnalysisElement(crossDoc) {
    const div = document.createElement('div');
    div.className = 'cross-document-analysis';
    
    div.innerHTML = `
        <h3>Cross-Document Analysis</h3>
        
        <div class="analysis-section">
            <h4>Common Themes</h4>
            ${createList(crossDoc.common_themes)}
        </div>
        
        <div class="analysis-section">
            <h4>Key Differences</h4>
            ${createList(crossDoc.key_differences)}
        </div>
        
        <div class="analysis-section">
            <h4>Patterns & Trends</h4>
            ${createList(crossDoc.patterns_and_trends)}
        </div>
        
        <div class="analysis-section">
            <h4>Synthesis</h4>
            <p>${escapeHtml(crossDoc.synthesis)}</p>
        </div>
    `;
    
    return div;
}

// Create list HTML
function createList(items) {
    if (!items || items.length === 0) {
        return '<p>None identified</p>';
    }
    
    return '<ul>' + items.map(item => `<li>${escapeHtml(item)}</li>`).join('') + '</ul>';
}

// Export analysis
function exportAnalysis(format) {
    if (!analysisResults) return;
    
    let content = '';
    const timestamp = new Date().toISOString().split('T')[0];
    
    if (format === 'markdown') {
        content = generateMarkdown();
    } else {
        content = generatePlainText();
    }
    
    // Create download
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    
    const firstDoc = analysisResults.documents[0].filename.replace(/\.[^/.]+$/, '');
    const extension = format === 'markdown' ? 'md' : 'txt';
    a.download = `DocIntel_${firstDoc}_${timestamp}.${extension}`;
    
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Generate Markdown export
function generateMarkdown() {
    let md = '# DocIntel Analysis Report\n\n';
    md += `**Generated:** ${new Date().toLocaleString()}\n\n`;
    
    if (analysisResults.context_used) {
        md += `**Analysis Focus:** ${analysisResults.context_used}\n\n`;
    }
    
    md += '---\n\n';
    
    // Document analyses
    for (let doc of analysisResults.documents) {
        const analysis = analysisResults.analyses[doc.doc_id];
        
        md += `## ${doc.filename}\n\n`;
        
        md += `### Executive Summary\n\n${analysis.executive_summary}\n\n`;
        
        md += `### Key Data Points & Statistics\n\n`;
        md += formatListMarkdown(analysis.key_data_points);
        
        md += `### Action Items & Recommendations\n\n`;
        md += formatListMarkdown(analysis.action_items);
        
        md += `### Risks & Gaps\n\n`;
        md += formatListMarkdown(analysis.risks_and_gaps);
        
        md += `### Critical Quotes & Passages\n\n`;
        md += formatListMarkdown(analysis.critical_quotes);
        
        md += '---\n\n';
    }
    
    // Cross-document analysis
    if (analysisResults.cross_document_analysis) {
        const crossDoc = analysisResults.cross_document_analysis;
        
        md += `## Cross-Document Analysis\n\n`;
        
        md += `### Common Themes\n\n`;
        md += formatListMarkdown(crossDoc.common_themes);
        
        md += `### Key Differences\n\n`;
        md += formatListMarkdown(crossDoc.key_differences);
        
        md += `### Patterns & Trends\n\n`;
        md += formatListMarkdown(crossDoc.patterns_and_trends);
        
        md += `### Synthesis\n\n${crossDoc.synthesis}\n\n`;
    }
    
    return md;
}

// Generate plain text export
function generatePlainText() {
    let txt = 'DOCINTEL ANALYSIS REPORT\n';
    txt += '========================\n\n';
    txt += `Generated: ${new Date().toLocaleString()}\n\n`;
    
    if (analysisResults.context_used) {
        txt += `Analysis Focus: ${analysisResults.context_used}\n\n`;
    }
    
    txt += '------------------------\n\n';
    
    // Document analyses
    for (let doc of analysisResults.documents) {
        const analysis = analysisResults.analyses[doc.doc_id];
        
        txt += `DOCUMENT: ${doc.filename}\n\n`;
        
        txt += `EXECUTIVE SUMMARY\n${analysis.executive_summary}\n\n`;
        
        txt += `KEY DATA POINTS & STATISTICS\n`;
        txt += formatListPlainText(analysis.key_data_points);
        
        txt += `ACTION ITEMS & RECOMMENDATIONS\n`;
        txt += formatListPlainText(analysis.action_items);
        
        txt += `RISKS & GAPS\n`;
        txt += formatListPlainText(analysis.risks_and_gaps);
        
        txt += `CRITICAL QUOTES & PASSAGES\n`;
        txt += formatListPlainText(analysis.critical_quotes);
        
        txt += '------------------------\n\n';
    }
    
    // Cross-document analysis
    if (analysisResults.cross_document_analysis) {
        const crossDoc = analysisResults.cross_document_analysis;
        
        txt += `CROSS-DOCUMENT ANALYSIS\n\n`;
        
        txt += `COMMON THEMES\n`;
        txt += formatListPlainText(crossDoc.common_themes);
        
        txt += `KEY DIFFERENCES\n`;
        txt += formatListPlainText(crossDoc.key_differences);
        
        txt += `PATTERNS & TRENDS\n`;
        txt += formatListPlainText(crossDoc.patterns_and_trends);
        
        txt += `SYNTHESIS\n${crossDoc.synthesis}\n\n`;
    }
    
    return txt;
}

// Format list for Markdown
function formatListMarkdown(items) {
    if (!items || items.length === 0) {
        return 'None identified\n\n';
    }
    return items.map(item => `- ${item}`).join('\n') + '\n\n';
}

// Format list for plain text
function formatListPlainText(items) {
    if (!items || items.length === 0) {
        return 'None identified\n\n';
    }
    return items.map(item => `  - ${item}`).join('\n') + '\n\n';
}

// Error handling
function showError(message) {
    errorMessage.textContent = message;
    errorSection.style.display = 'block';
    errorSection.scrollIntoView({ behavior: 'smooth' });
}

function hideError() {
    errorSection.style.display = 'none';
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}
