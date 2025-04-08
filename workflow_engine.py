"""
Workflow Engine for Automated OSINT Intelligence Gathering

This module provides a workflow engine that manages automated intelligence 
gathering workflows, allowing for scheduled and event-driven data collection
and analysis without manual intervention.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from threading import Thread, Event
import traceback

from models import OSINTCase, DataPoint, APIResult, db, WorkflowDefinition, WorkflowExecution, WorkflowStep
import api_service
import openai_service
from web_scraper import get_website_text_content

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variable to keep track of running workflow threads
_running_workflows = {}
_stop_event = Event()

class WorkflowEngine:
    """Main workflow engine class that manages OSINT workflows"""
    
    def __init__(self):
        """Initialize the workflow engine"""
        self.workflows = {}
        self.running = False
    
    def start(self):
        """Start the workflow engine"""
        if self.running:
            logger.warning("Workflow engine is already running")
            return
        
        self.running = True
        logger.info("Starting workflow engine")
        
        # Start a thread to periodically check for scheduled workflows
        Thread(target=self._scheduler_thread, daemon=True).start()
    
    def stop(self):
        """Stop the workflow engine and all running workflows"""
        if not self.running:
            logger.warning("Workflow engine is not running")
            return
        
        self.running = False
        _stop_event.set()
        logger.info("Stopping workflow engine")
        
        # Stop all running workflows
        for workflow_id, thread in list(_running_workflows.items()):
            logger.info(f"Stopping workflow {workflow_id}")
            thread.join(timeout=5.0)  # Give each workflow up to 5 seconds to clean up
    
    def _scheduler_thread(self):
        """Thread that periodically checks for scheduled workflows"""
        while self.running and not _stop_event.is_set():
            try:
                # Check for workflows that are due to run
                self._check_scheduled_workflows()
                
                # Check for new data that should trigger workflows
                self._check_event_triggers()
                
                # Sleep for a bit before checking again
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler thread: {str(e)}")
                logger.error(traceback.format_exc())
    
    def _check_scheduled_workflows(self):
        """Check for scheduled workflows that need to be executed"""
        try:
            # Query database for workflow definitions with schedules
            with db.session.no_autoflush:
                now = datetime.now()
                workflows = WorkflowDefinition.query.filter(
                    WorkflowDefinition.is_active == True,
                    WorkflowDefinition.schedule != None,
                    WorkflowDefinition.schedule != ""
                ).all()
                
                for workflow in workflows:
                    # Check if workflow is due to run
                    if self._is_workflow_due(workflow, now):
                        # Start workflow execution
                        self.execute_workflow(workflow.id)
        except Exception as e:
            logger.error(f"Error checking scheduled workflows: {str(e)}")
    
    def _is_workflow_due(self, workflow, current_time):
        """Check if a workflow is due to run based on its schedule"""
        try:
            schedule = json.loads(workflow.schedule)
            
            # Get the last execution time
            last_execution = WorkflowExecution.query.filter_by(
                workflow_id=workflow.id
            ).order_by(WorkflowExecution.start_time.desc()).first()
            
            if not last_execution:
                # Never run before, so it's due
                return True
            
            last_run = last_execution.start_time
            
            # Calculate next run time based on frequency
            frequency = schedule.get('frequency', 'daily')
            interval = schedule.get('interval', 1)
            
            if frequency == 'minutes':
                next_run = last_run + timedelta(minutes=interval)
            elif frequency == 'hourly':
                next_run = last_run + timedelta(hours=interval)
            elif frequency == 'daily':
                next_run = last_run + timedelta(days=interval)
            elif frequency == 'weekly':
                next_run = last_run + timedelta(weeks=interval)
            elif frequency == 'monthly':
                # Approximate a month as 30 days
                next_run = last_run + timedelta(days=30*interval)
            else:
                logger.warning(f"Unknown frequency: {frequency}, defaulting to daily")
                next_run = last_run + timedelta(days=interval)
            
            # Check if it's time to run again
            return current_time >= next_run
        except Exception as e:
            logger.error(f"Error determining if workflow is due: {str(e)}")
            return False
    
    def _check_event_triggers(self):
        """Check for new data that should trigger event-based workflows"""
        try:
            # Query database for workflow definitions with event triggers
            with db.session.no_autoflush:
                workflows = WorkflowDefinition.query.filter(
                    WorkflowDefinition.is_active == True,
                    WorkflowDefinition.trigger_type == 'event'
                ).all()
                
                # For each event-triggered workflow
                for workflow in workflows:
                    trigger_config = json.loads(workflow.trigger_config or '{}')
                    
                    # Check for data matching the trigger criteria
                    if trigger_config.get('data_type') == 'new_case':
                        # Look for cases created since last check
                        last_check = self._get_last_trigger_check(workflow.id)
                        
                        new_cases = OSINTCase.query.filter(
                            OSINTCase.created_at > last_check
                        ).all()
                        
                        for case in new_cases:
                            # Execute workflow for this case
                            self.execute_workflow(
                                workflow.id, 
                                context={'case_id': case.id}
                            )
                    
                    elif trigger_config.get('data_type') == 'new_datapoint':
                        # Look for data points added since last check
                        last_check = self._get_last_trigger_check(workflow.id)
                        
                        data_type = trigger_config.get('specific_type')
                        if data_type:
                            new_datapoints = DataPoint.query.filter(
                                DataPoint.created_at > last_check,
                                DataPoint.data_type == data_type
                            ).all()
                        else:
                            new_datapoints = DataPoint.query.filter(
                                DataPoint.created_at > last_check
                            ).all()
                        
                        for datapoint in new_datapoints:
                            # Execute workflow for this datapoint
                            self.execute_workflow(
                                workflow.id, 
                                context={
                                    'case_id': datapoint.case_id,
                                    'datapoint_id': datapoint.id
                                }
                            )
                    
                    # Update the last check time
                    self._update_trigger_check_time(workflow.id)
        except Exception as e:
            logger.error(f"Error checking event triggers: {str(e)}")
    
    def _get_last_trigger_check(self, workflow_id):
        """Get the last time a trigger was checked for a workflow"""
        # Check in workflow metadata or use a reasonable default (1 hour ago)
        return datetime.now() - timedelta(hours=1)
    
    def _update_trigger_check_time(self, workflow_id):
        """Update the last check time for a workflow trigger"""
        # Store in workflow metadata
        pass
    
    def execute_workflow(self, workflow_id, context=None):
        """
        Execute a workflow
        
        Args:
            workflow_id (int): ID of the workflow to execute
            context (dict, optional): Context data for the workflow
        """
        # Start workflow in a separate thread
        thread = Thread(
            target=self._workflow_thread,
            args=(workflow_id, context or {}),
            daemon=True
        )
        thread.start()
        
        # Keep track of the thread
        _running_workflows[workflow_id] = thread
        
        return True
    
    def _workflow_thread(self, workflow_id, context):
        """Thread that executes a workflow"""
        try:
            # Create workflow execution record
            execution = WorkflowExecution(
                workflow_id=workflow_id,
                start_time=datetime.now(),
                status='running',
                context=json.dumps(context)
            )
            db.session.add(execution)
            db.session.commit()
            
            # Get workflow definition
            workflow = WorkflowDefinition.query.get(workflow_id)
            if not workflow:
                logger.error(f"Workflow {workflow_id} not found")
                return
            
            # Parse workflow steps
            steps = json.loads(workflow.steps or '[]')
            
            # Execute each step
            for i, step in enumerate(steps):
                # Create step execution record
                step_execution = WorkflowStep(
                    execution_id=execution.id,
                    step_number=i+1,
                    step_type=step.get('type'),
                    status='running',
                    start_time=datetime.now()
                )
                db.session.add(step_execution)
                db.session.commit()
                
                try:
                    # Execute the step
                    result = self._execute_step(step, context)
                    
                    # If the step produces output, add it to the context
                    if result:
                        context.update(result)
                    
                    # Update step execution record
                    step_execution.status = 'completed'
                    step_execution.end_time = datetime.now()
                    step_execution.result = json.dumps(result) if result else None
                    db.session.commit()
                    
                except Exception as e:
                    logger.error(f"Error executing workflow step: {str(e)}")
                    logger.error(traceback.format_exc())
                    
                    # Update step execution record
                    step_execution.status = 'failed'
                    step_execution.end_time = datetime.now()
                    step_execution.error = str(e)
                    db.session.commit()
                    
                    # Update execution record and exit
                    execution.status = 'failed'
                    execution.end_time = datetime.now()
                    execution.error = str(e)
                    db.session.commit()
                    return
            
            # All steps completed successfully
            execution.status = 'completed'
            execution.end_time = datetime.now()
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Update execution record
            try:
                execution.status = 'failed'
                execution.end_time = datetime.now()
                execution.error = str(e)
                db.session.commit()
            except:
                pass
        finally:
            # Remove from running workflows
            if workflow_id in _running_workflows:
                del _running_workflows[workflow_id]
    
    def _execute_step(self, step, context):
        """
        Execute a workflow step
        
        Args:
            step (dict): Step definition
            context (dict): Workflow context
        
        Returns:
            dict: Result of the step execution
        """
        step_type = step.get('type')
        
        if step_type == 'api_query':
            return self._execute_api_query_step(step, context)
        
        elif step_type == 'llm_analysis':
            return self._execute_llm_analysis_step(step, context)
        
        elif step_type == 'web_scrape':
            return self._execute_web_scrape_step(step, context)
        
        elif step_type == 'data_store':
            return self._execute_data_store_step(step, context)
        
        elif step_type == 'condition':
            return self._execute_condition_step(step, context)
        
        else:
            raise ValueError(f"Unknown step type: {step_type}")
    
    def _execute_api_query_step(self, step, context):
        """Execute an API query step"""
        case_id = context.get('case_id')
        if not case_id:
            raise ValueError("Case ID is required for API query step")
        
        # Get the input data for the case
        case = OSINTCase.query.get(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        # Build input data from data points
        input_data = {}
        for data_point in case.data_points:
            if data_point.data_type == 'name':
                input_data['name'] = data_point.value
            elif data_point.data_type == 'phone':
                input_data['phone'] = data_point.value
            elif data_point.data_type == 'email':
                input_data['email'] = data_point.value
            elif data_point.data_type == 'social_media':
                input_data['social_media'] = data_point.value
            elif data_point.data_type == 'location':
                input_data['location'] = data_point.value
            elif data_point.data_type == 'vehicle':
                input_data['vehicle'] = data_point.value
            elif data_point.data_type == 'additional_info':
                input_data['additional_info'] = data_point.value
            elif data_point.data_type == 'image':
                input_data['has_image'] = True
            elif data_point.data_type == 'secondary_image':
                input_data['has_secondary_image'] = True
        
        # Check for specific API selection in step config
        api_selection = step.get('api_selection')
        
        if api_selection == 'auto':
            # Let the LLM decide which APIs to query
            llm_analysis = openai_service.process_input_with_llm(input_data)
            available_apis = api_service.get_all_apis()
            
            # Query the APIs
            api_results = api_service.query_apis(case_id, llm_analysis, available_apis)
            
            # Also check RapidAPI
            rapid_results = api_service.query_rapidapi(case_id, llm_analysis, available_apis, input_data)
            
            # Combine results
            api_results.extend(rapid_results)
            
        else:
            # Query specific APIs based on step configuration
            api_ids = step.get('api_ids', [])
            
            if not api_ids:
                raise ValueError("No APIs specified for query")
            
            # Create a minimal LLM analysis with specific APIs
            llm_analysis = {
                "recommended_api_types": step.get('api_types', []),
                "recommended_api_categories": step.get('api_categories', []),
                "query_parameters": {}
            }
            
            # Add query parameters from context or step config
            for data_type, value in input_data.items():
                if value:
                    llm_analysis["query_parameters"][data_type] = [value]
            
            # Override with step-specific parameters if provided
            if step.get('parameters'):
                llm_analysis["query_parameters"].update(step.get('parameters'))
            
            # Get the specified APIs
            available_apis = []
            for api_id in api_ids:
                api = api_service.get_api_config(api_id)
                if api:
                    available_apis.append(api)
            
            # Query the APIs
            api_results = api_service.query_apis(case_id, llm_analysis, available_apis)
        
        return {
            'api_results': api_results
        }
    
    def _execute_llm_analysis_step(self, step, context):
        """Execute an LLM analysis step"""
        analysis_type = step.get('analysis_type')
        
        if analysis_type == 'process_input':
            # Process input data to determine API selection
            input_data = context.get('input_data') or {}
            
            # If no input data in context, try to build from case
            if not input_data and context.get('case_id'):
                case_id = context.get('case_id')
                case = OSINTCase.query.get(case_id)
                
                if case:
                    input_data = {}
                    for data_point in case.data_points:
                        if data_point.data_type == 'name':
                            input_data['name'] = data_point.value
                        elif data_point.data_type == 'phone':
                            input_data['phone'] = data_point.value
                        elif data_point.data_type == 'email':
                            input_data['email'] = data_point.value
                        elif data_point.data_type == 'social_media':
                            input_data['social_media'] = data_point.value
                        elif data_point.data_type == 'location':
                            input_data['location'] = data_point.value
                        elif data_point.data_type == 'vehicle':
                            input_data['vehicle'] = data_point.value
                        elif data_point.data_type == 'additional_info':
                            input_data['additional_info'] = data_point.value
                        elif data_point.data_type == 'image':
                            input_data['has_image'] = True
                        elif data_point.data_type == 'secondary_image':
                            input_data['has_secondary_image'] = True
            
            llm_analysis = openai_service.process_input_with_llm(input_data)
            return {
                'llm_analysis': llm_analysis
            }
        
        elif analysis_type == 'analyze_results':
            # Analyze API results
            api_results = context.get('api_results') or []
            input_data = context.get('input_data') or {}
            
            # If no input data in context, try to build from case
            if not input_data and context.get('case_id'):
                case_id = context.get('case_id')
                case = OSINTCase.query.get(case_id)
                
                if case:
                    input_data = {}
                    for data_point in case.data_points:
                        if data_point.data_type == 'name':
                            input_data['name'] = data_point.value
                        elif data_point.data_type == 'phone':
                            input_data['phone'] = data_point.value
                        elif data_point.data_type == 'email':
                            input_data['email'] = data_point.value
                        elif data_point.data_type == 'social_media':
                            input_data['social_media'] = data_point.value
                        elif data_point.data_type == 'location':
                            input_data['location'] = data_point.value
                        elif data_point.data_type == 'vehicle':
                            input_data['vehicle'] = data_point.value
                        elif data_point.data_type == 'additional_info':
                            input_data['additional_info'] = data_point.value
                        elif data_point.data_type == 'image':
                            input_data['has_image'] = True
                        elif data_point.data_type == 'secondary_image':
                            input_data['has_secondary_image'] = True
            
            analysis = openai_service.analyze_data_with_llm(api_results, input_data)
            return {
                'data_analysis': analysis
            }
        
        elif analysis_type == 'generate_report':
            # Generate report from analysis and results
            data_analysis = context.get('data_analysis') or {}
            api_results = context.get('api_results') or []
            input_data = context.get('input_data') or {}
            
            # If no input data in context, try to build from case
            if not input_data and context.get('case_id'):
                case_id = context.get('case_id')
                case = OSINTCase.query.get(case_id)
                
                if case:
                    input_data = {}
                    for data_point in case.data_points:
                        if data_point.data_type == 'name':
                            input_data['name'] = data_point.value
                        elif data_point.data_type == 'phone':
                            input_data['phone'] = data_point.value
                        elif data_point.data_type == 'email':
                            input_data['email'] = data_point.value
                        elif data_point.data_type == 'social_media':
                            input_data['social_media'] = data_point.value
                        elif data_point.data_type == 'location':
                            input_data['location'] = data_point.value
                        elif data_point.data_type == 'vehicle':
                            input_data['vehicle'] = data_point.value
                        elif data_point.data_type == 'additional_info':
                            input_data['additional_info'] = data_point.value
                        elif data_point.data_type == 'image':
                            input_data['has_image'] = True
                        elif data_point.data_type == 'secondary_image':
                            input_data['has_secondary_image'] = True
            
            report = openai_service.generate_report_with_llm(data_analysis, api_results, input_data)
            return {
                'report': report
            }
            
        elif analysis_type == 'analyze_image':
            # Analyze image
            case_id = context.get('case_id')
            if not case_id:
                raise ValueError("Case ID is required for image analysis")
                
            # Look for image data points
            image_data = None
            image_type = step.get('image_type', 'primary')
            
            if image_type == 'primary':
                image_point = DataPoint.query.filter_by(case_id=case_id, data_type='image').first()
            else:
                image_point = DataPoint.query.filter_by(case_id=case_id, data_type='secondary_image').first()
                
            if image_point:
                image_data = image_point.value
                
            if not image_data:
                raise ValueError(f"No {image_type} image found for case {case_id}")
                
            # Analyze the image
            analysis = openai_service.analyze_image(image_data, image_type)
            
            return {
                'image_analysis': analysis
            }
        
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")
    
    def _execute_web_scrape_step(self, step, context):
        """Execute a web scraping step"""
        url = step.get('url')
        
        # Check if URL should be taken from context
        if url.startswith('$'):
            context_key = url[1:]
            url = context.get(context_key)
            
            if not url:
                raise ValueError(f"URL not found in context: {context_key}")
        
        # Scrape the website
        content = get_website_text_content(url)
        
        # Store result in specified context key
        result_key = step.get('result_key', 'scraped_content')
        
        return {
            result_key: content
        }
    
    def _execute_data_store_step(self, step, context):
        """Execute a data storage step"""
        store_type = step.get('store_type')
        
        if store_type == 'datapoint':
            # Store a new data point
            case_id = context.get('case_id')
            if not case_id:
                raise ValueError("Case ID is required for storing data points")
                
            data_type = step.get('data_type')
            if not data_type:
                raise ValueError("Data type is required for storing data points")
                
            # Get value from context or step configuration
            value_source = step.get('value_source')
            if value_source.startswith('$'):
                context_key = value_source[1:]
                value = context.get(context_key)
                
                if value is None:
                    raise ValueError(f"Value not found in context: {context_key}")
            else:
                value = step.get('value')
            
            # Create data point
            data_point = DataPoint(
                case_id=case_id,
                data_type=data_type,
                value=value,
                created_at=datetime.now()
            )
            db.session.add(data_point)
            db.session.commit()
            
            return {
                'datapoint_id': data_point.id
            }
        
        else:
            raise ValueError(f"Unknown store type: {store_type}")
    
    def _execute_condition_step(self, step, context):
        """Execute a conditional step"""
        condition = step.get('condition')
        
        # Replace variables in condition with values from context
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                placeholder = f"${key}"
                if placeholder in condition:
                    condition = condition.replace(placeholder, str(value))
        
        # Evaluate condition
        try:
            result = eval(condition)
            
            if result:
                # Execute 'then' branch
                then_steps = step.get('then', [])
                then_results = {}
                
                for then_step in then_steps:
                    result = self._execute_step(then_step, context)
                    if result:
                        then_results.update(result)
                
                return then_results
            else:
                # Execute 'else' branch
                else_steps = step.get('else', [])
                else_results = {}
                
                for else_step in else_steps:
                    result = self._execute_step(else_step, context)
                    if result:
                        else_results.update(result)
                
                return else_results
        except Exception as e:
            logger.error(f"Error evaluating condition: {str(e)}")
            raise ValueError(f"Error evaluating condition: {str(e)}")


# Create global workflow engine instance
workflow_engine = WorkflowEngine()

def start_workflow_engine():
    """Start the workflow engine"""
    workflow_engine.start()

def stop_workflow_engine():
    """Stop the workflow engine"""
    workflow_engine.stop()

def execute_workflow(workflow_id, context=None):
    """Execute a workflow"""
    return workflow_engine.execute_workflow(workflow_id, context or {})

def create_workflow(name, description, steps, schedule=None, trigger_type=None, trigger_config=None):
    """
    Create a new workflow definition
    
    Args:
        name (str): Name of the workflow
        description (str): Description of the workflow
        steps (list): List of workflow steps
        schedule (dict, optional): Schedule for the workflow
        trigger_type (str, optional): Type of trigger for the workflow
        trigger_config (dict, optional): Configuration for the trigger
        
    Returns:
        WorkflowDefinition: Created workflow definition
    """
    try:
        # Validate steps
        for step in steps:
            if 'type' not in step:
                raise ValueError("Each step must have a 'type'")
        
        # Create workflow definition
        workflow = WorkflowDefinition(
            name=name,
            description=description,
            steps=json.dumps(steps),
            schedule=json.dumps(schedule) if schedule else None,
            trigger_type=trigger_type,
            trigger_config=json.dumps(trigger_config) if trigger_config else None,
            is_active=True,
            created_at=datetime.now()
        )
        
        db.session.add(workflow)
        db.session.commit()
        
        logger.info(f"Created workflow: {name} (ID: {workflow.id})")
        return workflow
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating workflow: {str(e)}")
        raise