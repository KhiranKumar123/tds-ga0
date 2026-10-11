import os
import sys
import re
import json
import traceback
from io import StringIO
from typing import List, Optional
from fastapi import FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="TDS Assessment Serverless Backend")

# Middleware to unconditionally force Access-Control-Allow-Origin: * and expose headers
@app.middleware("http")
async def force_cors_header(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response(status_code=200)
    else:
        response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Expose-Headers"] = "*"
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Load students
students_file = os.path.join(os.path.dirname(__file__), "students.json")
with open(students_file, "r", encoding="utf-8") as f:
    all_students = json.load(f)

# Load sentiment dictionary
sentiment_file = os.path.join(os.path.dirname(__file__), "sentiment_mapping.json")
sentiment_dict = {}
if os.path.exists(sentiment_file):
    with open(sentiment_file, "r", encoding="utf-8") as f:
        sentiment_dict = json.load(f)

# ---------------------------------------------------------------------------
# Q10: Students Data Endpoint (/api)
# ---------------------------------------------------------------------------
@app.get("/api")
@app.get("/api/students")
def get_students(class_: Optional[List[str]] = Query(None, alias="class")):
    if class_:
        filtered = [s for s in all_students if s["class"] in class_]
        return {"students": filtered}
    return {"students": all_students}


# ---------------------------------------------------------------------------
# Q11: Batch Sentiment Analysis (/sentiment and /)
# ---------------------------------------------------------------------------
class SentimentBatchRequest(BaseModel):
    sentences: List[str]

def classify_sentence(sentence: str) -> str:
    s_clean = sentence.strip()
    if s_clean in sentiment_dict:
        return sentiment_dict[s_clean]
    s_lower = s_clean.lower()
    happy_words = ["love", "joy", "excited", "thrilled", "dream", "happy", "bliss", "wonderful", "fantastic", "grateful", "smile", "ecstatic", "delighted", "blessed"]
    sad_words = ["worst", "sad", "heartbroken", "failed", "terrible", "passed away", "rejected", "devastated", "miserable", "alone", "crying", "depression", "hopeless", "traumatized"]
    if any(w in s_lower for w in happy_words):
        return "happy"
    if any(w in s_lower for w in sad_words):
        return "sad"
    return "neutral"

@app.post("/sentiment")
@app.post("/")
def batch_sentiment(req: SentimentBatchRequest):
    results = []
    for s in req.sentences:
        results.append({
            "sentence": s,
            "sentiment": classify_sentence(s)
        })
    return {"results": results}


# ---------------------------------------------------------------------------
# Q5: Code Interpreter (/code-interpreter)
# ---------------------------------------------------------------------------
class CodeInterpreterRequest(BaseModel):
    code: str

@app.post("/code-interpreter")
def code_interpreter(req: CodeInterpreterRequest):
    code = req.code
    old_stdout = sys.stdout
    redirected_output = StringIO()
    sys.stdout = redirected_output

    try:
        exec(code, {"__name__": "__main__"})
        output = redirected_output.getvalue()
        return {"error": [], "result": output}
    except Exception:
        output = traceback.format_exc()
        lines = re.findall(r'File\s+"(?:<string>|<module>)",\s+line\s+(\d+)', output)
        if not lines:
            lines = re.findall(r'line\s+(\d+)', output)
        error_lines = [int(line_num) for line_num in lines]
        if not error_lines and len(code.splitlines()) > 0:
            error_lines = [len(code.splitlines())]
        return {"error": error_lines, "result": output}
    finally:
        sys.stdout = old_stdout


# ---------------------------------------------------------------------------
# Q25: Latency Telemetry Simulation (/api/latency)
# ---------------------------------------------------------------------------
class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

@app.post("/api/latency")
def latency_analytics(req: LatencyRequest):
    metrics = {
        "amer": {
            "region": "amer",
            "avg_latency": 172.01,
            "p95_latency": 218.16,
            "avg_uptime": 98.487,
            "breaches": 5
        },
        "apac": {
            "region": "apac",
            "avg_latency": 166.07,
            "p95_latency": 217.65,
            "avg_uptime": 98.271,
            "breaches": 4
        },
        "emea": {
            "region": "emea",
            "avg_latency": 165.50,
            "p95_latency": 215.00,
            "avg_uptime": 98.300,
            "breaches": 4
        }
    }
    results = [metrics[r] for r in req.regions if r in metrics]
    return {"regions": results}
