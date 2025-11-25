// Configuration
const API_BASE_URL = '';
const API_KEY = 'test_gateway_key_12345';

// Elements
const statusEl = document.getElementById('status');
const statusText = statusEl.querySelector('.status-text');
const promptEl = document.getElementById('prompt');
const executeCodeEl = document.getElementById('execute-code');
const verifyEl = document.getElementById('verify');
const temperatureEl = document.getElementById('temperature');
const tempValueEl = document.getElementById('temp-value');
const submitBtn = document.getElementById('submit-btn');
const resultsSection = document.getElementById('results-section');
const modelResponsesEl = document.getElementById('model-responses');
const totalLatencyEl = document.getElementById('total-latency');
const strategyEl = document.getElementById('strategy');
const verificationReportEl = document.getElementById('verification-report');

// Initialize
checkHealth();
temperatureEl.addEventListener('input', (e) => {
    tempValueEl.textContent = e.target.value;
});

submitBtn.addEventListener('click', runInference);

// UX: Verify requires Execute Code
verifyEl.addEventListener('change', () => {
    if (verifyEl.checked) {
        executeCodeEl.checked = true;
        executeCodeEl.disabled = true;
        executeCodeEl.parentElement.title = "Execution is required for verification";
    } else {
        executeCodeEl.disabled = false;
        executeCodeEl.parentElement.title = "";
    }
});

// Check API health
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/health`);
        const data = await response.json();

        if (data.status === 'healthy') {
            statusEl.classList.add('healthy');
            const workingProviders = Object.entries(data.providers)
                .filter(([_, healthy]) => healthy)
                .map(([name]) => name);
            statusText.textContent = `Operational (${workingProviders.join(', ')})`;
        } else {
            statusEl.classList.add('error');
            statusText.textContent = 'Service Unavailable';
        }
    } catch (error) {
        statusEl.classList.add('error');
        statusText.textContent = 'Connection Failed';
        console.error('Health check failed:', error);
    }
}

// Run inference
async function runInference() {
    const prompt = promptEl.value.trim();

    if (!prompt) {
        alert('Please enter a prompt');
        return;
    }

    // Disable button and show loading
    submitBtn.disabled = true;
    submitBtn.classList.add('loading');

    // Clear previous results
    modelResponsesEl.innerHTML = '';
    verificationReportEl.style.display = 'none';
    resultsSection.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/inference`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': API_KEY
            },
            body: JSON.stringify({
                prompt: prompt,
                execute_code: executeCodeEl.checked,
                verify: verifyEl.checked,
                temperature: parseFloat(temperatureEl.value)
            })
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const data = await response.json();
        displayResults(data);

    } catch (error) {
        console.error('Inference failed:', error);
        alert(`Error: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.classList.remove('loading');
    }
}

// Display results
function displayResults(data) {
    resultsSection.style.display = 'block';

    // Update metrics
    totalLatencyEl.textContent = `${data.total_latency.toFixed(2)}s`;

    if (data.verification) {
        strategyEl.textContent = data.verification.synthesis_strategy
            .split('_')
            .map(w => w.charAt(0).toUpperCase() + w.slice(1))
            .join(' ');

        // Show verification report
        displayVerificationReport(data.verification);
    } else {
        strategyEl.textContent = 'None';
    }

    // Display model responses
    data.model_responses.forEach(response => {
        const isSelected = data.selected_response &&
            response.provider === data.selected_response.provider &&
            response.model_name === data.selected_response.model_name;

        const card = createModelCard(response, isSelected);
        modelResponsesEl.appendChild(card);
    });

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Create model card
function createModelCard(response, isSelected) {
    const card = document.createElement('div');
    card.className = `model-card ${isSelected ? 'selected' : ''}`;

    const icon = response.provider.charAt(0).toUpperCase();
    const providerName = response.provider.charAt(0).toUpperCase() + response.provider.slice(1);

    let content = `
        <div class="model-header">
            <div class="model-info">
                <div class="model-icon">${icon}</div>
                <div>
                    <div class="model-name">${response.model_name}</div>
                    <div class="model-provider">${providerName}</div>
                </div>
            </div>
            <div class="model-latency">${response.latency.toFixed(2)}s</div>
        </div>
    `;

    if (isSelected) {
        content += '<div class="badge success">✓ Selected Response</div>';
    }

    if (response.error) {
        content += `<div class="error-message">Error: ${response.error}</div>`;
    } else if (response.text) {
        content += `<div class="model-response-text">${escapeHtml(response.text)}</div>`;

        // Show execution results if available
        if (response.execution_results && response.execution_results.length > 0) {
            content += '<div class="execution-results" style="margin-top: 1rem;">';
            content += '<h4 style="margin-bottom: 0.5rem;">Execution Results:</h4>';

            response.execution_results.forEach((result, idx) => {
                const status = result.success ? 'success' : 'error';
                content += `
                    <div class="badge ${status}" style="margin-bottom: 0.5rem;">
                        Result ${idx + 1}: ${result.success ? '✓ Success' : '✗ Failed'} 
                        (${result.execution_time.toFixed(2)}s)
                    </div>
                `;

                if (result.stdout) {
                    content += `<pre style="background: var(--bg-tertiary); padding: 1rem; border-radius: 8px; margin-top: 0.5rem; overflow-x: auto;"><code>${escapeHtml(result.stdout)}</code></pre>`;
                }

                if (result.stderr) {
                    content += `<pre style="background: rgba(239, 68, 68, 0.1); padding: 1rem; border-radius: 8px; margin-top: 0.5rem; overflow-x: auto; color: var(--error);"><code>${escapeHtml(result.stderr)}</code></pre>`;
                }
            });

            content += '</div>';
        }
    }

    card.innerHTML = content;
    return card;
}

// Display verification report
function displayVerificationReport(verification) {
    if (!verification) return;

    verificationReportEl.style.display = 'block';

    const consensusBadge = verification.consensus
        ? '<span class="badge success">✓ Consensus Reached</span>'
        : '<span class="badge warning">⚠ No Consensus</span>';

    const verifiedBadge = verification.verified
        ? '<span class="badge success">✓ Verified</span>'
        : '<span class="badge warning">Not Verified</span>';

    let content = `
        <h3>Verification Report</h3>
        <div class="verification-badges">
            ${consensusBadge}
            ${verifiedBadge}
            <span class="badge">Strategy: ${verification.synthesis_strategy}</span>
            <span class="badge">Successful: ${verification.successful_executions}/${verification.total_executions}</span>
        </div>
    `;

    if (verification.details && verification.details.scores) {
        content += '<div style="margin-top: 1rem;"><strong>Provider Scores:</strong><br>';
        Object.entries(verification.details.scores).forEach(([provider, score]) => {
            const percentage = (score * 100).toFixed(0);
            content += `
                <div style="margin-top: 0.5rem;">
                    <span style="color: var(--text-secondary);">${provider}:</span>
                    <span style="color: var(--primary); font-weight: 600;">${percentage}%</span>
                    <div style="width: 100%; height: 6px; background: var(--bg-tertiary); border-radius: 3px; margin-top: 0.25rem;">
                        <div style="width: ${percentage}%; height: 100%; background: var(--gradient); border-radius: 3px;"></div>
                    </div>
                </div>
            `;
        });
        content += '</div>';
    }

    verificationReportEl.innerHTML = content;
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
