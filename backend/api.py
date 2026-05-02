import os, json, threading
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()
os.makedirs("data", exist_ok=True)

app = FastAPI(title="VooAlerta")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CACHE_FILE = "data/flights_cache.json"
search_status = {"running": False, "last": None}


def load_flights():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            data = json.load(f)
            return data if data else []
    return []


@app.get("/api/flights")
def get_flights_api(filter: str = "todos", q: str = ""):
    flights = load_flights()
    if q:
        ql = q.lower()
        flights = [f for f in flights if ql in (f["origin_city"]+f["dest_city"]+f.get("airline","")).lower()]
    if filter == "ativo":     flights = [f for f in flights if f["status"] == "ativo"]
    elif filter == "enviado": flights = [f for f in flights if f["sent"]]
    elif filter == "pendente":flights = [f for f in flights if not f["sent"] and f["status"] == "ativo"]
    return {"flights": flights, "updated_at": datetime.now().isoformat()}


@app.get("/api/stats")
def get_stats():
    flights = load_flights()
    return {
        "total":    len(flights),
        "sent":     sum(1 for f in flights if f["sent"]),
        "max_disc": max((f["discount"] for f in flights), default=0),
        "min_cfg":  int(os.getenv("MINIMUM_DISCOUNT_PCT", "20")),
    }


@app.post("/api/search")
def trigger_search():
    if search_status["running"]:
        return {"status": "already_running", "message": "Busca já em andamento, aguarde..."}

    def run():
        search_status["running"] = True
        try:
            import sys
            sys.path.insert(0, os.path.dirname(__file__))
            from main import run_search
            run_search()
            search_status["last"] = datetime.now().isoformat()
        except Exception as e:
            print(f"Erro na busca: {e}")
        finally:
            search_status["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return {"status": "started", "message": "Busca iniciada!"}


@app.get("/api/search/status")
def get_search_status():
    return {"running": search_status["running"], "last": search_status["last"]}


app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
