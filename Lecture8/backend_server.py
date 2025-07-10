from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import Column, Integer, String, Text
from typing import Any, Dict, List, Optional
from agno.models.openai import OpenAIChat
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dotenv import load_dotenv
from agno.agent import Agent
import traceback
import uvicorn
import json


from variables import BACKEND_BASE_URL, BACKEND_PORT, Base, SessionLocal, engine

load_dotenv()


class TaskModel(Base):
    """
    Database model for storing task definitions.
    """

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    system_prompt = Column(Text, nullable=False)
    parameters = Column(Text, nullable=False)


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Task Management API",
    description="API for managing and executing AI tasks using Agno agents",
    version="1.0.0",
)

agent = Agent(
    name="Task Executor",
    model=OpenAIChat(id="gpt-4o-mini"),
    add_history_to_messages=True,
    num_history_responses=3,
    add_datetime_to_instructions=True,
    markdown=True,
)


class TaskParameter(BaseModel):
    """
    Model for task parameter definition.
    """

    name: str


class TaskCreate(BaseModel):
    """
    Model for creating a new task.
    """

    name: str
    system_prompt: str
    parameters: List[TaskParameter]


class TaskEdit(BaseModel):
    """
    Model for editing an existing task.
    """

    name: Optional[str] = None
    system_prompt: Optional[str] = None
    parameters: Optional[List[TaskParameter]] = None


class TaskResponse(BaseModel):
    """
    Model for task response.
    """

    id: int
    name: str
    system_prompt: str
    parameters: List[TaskParameter]


class TaskExecutionResponse(BaseModel):
    """
    Model for task execution response.
    """

    result: str
    task_name: str


def get_db() -> Session:
    """
    Get database session.

    :return: Database session.
    :rtype: Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/api/v1/tasks/create", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)) -> TaskResponse:
    """
    Create a new task definition.

    :param task: Task creation data.
    :type task: TaskCreate
    :param db: Database session.
    :type db: Session
    :raises HTTPException: If task name already exists or database error occurs.
    :return: Created task information.
    :rtype: TaskResponse
    """
    try:
        existing_task = db.query(TaskModel).filter(TaskModel.name == task.name).first()
        if existing_task:
            raise HTTPException(
                status_code=400, detail=f"Task with name '{task.name}' already exists"
            )

        parameters_json = json.dumps([param.dict() for param in task.parameters])

        db_task = TaskModel(
            name=task.name, system_prompt=task.system_prompt, parameters=parameters_json
        )

        db.add(db_task)
        db.commit()
        db.refresh(db_task)

        parameters = [
            TaskParameter(**param) for param in json.loads(db_task.parameters)
        ]

        return TaskResponse(
            id=db_task.id,
            name=db_task.name,
            system_prompt=db_task.system_prompt,
            parameters=parameters,
        )

    except (ValueError, TypeError) as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=400, detail=f"Invalid parameter format: {str(e)}"
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@app.patch("/api/v1/tasks/edit/{task_id}", response_model=TaskResponse)
def edit_task(
    task_id: int, task_update: TaskEdit, db: Session = Depends(get_db)
) -> TaskResponse:
    """
    Edit an existing task definition.

    :param task_id: ID of the task to edit.
    :type task_id: int
    :param task_update: Task update data.
    :type task_update: TaskEdit
    :param db: Database session.
    :type db: Session
    :raises HTTPException: If task not found or database error occurs.
    :return: Updated task information.
    :rtype: TaskResponse
    """
    try:
        db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not db_task:
            raise HTTPException(
                status_code=404, detail=f"Task with ID {task_id} not found"
            )

        if task_update.name is not None:
            existing_task = (
                db.query(TaskModel)
                .filter(TaskModel.name == task_update.name, TaskModel.id != task_id)
                .first()
            )
            if existing_task:
                raise HTTPException(
                    status_code=400,
                    detail=f"Task with name '{task_update.name}' already exists",
                )
            db_task.name = task_update.name

        if task_update.system_prompt is not None:
            db_task.system_prompt = task_update.system_prompt

        if task_update.parameters is not None:
            parameters_json = json.dumps(
                [param.dict() for param in task_update.parameters]
            )
            db_task.parameters = parameters_json

        db.commit()
        db.refresh(db_task)

        parameters = [
            TaskParameter(**param) for param in json.loads(db_task.parameters)
        ]

        return TaskResponse(
            id=db_task.id,
            name=db_task.name,
            system_prompt=db_task.system_prompt,
            parameters=parameters,
        )

    except (ValueError, TypeError) as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=400, detail=f"Invalid parameter format: {str(e)}"
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to edit task: {str(e)}")


@app.post("/api/v1/tasks/execute", response_model=TaskExecutionResponse)
def execute_task(
    task_name: str = Query(..., description="Name of the task to execute"),
    task_params: Dict[str, Any] = None,
    db: Session = Depends(get_db),
) -> TaskExecutionResponse:
    """
    Execute a task with given parameters.

    :param task_name: Name of the task to execute.
    :type task_name: str
    :param task_params: Parameters for task execution.
    :type task_params: Dict[str, Any]
    :param db: Database session.
    :type db: Session
    :raises HTTPException: If task not found or execution fails.
    :return: Task execution result.
    :rtype: TaskExecutionResponse
    """
    try:
        db_task = db.query(TaskModel).filter(TaskModel.name == task_name).first()
        if not db_task:
            raise HTTPException(status_code=404, detail=f"Task '{task_name}' not found")

        expected_params = json.loads(db_task.parameters)

        missing_params = []
        filtered_params = {}
        for param_def in expected_params:
            param_name = param_def["name"]

            if param_name in task_params:
                filtered_params[param_name] = task_params[param_name]

            if param_name not in task_params or task_params[param_name] is None:
                missing_params.append(param_name)

        task_params = filtered_params

        if missing_params:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required parameters: {', '.join(missing_params)}",
            )

        param_text = ""
        for param_def in expected_params:
            param_name = param_def["name"]

            if param_name in task_params:
                param_text += f"\n{param_name}: {task_params[param_name]}"
            else:
                param_text += f"\n{param_name}: Not provided"

        full_prompt = f"{db_task.system_prompt}\n\nParameters:{param_text}"

        response = agent.run(full_prompt)

        return TaskExecutionResponse(result=response.content, task_name=task_name)

    except (ValueError, TypeError) as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Invalid parameters: {str(e)}")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(e)}")


@app.get("/api/v1/tasks/list", response_model=List[TaskResponse])
def list_tasks(db: Session = Depends(get_db)) -> List[TaskResponse]:
    """
    List all available tasks.

    :param db: Database session.
    :type db: Session
    :raises HTTPException: If database error occurs.
    :return: List of all tasks.
    :rtype: List[TaskResponse]
    """
    try:
        tasks = db.query(TaskModel).all()
        result = []

        for task in tasks:
            parameters = [
                TaskParameter(**param) for param in json.loads(task.parameters)
            ]
            result.append(
                TaskResponse(
                    id=task.id,
                    name=task.name,
                    system_prompt=task.system_prompt,
                    parameters=parameters,
                )
            )

        return result

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@app.get("/api/v1/tasks/read/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)) -> TaskResponse:
    """
    Get a specific task by ID.

    :param task_id: ID of the task to retrieve.
    :type task_id: int
    :param db: Database session.
    :type db: Session
    :raises HTTPException: If task not found.
    :return: Task information.
    :rtype: TaskResponse
    """
    try:
        db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not db_task:
            raise HTTPException(
                status_code=404, detail=f"Task with ID {task_id} not found"
            )

        parameters = [
            TaskParameter(**param) for param in json.loads(db_task.parameters)
        ]

        return TaskResponse(
            id=db_task.id,
            name=db_task.name,
            system_prompt=db_task.system_prompt,
            parameters=parameters,
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")


@app.delete("/api/v1/tasks/delete/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)) -> Dict[str, bool]:
    """
    Delete a task by ID.

    :param task_id: ID of the task to delete.
    :type task_id: int
    :param db: Database session.
    :type db: Session
    :raises HTTPException: If task not found.
    :return: Success confirmation.
    :rtype: Dict[str, bool]
    """
    try:
        db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not db_task:
            raise HTTPException(
                status_code=404, detail=f"Task with ID {task_id} not found"
            )

        db.delete(db_task)
        db.commit()

        return {"ok": True}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host=BACKEND_BASE_URL, port=BACKEND_PORT)
