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

# Configure the database - using SQLite for simplicity
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///osint.db"
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
from api_service import query_apis, get_all_apis, add_api_config, get_api_config, update_api_config, delete_api_config
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
        
        # Handle image if provided
        image_data = None
        if 'image' in request.files and request.files['image'].filename:
            image_file = request.files['image']
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create a new OSINT case
        with app.app_context():
            case = OSINTCase(
                name=name,
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
        
        # Analyze gathered data with LLM
        data_analysis = analyze_data_with_llm(api_results, input_data)
        
        # Generate report
        report = generate_report_with_llm(data_analysis, api_results, input_data)
        
        # Store session data for report viewing
        session['case_id'] = case.id
        session['report'] = report
        session['api_results'] = api_results
        
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

@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error="Server error occurred. Please try again."), 500
