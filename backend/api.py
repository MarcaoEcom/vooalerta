import os, json
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

EXAMPLE = [
    {"id":"e1","origin":"POA","destination":"GRU","origin_city":"Porto Alegre","dest_city":"São Paulo","date":"14/05","time":"07:00 AM","airline":"LATAM","duration":"1h 35m","stops":0,"price":286,"price_orig":520,"discount":45,"price_level":"low","is_best":True,"status":"ativo","sent":True,"sent_at":"01/05 08:02","found_at":datetime.now().isoformat()},
    {"id":"e2","origin":"POA","destination":"GIG","origin_city":"Porto Alegre","dest_city":"Rio de Janeiro","date":"15/05","time":"06:30 AM","airline":"Gol","duration":"2h 10m","stops":0,"price":336,"price_orig":480,"discount":30,"price_level":"low","is_best":False,"status":"ativo","sent":True,"sent_at":"01/05 08:03","found_at":datetime.now().isoformat()},
    {"id":"e3","origin":"POA","destination":"FLN","origin_city":"Porto Alegre","dest_city":"Florianópolis","date":"16/05","time":"09:15 AM","airline":"Azul","duration":"50m","stops":0,"price":217,"price_orig":310,"discount":30,"price_level":"low","is_best":True,"status":"ativo","sent":False,"sent_at":None,"found_at":datetime.now().isoformat()},
    {"id":"e4","origin":"POA","destination":"CWB","origin_city":"Porto Alegre","dest_city":"Curitiba","date":"17/05","time":"11:00 AM","airline":"LATAM","duration":"1h 05m","stops":0,"price":203,"price_orig":290,"discount":30,"price_level":"low","is_best":False,"status":"ativo","sent":False,"sent_at":None,"found_at":datetime.now().isoformat()},
]


def load_flights():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            data = json.load(f)
            return data if data else EXAMPLE
    return EXAMPLE


@app.get("/api/flights")
def get_flights_api(filter: str = "todos", q: str = ""):
    flights = load_flights()
    if q:
        ql = q.lower()
        flights = [f for f in flights if ql in (f["origin_city"]+f["dest_city"]+f["airline"]).lower()]
    if filter == "ativo":    flights = [f for f in flights if f["status"] == "ativo"]
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


app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
