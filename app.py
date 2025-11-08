from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Easee API base URL
EASEE_API_BASE = "https://api.easee.com/api"

class EaseeAPI:
    def __init__(self):
        self.access_token = None
        self.base_url = EASEE_API_BASE
    
    def authenticate(self, username, password):
        """Authenticate user and get access token"""
        url = f"{self.base_url}/accounts/login"
        payload = {
            "userName": username,
            "password": password
        }
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("accessToken")
                return True, self.access_token
            else:
                return False, response.text
        except Exception as e:
            return False, str(e)
    
    def get_sites(self, access_token):
        """Get all available sites for the authenticated user"""
        url = f"{self.base_url}/sites"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, response.text
        except Exception as e:
            return False, str(e)
    
    def get_chargers(self, access_token, site_id):
        """Get all chargers for a specific site"""
        url = f"{self.base_url}/sites/{site_id}/chargers"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, response.text
        except Exception as e:
            return False, str(e)
    
    def get_hourly_consumption(self, access_token, charger_id, year, month):
        """Get hourly consumption for a charger for a given month"""
        # Calculate date range for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        # Try different possible endpoint formats
        endpoints_to_try = [
            f"{self.base_url}/chargers/{charger_id}/consumption/hourly",
            f"{self.base_url}/chargers/{charger_id}/energy/hourly",
            f"{self.base_url}/chargers/{charger_id}/consumption",
        ]
        
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "from": start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "to": end_date.strftime("%Y-%m-%dT%H:%M:%S.999Z")
        }
        
        last_error = None
        for url in endpoints_to_try:
            try:
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    return True, response.json()
                elif response.status_code == 404:
                    # Try next endpoint
                    last_error = f"Endpoint not found: {url}"
                    continue
                else:
                    error_msg = f"Status {response.status_code}: {response.text[:200]}"
                    try:
                        error_json = response.json()
                        if isinstance(error_json, dict):
                            error_msg = error_json.get('message', error_json.get('error', error_msg))
                    except:
                        pass
                    last_error = error_msg
                    # If it's not a 404, return the error
                    if response.status_code != 404:
                        return False, error_msg
            except Exception as e:
                last_error = f"Exception for {url}: {str(e)}"
                continue
        
        # If all endpoints failed, return the last error
        return False, last_error or "All API endpoints failed"

# Initialize API client
easee_api = EaseeAPI()

@app.route('/')
def index():
    """Redirect to login if not authenticated"""
    if 'access_token' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('login.html', error='Please provide both username and password')
        
        success, result = easee_api.authenticate(username, password)
        
        if success:
            session['access_token'] = result
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error=f'Authentication failed: {result}')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Main dashboard"""
    if 'access_token' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/api/sites', methods=['GET'])
def api_sites():
    """API endpoint to get sites"""
    if 'access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    success, result = easee_api.get_sites(session['access_token'])
    
    if success:
        return jsonify({'success': True, 'sites': result})
    else:
        return jsonify({'success': False, 'error': result}), 400

@app.route('/api/chargers/<site_id>', methods=['GET'])
def api_chargers(site_id):
    """API endpoint to get chargers for a site"""
    if 'access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    success, result = easee_api.get_chargers(session['access_token'], site_id)
    
    if success:
        return jsonify({'success': True, 'chargers': result})
    else:
        return jsonify({'success': False, 'error': result}), 400

@app.route('/api/consumption/<charger_id>', methods=['GET'])
def api_consumption(charger_id):
    """API endpoint to get consumption for a charger"""
    if 'access_token' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    if not year or not month:
        return jsonify({'error': 'Year and month are required'}), 400
    
    success, result = easee_api.get_hourly_consumption(
        session['access_token'], charger_id, year, month
    )
    
    if success:
        # Calculate total consumption and price
        total_kwh = 0
        hourly_data = []
        
        try:
            # Handle different response formats
            if result is None:
                return jsonify({'success': False, 'error': 'No data returned from API'}), 400
            
            # If result is a dict, try to extract the list
            if isinstance(result, dict):
                # Try common keys that might contain the data
                data_list = result.get('data') or result.get('consumption') or result.get('hourly') or []
                if isinstance(data_list, list):
                    result = data_list
                else:
                    # If it's a single entry dict, wrap it in a list
                    result = [result]
            
            if isinstance(result, list):
                for entry in result:
                    if not isinstance(entry, dict):
                        continue
                    
                    # Handle different possible field names and units
                    consumption = entry.get('consumption') or entry.get('energy') or entry.get('kwh') or entry.get('wh') or 0
                    
                    # Convert to float if it's a string
                    try:
                        consumption = float(consumption)
                    except (ValueError, TypeError):
                        consumption = 0
                    
                    # If consumption is in Wh (watt-hours), convert to kWh
                    # Easee API typically returns in Wh
                    if consumption > 0:
                        if consumption > 100:  # Likely in Wh (values > 100 Wh)
                            kwh = consumption / 1000.0
                        else:
                            kwh = consumption  # Already in kWh
                        
                        total_kwh += kwh
                        timestamp = entry.get('timestamp') or entry.get('date') or entry.get('time') or entry.get('dateTime')
                        hourly_data.append({
                            'timestamp': timestamp,
                            'consumption': kwh
                        })
            
            total_price = total_kwh * 1.0  # 1 kWh = 1 NOK
            
            return jsonify({
                'success': True,
                'consumption': result,
                'total_kwh': round(total_kwh, 2),
                'total_price': round(total_price, 2),
                'hourly_data': hourly_data
            })
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error processing data: {str(e)}'}), 500
    else:
        return jsonify({'success': False, 'error': result}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)

