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
    from models import (
        APIConfiguration, OSINTCase, DataPoint, APIResult,
        WorkflowDefinition, WorkflowExecution, WorkflowStep
    )
    db.create_all()

# Import services after app and db initialization
from openai_service import process_input_with_llm, analyze_data_with_llm, generate_report_with_llm, ai_provider
from api_service import query_apis, query_rapidapi, get_all_apis, add_api_config, get_api_config, update_api_config, delete_api_config
from web_scraper import get_website_text_content
import workflow_engine

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

@app.route('/help')
def help_page():
    """Route to display help and documentation page"""
    return render_template('help.html')

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

@app.route('/populate_osint_apis', methods=['GET'])
def populate_osint_apis():
    """Route to populate the database with categorized OSINT APIs"""
    try:
        # Import the OSINT API list
        from osint_apis import OSINT_APIS
        
        # Function to add an API if it doesn't exist
        def add_api_config_if_not_exists(api_data):
            existing_api = APIConfiguration.query.filter_by(api_name=api_data["api_name"]).first()
            if existing_api:
                logger.info(f"API '{api_data['api_name']}' already exists.")
                return False
            else:
                # Add the API to the database
                api_config = APIConfiguration(
                    api_name=api_data["api_name"],
                    api_url=api_data["api_url"],
                    api_key_env=api_data["api_key_env"],
                    description=api_data["description"],
                    endpoints=api_data["endpoints"],
                    format=api_data["format"]
                )
                db.session.add(api_config)
                db.session.commit()
                logger.info(f"Added API '{api_data['api_name']}' to database.")
                return True
        
        # Add OSINT APIs to database
        apis_count = 0
        for api_data in OSINT_APIS:
            if add_api_config_if_not_exists(api_data):
                apis_count += 1
        
        # Show success message
        if apis_count > 0:
            flash(f"Successfully added {apis_count} OSINT APIs to the directory.", "success")
        else:
            flash("No new OSINT APIs were added to the directory.", "info")
        
        return redirect(url_for('api_config'))
    except Exception as e:
        logger.error(f"Error populating OSINT APIs: {str(e)}")
        flash(f"Error populating OSINT APIs: {str(e)}", "danger")
        return redirect(url_for('api_config'))

@app.route('/workflows', methods=['GET', 'POST'])
def workflows():
    """Route to manage intelligence gathering workflows"""
    if request.method == 'POST':
        try:
            # Add new workflow
            name = request.form.get('name')
            description = request.form.get('description')
            steps = request.form.get('steps')
            
            # Schedule configuration
            schedule_enabled = request.form.get('schedule_enabled') == 'on'
            if schedule_enabled:
                frequency = request.form.get('frequency')
                interval = int(request.form.get('interval', 1))
                schedule = {'frequency': frequency, 'interval': interval}
            else:
                schedule = None
            
            # Trigger configuration
            trigger_type = request.form.get('trigger_type')
            trigger_config = None
            
            if trigger_type == 'event':
                event_type = request.form.get('event_type')
                data_type = request.form.get('data_type')
                trigger_config = {'event_type': event_type, 'data_type': data_type}
            
            # Validate steps
            if not steps:
                flash("Workflow steps are required", "danger")
                return redirect(url_for('workflows'))
            
            try:
                steps_data = json.loads(steps)
            except json.JSONDecodeError:
                flash("Invalid workflow steps JSON", "danger")
                return redirect(url_for('workflows'))
            
            # Create the workflow
            workflow_engine.create_workflow(
                name=name,
                description=description,
                steps=steps_data,
                schedule=schedule,
                trigger_type=trigger_type,
                trigger_config=trigger_config
            )
            
            flash("Workflow created successfully", "success")
            return redirect(url_for('workflows'))
            
        except Exception as e:
            logger.error(f"Error creating workflow: {str(e)}")
            flash(f"Error creating workflow: {str(e)}", "danger")
    
    # Get all workflows
    workflows = WorkflowDefinition.query.all()
    
    # Get workflow execution history
    executions = WorkflowExecution.query.order_by(WorkflowExecution.start_time.desc()).limit(20).all()
    
    return render_template('workflows.html', 
                          workflows=workflows,
                          executions=executions)

@app.route('/workflows/<int:workflow_id>/execute', methods=['POST'])
def execute_workflow(workflow_id):
    """Route to manually execute a workflow"""
    try:
        # Get context data from request
        context = request.json or {}
        
        # Execute the workflow
        result = workflow_engine.execute_workflow(workflow_id, context)
        
        if result:
            return jsonify({"status": "success", "message": "Workflow execution started"})
        else:
            return jsonify({"status": "error", "message": "Failed to start workflow execution"}), 500
            
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/workflows/<int:workflow_id>', methods=['PUT', 'DELETE'])
def manage_workflow(workflow_id):
    """Route to manage a workflow"""
    if request.method == 'PUT':
        try:
            # Update workflow
            data = request.json
            workflow = WorkflowDefinition.query.get(workflow_id)
            
            if not workflow:
                return jsonify({"status": "error", "message": "Workflow not found"}), 404
            
            # Update fields
            if 'name' in data:
                workflow.name = data['name']
            if 'description' in data:
                workflow.description = data['description']
            if 'steps' in data:
                workflow.steps = json.dumps(data['steps'])
            if 'schedule' in data:
                workflow.schedule = json.dumps(data['schedule']) if data['schedule'] else None
            if 'trigger_type' in data:
                workflow.trigger_type = data['trigger_type']
            if 'trigger_config' in data:
                workflow.trigger_config = json.dumps(data['trigger_config']) if data['trigger_config'] else None
            if 'is_active' in data:
                workflow.is_active = data['is_active']
            
            workflow.updated_at = datetime.now()
            db.session.commit()
            
            return jsonify({"status": "success", "message": "Workflow updated successfully"})
            
        except Exception as e:
            logger.error(f"Error updating workflow: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            # Delete workflow
            workflow = WorkflowDefinition.query.get(workflow_id)
            
            if not workflow:
                return jsonify({"status": "error", "message": "Workflow not found"}), 404
            
            db.session.delete(workflow)
            db.session.commit()
            
            return jsonify({"status": "success", "message": "Workflow deleted successfully"})
            
        except Exception as e:
            logger.error(f"Error deleting workflow: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/workflow_executions/<int:execution_id>', methods=['GET'])
def workflow_execution_details(execution_id):
    """Route to get workflow execution details"""
    try:
        execution = WorkflowExecution.query.get(execution_id)
        
        if not execution:
            return jsonify({"status": "error", "message": "Execution not found"}), 404
        
        # Get workflow details
        workflow = WorkflowDefinition.query.get(execution.workflow_id)
        
        # Get execution steps
        steps = WorkflowStep.query.filter_by(execution_id=execution_id).order_by(WorkflowStep.step_number).all()
        
        return jsonify({
            "status": "success",
            "execution": execution.to_dict(),
            "workflow": workflow.to_dict() if workflow else None,
            "steps": [step.to_dict() for step in steps]
        })
        
    except Exception as e:
        logger.error(f"Error getting execution details: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/start_workflow_engine', methods=['POST'])
def start_workflow_engine_route():
    """Route to start the workflow engine"""
    try:
        workflow_engine.start_workflow_engine()
        return jsonify({"status": "success", "message": "Workflow engine started"})
    except Exception as e:
        logger.error(f"Error starting workflow engine: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/stop_workflow_engine', methods=['POST'])
def stop_workflow_engine_route():
    """Route to stop the workflow engine"""
    try:
        workflow_engine.stop_workflow_engine()
        return jsonify({"status": "success", "message": "Workflow engine stopped"})
    except Exception as e:
        logger.error(f"Error stopping workflow engine: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error="Server error occurred. Please try again."), 500

# Initialize the workflow engine when the app starts
# We'll initialize the workflow engine on first request to ensure all dependencies are loaded
@app.route('/initialize_workflow_engine', methods=['POST'])
def initialize_workflow_engine():
    """Initialize the workflow engine on demand"""
    try:
        workflow_engine.start_workflow_engine()
        logger.info("Workflow engine started")
        return jsonify({"status": "success", "message": "Workflow engine initialized"})
    except Exception as e:
        logger.error(f"Error starting workflow engine: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
