from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from helpers import intersect

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent.absolute() / "static"),
    name="static",
)
templates = Jinja2Templates(directory="templates/")
app.state.lastTaskId = 0
app.state.progressDict = {}

@app.get("/healthcheck")
def read_healthcheck():
    return {"status": "ok"}

@app.get("/")
def form_get(request: Request):
    return templates.TemplateResponse('form.html', \
                                      context={'request': request})

@app.get("/newtask")
def get_new_task(request: Request):
    app.state.lastTaskId = app.state.lastTaskId + 1
    return app.state.lastTaskId

@app.post("/intersector")
def form_post(request: Request, taskId: int = Form(0), target_drama: str = Form(...), 
              user_list: str = Form(...), pleaseSpoiler: bool = Form(False)):
    app.state.progressDict[taskId] = "Looking..."
    def progressFn(prog_rep: str):
        print(prog_rep)
        app.state.progressDict[taskId] = prog_rep
    def checkFn():
        most_recent = taskId >= app.state.lastTaskId
        if not most_recent:
            print('Should cancel task', taskId)
        return most_recent

    common_actors = intersect(target_drama, user_list, checkFn, progressFn)

    # Don't want to keep growing memory as taskIds grow
    del app.state.progressDict[taskId]

    return templates.TemplateResponse('results.html', \
                                       context={'request': request, \
                                                'result_actors': common_actors, \
                                                'pleaseSpoiler': pleaseSpoiler})

@app.get("/progress/{taskId}")
def get_progress(taskId: int):
    if int(taskId) in app.state.progressDict:
        return app.state.progressDict[int(taskId)]
    return "Looking..."
