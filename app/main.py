
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.schemas import ActionRequest
from app.gate.controller import evaluate_plan
from app.tools.registry import execute_action


app = FastAPI(
    title="ACTION GATE",
    description="A security layer for AI agent actions.",
    version="0.1.0",
)


class PlanRequest(BaseModel):
    actions: list[ActionRequest] = Field(max_length=50)


@app.get("/")
def home():
    return {
        "project": "ACTION GATE",
        "status": "running",
        "message": "AI action security gateway is online.",
    }


@app.post("/evaluate")
def evaluate(request: PlanRequest):
    return evaluate_plan(request.actions)


@app.post("/execute")
def execute(action: ActionRequest):
    result = execute_action(action, principal="ai_agent")

    if not result.get("success"):
        raise HTTPException(status_code=403, detail=result)

    return result
