from app import db
from datetime import datetime
import json

class WorkflowDefinition(db.Model):
    """Model for storing workflow definitions for automated intelligence gathering"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=True)
    steps = db.Column(db.Text, nullable=True)  # JSON string of workflow steps
    schedule = db.Column(db.Text, nullable=True)  # JSON string of schedule configuration
    trigger_type = db.Column(db.String(64), nullable=True)  # 'schedule', 'event', 'manual'
    trigger_config = db.Column(db.Text, nullable=True)  # JSON string of trigger configuration
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    executions = db.relationship('WorkflowExecution', backref='workflow', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<WorkflowDefinition {self.id}: {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'steps': json.loads(self.steps) if self.steps else [],
            'schedule': json.loads(self.schedule) if self.schedule else None,
            'trigger_type': self.trigger_type,
            'trigger_config': json.loads(self.trigger_config) if self.trigger_config else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class WorkflowExecution(db.Model):
    """Model for storing workflow execution records"""
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow_definition.id'), nullable=False)
    status = db.Column(db.String(32), nullable=False)  # 'running', 'completed', 'failed'
    context = db.Column(db.Text, nullable=True)  # JSON string of execution context
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    error = db.Column(db.Text, nullable=True)
    
    # Relationships
    steps = db.relationship('WorkflowStep', backref='execution', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<WorkflowExecution {self.id}: {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'status': self.status,
            'context': json.loads(self.context) if self.context else {},
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'error': self.error,
            'steps': [step.to_dict() for step in self.steps]
        }

class WorkflowStep(db.Model):
    """Model for storing workflow step execution records"""
    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.Integer, db.ForeignKey('workflow_execution.id'), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    step_type = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(32), nullable=False)  # 'running', 'completed', 'failed'
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    result = db.Column(db.Text, nullable=True)  # JSON string of step result
    error = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<WorkflowStep {self.id}: {self.step_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'step_number': self.step_number,
            'step_type': self.step_type,
            'status': self.status,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'result': json.loads(self.result) if self.result else None,
            'error': self.error
        }

class APIConfiguration(db.Model):
    """Model for storing API configurations for OSINT searches"""
    id = db.Column(db.Integer, primary_key=True)
    api_name = db.Column(db.String(128), nullable=False, unique=True)
    api_url = db.Column(db.String(512), nullable=False)
    api_key_env = db.Column(db.String(128), nullable=True)  # Environment variable name for API key
    description = db.Column(db.Text, nullable=True)
    endpoints = db.Column(db.Text, nullable=True)  # JSON string of endpoint configurations
    format = db.Column(db.Text, nullable=True)  # JSON string of format details
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<APIConfiguration {self.api_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'api_name': self.api_name,
            'api_url': self.api_url,
            'api_key_env': self.api_key_env,
            'description': self.description,
            'endpoints': json.loads(self.endpoints) if self.endpoints else {},
            'format': json.loads(self.format) if self.format else {},
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class OSINTCase(db.Model):
    """Model for storing OSINT cases"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=True)  # Name of the person or case
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    data_points = db.relationship('DataPoint', backref='case', lazy=True, cascade="all, delete-orphan")
    api_results = db.relationship('APIResult', backref='case', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<OSINTCase {self.id}: {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'data_points': [dp.to_dict() for dp in self.data_points],
            'api_results': [ar.to_dict() for ar in self.api_results]
        }

class DataPoint(db.Model):
    """Model for storing data points related to an OSINT case"""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('osint_case.id'), nullable=False)
    data_type = db.Column(db.String(64), nullable=False)  # Type of data (e.g., name, phone, email, etc.)
    value = db.Column(db.Text, nullable=False)  # The actual data value
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<DataPoint {self.id}: {self.data_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'data_type': self.data_type,
            'value': self.value,
            'created_at': self.created_at.isoformat()
        }

class APIResult(db.Model):
    """Model for storing results from API calls"""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('osint_case.id'), nullable=False)
    api_config_id = db.Column(db.Integer, db.ForeignKey('api_configuration.id'), nullable=False)
    endpoint = db.Column(db.String(256), nullable=False)
    query_params = db.Column(db.Text, nullable=True)  # JSON string of parameters used in the query
    result = db.Column(db.Text, nullable=True)  # JSON string of API results
    status = db.Column(db.String(32), nullable=False)  # success, error, etc.
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationship with API configuration
    api_config = db.relationship('APIConfiguration', backref='results')
    
    def __repr__(self):
        return f'<APIResult {self.id}: {self.endpoint}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'case_id': self.case_id,
            'api_config_id': self.api_config_id,
            'endpoint': self.endpoint,
            'query_params': json.loads(self.query_params) if self.query_params else {},
            'result': json.loads(self.result) if self.result else {},
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'api_name': self.api_config.api_name if self.api_config else None
        }
