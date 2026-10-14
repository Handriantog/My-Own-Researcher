"""Review-only endpoints and explicit durable research lifecycle actions."""
from functools import wraps
from flask import Blueprint, current_app, request, g
from research_runtime import current_context, inference_scope, InferenceContext
from ..services import research_settings as settings
from ..services.research_drafts import ResearchDrafts
from ..services.research_estimates import estimate
from ..services.research_storage import research_root
from ..models.project import ProjectManager
from ..services.simulation_manager import SimulationManager
from ..services.report_agent import ReportManager

research_bp = Blueprint('research',__name__)


def guarded(function):
    @wraps(function)
    def wrapped(*args,**kwargs):
        try:
            return function(*args,**kwargs)
        except LookupError as error:
            return {'success':False,'error':str(error)},404
        except (ValueError,TypeError) as error:
            return {'success':False,'error':str(error)},400
        except RuntimeError as error:
            return {'success':False,'error':str(error)},409
    return wrapped


def runs():
    return current_app.extensions['research_runs']


def body():
    data = request.get_json(silent=True)
    if not isinstance(data,dict):
        raise ValueError('A JSON object is required')
    return data


@research_bp.route('/settings',methods=['GET','PUT'])
@guarded
def preferences():
    if request.method == 'GET':
        return {'success':True,'data':settings.settings_payload()}
    value = settings.validate_settings(body())
    return {'success':True,'data':settings.save_defaults(value)}


@research_bp.post('/drafts')
@guarded
def create_draft():
    drafts = ResearchDrafts()
    draft = drafts.create(request.files.getlist('files'),request.form.get('question',''))
    return {'success':True,'data':drafts.public(draft)},201


@research_bp.get('/drafts/<draft_id>')
@guarded
def get_draft(draft_id):
    drafts = ResearchDrafts()
    return {'success':True,'data':drafts.public(drafts.get(draft_id))}


@research_bp.get('/projects/<project_id>')
@guarded
def review_project(project_id):
    import re
    if not re.fullmatch(r'proj_[A-Za-z0-9_-]+',project_id):
        raise ValueError('Invalid project ID')
    project = ProjectManager.get_project(project_id)
    if not project:
        raise LookupError('Project not found')
    return {'success':True,'data':{'project_id':project_id,'question':project.simulation_requirement,
        'files':project.files,'text_length':project.total_text_length,'research_run_id':project.research_run_id}}


@research_bp.post('/estimate')
@guarded
def estimate_draft():
    data = body()
    chosen = settings.validate_settings(data.get('settings',{}))
    if data.get('draft_id'):
        text = ResearchDrafts().text(data['draft_id'])
    else:
        import re
        project_id=data.get('project_id','')
        if not re.fullmatch(r'proj_[A-Za-z0-9_-]+',project_id):
            raise ValueError('A draft or project is required')
        text=ProjectManager.get_extracted_text(project_id)
        if not text:
            raise LookupError('Saved source text is unavailable')
    return {'success':True,'data':estimate(text,chosen)}


@research_bp.post('/runs')
@guarded
def start_run():
    data=body()
    existing=runs().retry(data)
    if existing:
        return {'success':True,'data':existing},202
    chosen=settings.validate_settings(data.get('settings',{}))
    metadata=settings.settings_payload()
    if metadata['provider']['connection']=='unavailable':
        existing=runs().retry(data)
        if existing:
            return {'success':True,'data':existing},202
        raise ValueError('Connect the configured provider before starting research')
    graph=metadata['graph']
    if graph['status']=='unavailable':
        existing=runs().retry(data)
        if existing:
            return {'success':True,'data':existing},202
        raise ValueError(graph.get('error') or 'The graph service is unavailable')
    graph_snapshot={key:graph.get(key) for key in ('provider','inference_provider','model')}
    result=runs().start(data.get('draft_id'),chosen,data.get('idempotency_key'),
        project_id=data.get('project_id'),simulation_id=data.get('simulation_id'),
        graph_settings=graph_snapshot,locale='zh' if request.headers.get('Accept-Language','en').startswith('zh') else 'en')
    return {'success':True,'data':result},202


@research_bp.get('/runs/<run_id>')
@guarded
def get_run(run_id):
    return {'success':True,'data':runs().get(run_id)}


@research_bp.post('/runs/<run_id>/stop')
@guarded
def stop_run(run_id):
    return {'success':True,'data':runs().stop(run_id)},202


@research_bp.post('/runs/<run_id>/resume')
@guarded
def resume_run(run_id):
    return {'success':True,'data':runs().resume(run_id)},202


@research_bp.post('/runs/<run_id>/partial-report')
@guarded
def partial_report(run_id):
    return {'success':True,'data':runs().resume(run_id,partial_report=True)},202


INFERENCE_PATHS = {'/api/graph/ontology/generate','/api/graph/ontology/resume','/api/graph/build',
    '/api/simulation/prepare','/api/simulation/start','/api/simulation/generate-profiles',
    '/api/simulation/interview','/api/simulation/interview/batch','/api/simulation/interview/all',
    '/api/report/generate','/api/report/chat'}


def bind_reviewed_inference():
    if request.method!='POST' or request.path not in INFERENCE_PATHS or current_context() is not None:
        return
    data=request.get_json(silent=True) or {}
    project_id=data.get('project_id')
    simulation_id=data.get('simulation_id')
    if data.get('report_id'):
        report=ReportManager.get_report(data['report_id'])
        simulation_id=report.simulation_id if report else simulation_id
    if simulation_id:
        simulation=SimulationManager().get_simulation(simulation_id)
        if simulation:
            project_id=simulation.project_id
    project=ProjectManager.get_project(project_id) if project_id else None
    context=None
    if project and getattr(project, 'research_run_id', None):
        try:
            run=runs().raw(project.research_run_id)
            if request.headers.get('X-Research-Client')=='browser' and run['status'] in {'running','queued','stopping'}:
                return {'success':False,'code':'run_active','run_id':run['run_id'],
                        'error':'This research is already running. Follow its progress.'},409
            context=runs().context(run)
        except LookupError:
            pass
    if context is None and request.headers.get('X-Research-Client')=='browser':
        return {'success':False,'code':'review_required','error':'Review the research settings before starting model work.',
                'review':{'project_id':project_id,'simulation_id':simulation_id}},409
    if context is None and data.get('research_settings'):
        import hashlib
        chosen=settings.validate_settings(data['research_settings'])
        key=hashlib.sha256(str(project_id or simulation_id or 'legacy').encode()).hexdigest()[:24]
        context=InferenceContext('api_'+key,chosen['provider'],chosen['model'],chosen['concurrency'])
    if context:
        scope=inference_scope(context)
        scope.__enter__()
        g.research_inference_scope=scope


def unbind_reviewed_inference(error=None):
    scope=g.pop('research_inference_scope',None)
    if scope:
        scope.__exit__(None,None,None)
