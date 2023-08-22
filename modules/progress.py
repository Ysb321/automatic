import base64
import io
import time
from pydantic import BaseModel, Field # pylint: disable=no-name-in-module
import modules.shared as shared


current_task = None
pending_tasks = {}
finished_tasks = []
recorded_results = []
recorded_results_limit = 2


def start_task(id_task):
    global current_task # pylint: disable=global-statement
    current_task = id_task
    pending_tasks.pop(id_task, None)


def record_results(id_task, res):
    recorded_results.append((id_task, res))
    if len(recorded_results) > recorded_results_limit:
        recorded_results.pop(0)


def finish_task(id_task):
    global current_task # pylint: disable=global-statement
    if current_task == id_task:
        current_task = None
    finished_tasks.append(id_task)
    if len(finished_tasks) > 16:
        finished_tasks.pop(0)


def add_task_to_queue(id_job):
    pending_tasks[id_job] = time.time()


class ProgressRequest(BaseModel):
    id_task: str = Field(default=None, title="Task ID", description="id of the task to get progress for")
    id_live_preview: int = Field(default=-1, title="Live preview image ID", description="id of last received last preview image")


class InternalProgressResponse(BaseModel):
    active: bool = Field(title="Whether the task is being worked on right now")
    queued: bool = Field(title="Whether the task is in queue")
    paused: bool = Field(title="Whether the task is paused")
    completed: bool = Field(title="Whether the task has already finished")
    progress: float = Field(default=None, title="Progress", description="The progress with a range of 0 to 1")
    eta: float = Field(default=None, title="ETA in secs")
    live_preview: str = Field(default=None, title="Live preview image", description="Current live preview; a data: uri")
    id_live_preview: int = Field(default=None, title="Live preview image ID", description="Send this together with next request to prevent receiving same image")
    textinfo: str = Field(default=None, title="Info text", description="Info text used by WebUI.")


def setup_progress_api(app):
    return app.add_api_route("/internal/progress", progressapi, methods=["POST"], response_model=InternalProgressResponse)


def progressapi(req: ProgressRequest):
    active = req.id_task == current_task
    queued = req.id_task in pending_tasks
    completed = req.id_task in finished_tasks
    paused = shared.state.paused
    if not active:
        return InternalProgressResponse(active=active, queued=queued, paused=paused, completed=completed, id_live_preview=-1, textinfo="Queued..." if queued else "Waiting...")
    progress = 0
    job_count, job_no = shared.state.job_count, shared.state.job_no
    sampling_steps, sampling_step = shared.state.sampling_steps, shared.state.sampling_step
    if job_count > 0:
        progress += job_no / job_count
    if sampling_steps > 0 and job_count > 0:
        progress += 1 / job_count * sampling_step / sampling_steps
    progress = min(progress, 1)
    elapsed_since_start = time.time() - shared.state.time_start
    predicted_duration = elapsed_since_start / progress if progress > 0 else None
    eta = predicted_duration - elapsed_since_start if predicted_duration is not None else None
    id_live_preview = req.id_live_preview
    live_preview = None
    shared.state.set_current_image()
    if shared.opts.live_previews_enable and (shared.state.id_live_preview != req.id_live_preview) and (shared.state.current_image is not None):
        buffered = io.BytesIO()
        shared.state.current_image.save(buffered, format='jpeg')
        live_preview = f'data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode("ascii")}'
        id_live_preview = shared.state.id_live_preview
    return InternalProgressResponse(active=active, queued=queued, paused=paused, completed=completed, progress=progress, eta=eta, live_preview=live_preview, id_live_preview=id_live_preview, textinfo=shared.state.textinfo)
