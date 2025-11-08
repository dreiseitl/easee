from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
from datetime import datetime, timedelta
import os
import json
import urllib3

# Disable SSL warnings when verify=False is used
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        
        # Use lifetime-energy endpoint for hourly consumption
        url = f"{self.base_url}/chargers/lifetime-energy/{charger_id}/hourly"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "from": start_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "to": end_date.strftime("%Y-%m-%dT%H:%M:%S.999Z")
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                return True, response.json()
            else:
                error_msg = f"Status {response.status_code}: {response.text[:200]}"
                try:
                    error_json = response.json()
                    if isinstance(error_json, dict):
                        error_msg = error_json.get('message', error_json.get('error', error_msg))
                except:
                    pass
                return False, error_msg
        except Exception as e:
            return False, f"Exception: {str(e)}"

# Initialize API client
easee_api = EaseeAPI()

# Electricity price API base URL
ELECTRICITY_PRICE_API_BASE = "https://www.hvakosterstrommen.no/api/v1/prices"
CACHE_DIR = "cache/electricity_prices"

def ensure_cache_dir():
    """Ensure the cache directory exists"""
    os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_file_path(year, month, day, price_area):
    """Get the local cache file path for a specific day"""
    return os.path.join(CACHE_DIR, f"{year}_{month:02d}_{day:02d}_{price_area}.json")

def get_electricity_prices(year, month, price_area="NO1"):
    """
    Get hourly electricity prices for a given month and price area
    Uses local cache if available, otherwise downloads and caches
    Returns dict with hour -> price mapping
    """
    ensure_cache_dir()
    prices_by_hour = {}
    
    # Get number of days in the month
    if month == 12:
        num_days = 31
    elif month in [1, 3, 5, 7, 8, 10]:
        num_days = 31
    elif month in [4, 6, 9, 11]:
        num_days = 30
    else:  # February
        if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
            num_days = 29
        else:
            num_days = 28
    
    # Fetch prices for each day in the month
    for day in range(1, num_days + 1):
        cache_file = get_cache_file_path(year, month, day, price_area)
        daily_prices = None
        
        # Try to load from cache first
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    daily_prices = json.load(f)
                    print(f"Loaded prices from cache: {year}-{month:02d}-{day:02d}_{price_area}")
            except Exception as e:
                print(f"Error reading cache file {cache_file}: {str(e)}")
                # If cache read fails, continue to download
        
        # If not in cache, download from API
        if daily_prices is None:
            try:
                url = f"{ELECTRICITY_PRICE_API_BASE}/{year}/{month:02d}-{day:02d}_{price_area}.json"
                # Disable SSL verification to handle certificate issues
                # Note: This is safe for public APIs that don't require authentication
                response = requests.get(url, timeout=10, verify=False)
                
                if response.status_code == 200:
                    daily_prices = response.json()
                    # Save to cache
                    try:
                        with open(cache_file, 'w', encoding='utf-8') as f:
                            json.dump(daily_prices, f, indent=2, ensure_ascii=False)
                        print(f"Downloaded and cached prices: {year}-{month:02d}-{day:02d}_{price_area}")
                    except Exception as e:
                        print(f"Error saving cache file {cache_file}: {str(e)}")
                else:
                    print(f"Error fetching prices for {year}-{month:02d}-{day:02d}: HTTP {response.status_code}")
                    continue
            except Exception as e:
                print(f"Error fetching prices for {year}-{month:02d}-{day:02d}: {str(e)}")
                continue
        
        # Process the price data
        if daily_prices:
            for price_entry in daily_prices:
                # Parse the time_start to get the hour
                time_start = price_entry.get('time_start', '')
                if time_start:
                    try:
                        # Parse ISO 8601 format: "2022-10-17T00:00:00+02:00"
                        dt = datetime.fromisoformat(time_start.replace('Z', '+00:00'))
                        # Use as key: year-month-day-hour
                        hour_key = dt.strftime('%Y-%m-%dT%H:00:00')
                        prices_by_hour[hour_key] = price_entry.get('NOK_per_kWh', 0)
                    except (ValueError, AttributeError):
                        continue
    
    return prices_by_hour

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
    price_area = request.args.get('price_area', 'NO1')  # Default to NO1 (Oslo)
    
    if not year or not month:
        return jsonify({'error': 'Year and month are required'}), 400
    
    # Validate price area
    valid_price_areas = ['NO1', 'NO2', 'NO3', 'NO4', 'NO5']
    if price_area not in valid_price_areas:
        price_area = 'NO1'  # Default to NO1 if invalid
    
    success, result = easee_api.get_hourly_consumption(
        session['access_token'], charger_id, year, month
    )
    
    if success:
        # Fetch electricity prices for the month
        try:
            prices_by_hour = get_electricity_prices(year, month, price_area)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error fetching electricity prices: {str(e)}'}), 500
        
        # Calculate total consumption and price
        total_kwh = 0
        total_cost = 0
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
                        
                        # Try to match timestamp with price
                        price_per_kwh = 0
                        if timestamp:
                            try:
                                # Parse timestamp and create hour key
                                if isinstance(timestamp, str):
                                    # Try to parse various formats
                                    try:
                                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    except:
                                        # Try other formats
                                        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                                            try:
                                                dt = datetime.strptime(timestamp, fmt)
                                                break
                                            except:
                                                continue
                                    hour_key = dt.strftime('%Y-%m-%dT%H:00:00')
                                    price_per_kwh = prices_by_hour.get(hour_key, 0)
                            except:
                                # If parsing fails, try to find closest match
                                pass
                        
                        # Calculate cost for this hour
                        cost = kwh * price_per_kwh
                        total_cost += cost
                        
                        hourly_data.append({
                            'timestamp': timestamp,
                            'consumption': kwh,
                            'price_per_kwh': round(price_per_kwh, 4),
                            'cost': round(cost, 2)
                        })
            
            return jsonify({
                'success': True,
                'consumption': result,
                'total_kwh': round(total_kwh, 2),
                'total_cost': round(total_cost, 2),
                'price_area': price_area,
                'hourly_data': hourly_data
            })
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error processing data: {str(e)}'}), 500
    else:
        return jsonify({'success': False, 'error': result}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)

