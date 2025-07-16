from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import csv
import requests
import time
import io
import os
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

# Add this route for static files
@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# Keep your existing routes...
@app.route('/')
def index():
    return send_file('static/index.html')

# Move credentials to environment variables for security
CLIENT_ID = os.getenv('PLAID_CLIENT_ID', '638a31f9c71c5a0014c2de77')
SECRET_KEY = os.getenv('PLAID_SECRET_KEY', 'aa9b0d6e64bc781ab58f97e4358e6c')
PLAID_ENV = os.getenv('PLAID_ENV', 'sandbox')

def get_plaid_url():
    if PLAID_ENV == 'production':
        return "https://production.plaid.com"
    elif PLAID_ENV == 'development':
        return "https://development.plaid.com"
    else:
        return "https://sandbox.plaid.com"

def fetch_institutions_with_delay(country_codes, routing_numbers, oauth, include_optional_metadata, include_auth_metadata, include_payment_initiation_metadata, delay=6):
    url = f"{get_plaid_url()}/institutions/get"
    offset = 0
    institutions = []

    while True:
        payload = {
            "client_id": CLIENT_ID,
            "secret": SECRET_KEY,
            "count": 500,
            "offset": offset,
            "country_codes": country_codes,
            "options": {}
        }

        if routing_numbers:
            payload["options"]["routing_numbers"] = routing_numbers
        if oauth:
            payload["options"]["oauth"] = oauth
        if include_optional_metadata:
            payload["options"]["include_optional_metadata"] = include_optional_metadata
        if include_auth_metadata:
            payload["options"]["include_auth_metadata"] = include_auth_metadata
        if include_payment_initiation_metadata:
            payload["options"]["include_payment_initiation_metadata"] = include_payment_initiation_metadata

        print(f"Fetching institutions at offset {offset}")
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if not data['institutions']:
                break
            institutions.extend(data['institutions'])
            offset += 500
            time.sleep(delay)
        else:
            print(f"Error {response.status_code}: {response.text}")
            break

    return institutions

@app.route('/')
def index():
    return send_file('static/index.html')

@app.route('/api/institutions', methods=['POST'])
def get_institutions():
    try:
        data = request.json
        
        country_codes = data.get('country_codes', [])
        selected_products = data.get('selected_products', [])
        routing_numbers = data.get('routing_numbers', [])
        oauth = data.get('oauth', False)
        include_optional_metadata = data.get('include_optional_metadata', False)
        include_auth_metadata = data.get('include_auth_metadata', False)
        include_payment_initiation_metadata = data.get('include_payment_initiation_metadata', False)

        # Fetch institutions
        institutions = fetch_institutions_with_delay(
            country_codes, routing_numbers, oauth,
            include_optional_metadata, include_auth_metadata,
            include_payment_initiation_metadata
        )

        if not institutions:
            return jsonify({'error': 'No institutions found'}), 404

        # Filter for institutions that support any of the selected products
        filtered = [
            inst for inst in institutions
            if not selected_products or any(product in inst.get("products", []) for product in selected_products)
        ]

        # Build dynamic headers
        base_headers = ['Name', 'ID', 'Country']
        optional_headers = []

        if oauth:
            optional_headers.append('OAuth')

        optional_headers.append('Products')

        # Add per-product boolean columns
        per_product_columns = [prod.capitalize() for prod in selected_products]
        optional_headers.extend(per_product_columns)

        if routing_numbers:
            optional_headers.append('Routing Numbers')
        if include_auth_metadata:
            optional_headers.extend([
                'Auth Product Support',
                'Automated Micro Deposits',
                'Instant Auth',
                'Instant Match',
                'Instant Micro Deposits'
            ])
        if include_optional_metadata:
            optional_headers.extend(['Primary Color', 'Logo', 'Logo Available', 'URL'])

        headers = base_headers + optional_headers

        # Create CSV data
        csv_data = []
        csv_data.append(headers)

        for inst in filtered:
            row = [
                inst.get('name', 'N/A'),
                inst.get('institution_id', 'N/A'),
                ", ".join(inst.get('country_codes', []))
            ]

            if oauth:
                row.append(inst.get('oauth', False))

            products_list = inst.get('products', [])
            row.append(", ".join(products_list))

            # Per-product booleans
            row.extend([product in products_list for product in selected_products])

            if routing_numbers:
                row.append(", ".join(inst.get('routing_numbers', [])))
            if include_auth_metadata:
                supported = inst.get('auth_metadata', {}).get('supported_methods', {})
                row.extend([
                    'auth' in products_list,
                    supported.get('automated_micro_deposits', False),
                    supported.get('instant_auth', False),
                    supported.get('instant_match', False),
                    supported.get('instant_micro_deposits', False),
                ])
            if include_optional_metadata:
                logo = inst.get('logo', 'N/A')
                row.extend([
                    inst.get('primary_color', 'N/A'),
                    logo,
                    bool(logo and logo != 'N/A'),
                    inst.get('url', 'N/A')
                ])

            csv_data.append(row)

        return jsonify({
            'total_institutions': len(institutions),
            'filtered_institutions': len(filtered),
            'csv_data': csv_data
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-csv', methods=['POST'])
def download_csv():
    try:
        data = request.json
        csv_data = data.get('csv_data', [])
        
        # Create CSV file in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        for row in csv_data:
            writer.writerow(row)
        
        # Convert to bytes
        csv_bytes = io.BytesIO()
        csv_bytes.write(output.getvalue().encode('utf-8'))
        csv_bytes.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"institutions_{timestamp}.csv"
        
        return send_file(
            csv_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)