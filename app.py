import os
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
import json
import base64
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database - using PostgreSQL
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import the models here
    from models import APIConfiguration, OSINTCase, DataPoint, APIResult
    db.create_all()

# Import services after app and db initialization
from openai_service import process_input_with_llm, analyze_data_with_llm, generate_report_with_llm, ai_provider
from api_service import query_apis, query_rapidapi, get_all_apis, add_api_config, get_api_config, update_api_config, delete_api_config
from web_scraper import get_website_text_content

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api_config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        try:
            api_name = request.form.get('api_name')
            api_url = request.form.get('api_url')
            api_key_env = request.form.get('api_key_env')
            description = request.form.get('description')
            endpoints = request.form.get('endpoints')
            format_details = request.form.get('format')
            
            # Add new API configuration
            add_api_config(api_name, api_url, api_key_env, description, endpoints, format_details)
            flash('API configuration added successfully', 'success')
            return redirect(url_for('api_config'))
        except Exception as e:
            logger.error(f"Error adding API configuration: {str(e)}")
            flash(f'Error adding API configuration: {str(e)}', 'danger')
    
    # Get all API configurations
    apis = get_all_apis()
    return render_template('api_config.html', apis=apis)

@app.route('/api_config/<int:api_id>', methods=['PUT', 'DELETE'])
def manage_api_config(api_id):
    if request.method == 'PUT':
        try:
            data = request.json
            update_api_config(
                api_id,
                data.get('api_name'),
                data.get('api_url'),
                data.get('api_key_env'),
                data.get('description'),
                data.get('endpoints'),
                data.get('format')
            )
            return jsonify({"status": "success", "message": "API configuration updated"})
        except Exception as e:
            logger.error(f"Error updating API configuration: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            delete_api_config(api_id)
            return jsonify({"status": "success", "message": "API configuration deleted"})
        except Exception as e:
            logger.error(f"Error deleting API configuration: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/submit_osint', methods=['POST'])
def submit_osint():
    try:
        # Get form data
        name = request.form.get('name', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        social_media = request.form.get('social_media', '')
        location = request.form.get('location', '')
        vehicle = request.form.get('vehicle', '')
        additional_info = request.form.get('additional_info', '')
        
        # Ensure at least one field is filled
        if not any([name, phone, email, social_media, location, vehicle, additional_info, 
                   'image' in request.files and request.files['image'].filename]):
            flash("Please provide at least one piece of information to begin the investigation.", "warning")
            return redirect(url_for('index'))
        
        # Handle image if provided
        image_data = None
        if 'image' in request.files and request.files['image'].filename:
            image_file = request.files['image']
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create a new OSINT case
        with app.app_context():
            case = OSINTCase(
                name=name or "Unnamed Case",  # Default name if none provided
                created_at=datetime.now()
            )
            db.session.add(case)
            db.session.flush()  # Get the case ID without committing
            
            # Add initial data points
            data_points = []
            if name:
                data_points.append(DataPoint(case_id=case.id, data_type='name', value=name))
            if phone:
                data_points.append(DataPoint(case_id=case.id, data_type='phone', value=phone))
            if email:
                data_points.append(DataPoint(case_id=case.id, data_type='email', value=email))
            if social_media:
                data_points.append(DataPoint(case_id=case.id, data_type='social_media', value=social_media))
            if location:
                data_points.append(DataPoint(case_id=case.id, data_type='location', value=location))
            if vehicle:
                data_points.append(DataPoint(case_id=case.id, data_type='vehicle', value=vehicle))
            if additional_info:
                data_points.append(DataPoint(case_id=case.id, data_type='additional_info', value=additional_info))
            if image_data:
                data_points.append(DataPoint(case_id=case.id, data_type='image', value=image_data))
            
            db.session.add_all(data_points)
            db.session.commit()
        
        # Process input with LLM to determine which APIs to query
        input_data = {
            'name': name,
            'phone': phone,
            'email': email,
            'social_media': social_media,
            'location': location,
            'vehicle': vehicle,
            'additional_info': additional_info,
            'has_image': image_data is not None
        }
        
        # Get LLM analysis of the input data
        llm_analysis = process_input_with_llm(input_data)
        logger.debug(f"LLM Analysis: {llm_analysis}")
        
        # Get all available APIs
        all_apis = get_all_apis()
        
        # Query selected APIs based on LLM analysis
        api_results = query_apis(case.id, llm_analysis, all_apis)
        
        # Query RapidAPI for additional data
        logger.debug("Querying RapidAPI for additional data...")
        rapidapi_results = query_rapidapi(case.id, llm_analysis, all_apis, input_data)
        
        # Combine all API results
        combined_api_results = api_results + rapidapi_results
        
        # Analyze gathered data with LLM
        data_analysis = analyze_data_with_llm(combined_api_results, input_data)
        
        # Generate report
        report = generate_report_with_llm(data_analysis, combined_api_results, input_data)
        
        # Store session data for report viewing
        session['case_id'] = case.id
        session['report'] = report
        session['api_results'] = combined_api_results
        
        return redirect(url_for('report'))
    
    except Exception as e:
        logger.error(f"Error processing OSINT request: {str(e)}")
        flash(f"Error processing request: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/report')
def report():
    case_id = session.get('case_id')
    report_data = session.get('report')
    api_results = session.get('api_results')
    
    if not case_id or not report_data:
        flash("No report data available. Please submit a new OSINT request.", "warning")
        return redirect(url_for('index'))
    
    return render_template('report.html', 
                           report=report_data, 
                           api_results=api_results,
                           case_id=case_id)

@app.route('/scrape_url', methods=['POST'])
def scrape_url():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({"status": "error", "message": "URL is required"}), 400
        
        content = get_website_text_content(url)
        return jsonify({"status": "success", "content": content})
    
    except Exception as e:
        logger.error(f"Error scraping URL: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', error="Page not found"), 404

@app.route('/ai_model_config', methods=['GET', 'POST'])
def ai_model_config():
    # Check for API keys
    has_openai_key = os.environ.get("OPENAI_API_KEY") is not None
    has_openrouter_key = os.environ.get("OPENROUTER_API_KEY") is not None
    
    if request.method == 'POST':
        try:
            model_id = request.form.get('model_id')
            if model_id:
                ai_provider.set_model(model_id)
                flash('AI model updated successfully', 'success')
            else:
                flash('Please select a valid model', 'warning')
            return redirect(url_for('ai_model_config'))
        except Exception as e:
            logger.error(f"Error updating AI model: {str(e)}")
            flash(f"Error updating AI model: {str(e)}", 'danger')
    
    # Get available models and current settings
    available_models = ai_provider.get_available_models()
    current_provider = ai_provider.provider
    current_model = ai_provider.model
    
    return render_template('ai_model_config.html',
                           available_models=available_models,
                           current_provider=current_provider,
                           current_model=current_model,
                           has_openai_key=has_openai_key,
                           has_openrouter_key=has_openrouter_key)

@app.route('/api/refresh-models', methods=['POST'])
def refresh_models():
    try:
        ai_provider.refresh_model_list()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error refreshing models: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/save_api_key', methods=['POST'])
def save_api_key():
    try:
        data = request.json
        key_name = data.get('key_name')
        key_value = data.get('key_value')
        
        if not key_name or not key_value:
            return jsonify({"success": False, "error": "Key name and value are required"}), 400
        
        # In a production environment, you would securely store these in environment variables
        # For Replit, we're using the environment variable system
        os.environ[key_name] = key_value
        logger.info(f"API key '{key_name}' saved successfully")
        
        return jsonify({"success": True, "message": f"API key '{key_name}' saved successfully"})
    except Exception as e:
        logger.error(f"Error saving API key: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/populate_api_directory', methods=['POST'])
def populate_api_directory():
    """Route to populate the API directory from public sources"""
    try:
        # Import the script functions
        from populate_api_directory import fetch_apis_guru, fetch_public_apis, add_api_config_if_not_exists
        
        # Determine which source to use
        source = request.form.get('source', 'all')
        apis_count = 0
        
        if source in ['all', 'apis_guru']:
            # Fetch and add APIs from APIs.guru
            apis_guru_apis = fetch_apis_guru()
            apis_guru_count = 0
            for api_data in apis_guru_apis:
                if add_api_config_if_not_exists(api_data):
                    apis_guru_count += 1
            logger.info(f"Added {apis_guru_count} APIs from APIs.guru to database")
            apis_count += apis_guru_count
        
        if source in ['all', 'public_apis']:
            # Fetch and add APIs from Public APIs
            public_apis = fetch_public_apis()
            public_apis_count = 0
            for api_data in public_apis:
                if add_api_config_if_not_exists(api_data):
                    public_apis_count += 1
            logger.info(f"Added {public_apis_count} APIs from Public APIs to database")
            apis_count += public_apis_count
        
        flash(f"Successfully added {apis_count} new APIs to the directory", "success")
        return redirect(url_for('api_config'))
    
    except Exception as e:
        logger.error(f"Error populating API directory: {str(e)}")
        flash(f"Error populating API directory: {str(e)}", "danger")
        return redirect(url_for('api_config'))

@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error="Server error occurred. Please try again."), 500
