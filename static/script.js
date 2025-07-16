const countries = ["US", "GB", "ES", "NL", "FR", "IE", "CA", "DE", "IT", "PL", "DK", "NO", "SE", "EE", "LT", "LV", "PT", "BE"];
const products = ["assets", "auth", "balance", "employment", "identity", "income_verification", "identity_verification", "investments", "liabilities", "payment_initiation", "standing_orders", "transactions", "transfer"];

let csvData = null;

// Initialize the form
document.addEventListener('DOMContentLoaded', function() {
    initializeCheckboxes();
    setupEventListeners();
});

function initializeCheckboxes() {
    const countryContainer = document.getElementById('countryCheckboxes');
    const productContainer = document.getElementById('productCheckboxes');

    // Create country checkboxes
    countries.forEach(country => {
        const colDiv = document.createElement('div');
        colDiv.className = 'col-md-3 col-sm-6';
        colDiv.innerHTML = `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="country_${country}" value="${country}">
                <label class="form-check-label" for="country_${country}">${country}</label>
            </div>
        `;
        countryContainer.appendChild(colDiv);
    });

    // Create product checkboxes
    products.forEach(product => {
        const colDiv = document.createElement('div');
        colDiv.className = 'col-md-3 col-sm-6';
        colDiv.innerHTML = `
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="product_${product}" value="${product}">
                <label class="form-check-label" for="product_${product}">${product}</label>
            </div>
        `;
        productContainer.appendChild(colDiv);
    });
}

function setupEventListeners() {
    document.getElementById('institutionForm').addEventListener('submit', handleFormSubmit);
    document.getElementById('downloadButton').addEventListener('click', downloadCSV);
}

function handleFormSubmit(e) {
    e.preventDefault();
    
    const fetchButton = document.getElementById('fetchButton');
    const spinner = fetchButton.querySelector('.spinner-border');
    const buttonText = fetchButton.textContent;
    
    // Show loading state
    fetchButton.disabled = true;
    spinner.classList.remove('d-none');
    fetchButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Fetching...';
    
    // Hide previous results/errors
    document.getElementById('results').classList.add('d-none');
    document.getElementById('error').classList.add('d-none');
    
    // Collect form data
    const formData = {
        country_codes: getCheckedValues('input[id^="country_"]:checked'),
        selected_products: getCheckedValues('input[id^="product_"]:checked'),
        routing_numbers: document.getElementById('routingNumbers').value
            .split(',')
            .map(r => r.trim())
            .filter(r => r),
        oauth: document.getElementById('oauth').checked,
        include_optional_metadata: document.getElementById('includeOptionalMetadata').checked,
        include_auth_metadata: document.getElementById('includeAuthMetadata').checked,
        include_payment_initiation_metadata: document.getElementById('includePaymentInitiationMetadata').checked
    };
    
    // Send request to backend
    fetch('/api/institutions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Store CSV data for download
        csvData = data.csv_data;
        
        // Show success message
        document.getElementById('resultsText').textContent = 
            `Total institutions fetched: ${data.total_institutions}. ` +
            `Institutions after product filter: ${data.filtered_institutions}`;
        document.getElementById('results').classList.remove('d-none');
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('errorText').textContent = error.message;
        document.getElementById('error').classList.remove('d-none');
    })
    .finally(() => {
        // Reset button state
        fetchButton.disabled = false;
        spinner.classList.add('d-none');
        fetchButton.textContent = 'Fetch Institutions';
    });
}

function getCheckedValues(selector) {
    return Array.from(document.querySelectorAll(selector)).map(cb => cb.value);
}

function downloadCSV() {
    if (!csvData) {
        alert('No data available for download');
        return;
    }
    
    const downloadButton = document.getElementById('downloadButton');
    downloadButton.disabled = true;
    downloadButton.textContent = 'Downloading...';
    
    fetch('/api/download-csv', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ csv_data: csvData })
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `institutions_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    })
    .catch(error => {
        console.error('Error downloading CSV:', error);
        alert('Error downloading CSV file');
    })
    .finally(() => {
        downloadButton.disabled = false;
        downloadButton.textContent = 'Download CSV';
    });
}