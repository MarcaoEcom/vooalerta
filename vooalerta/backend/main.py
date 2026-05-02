import os, json, logging, re
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from fast_flights import FlightData, Passengers, get_flights
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# ROTAS QUE VOCÊ QUER MONITORAR
# ──────────────────────────────────────────────
ROUTES = [
    {"origin": "POA", "destination": "GRU", "origin_city": "Porto Alegre", "dest_city": "São Paulo"},
    {"origin": "POA", "destination": "GIG", "origin_city": "Porto Alegre", "dest_city": "Rio de Janeiro"},
    {"origin": "POA", "destination": "FLN", "origin_city": "Porto Alegre", "dest_city": "Florianópolis"},
    {"origin": "POA", "destination": "CWB", "origin_city": "Porto Alegre", "dest_city": "Curitiba"},
]

MINIMUM_DISCOUNT_PCT = int(os.getenv("MINIMUM_DISCOUNT_PCT", "20"))
DAYS_AHEAD           = int(os.getenv("DAYS_AHEAD", "30"))
CACHE_FILE           = "data/flights_cache.json"
HISTORY_FILE         = "data/sent_history.json"
# ──────────────────────────────────────────────

os.makedirs("data", exist_ok=True)


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_price(price_str: str) -> float | None:
    """Converte string de preço (ex: 'R$286' ou 'BRL 286') para float."""
    nums = re.findall(r"[\d.,]+", price_str.replace(",", ""))
    return float(nums[0]) if nums else None


def price_label_to_multiplier(label: str) -> float:
    """Estima desconto baseado no indicador do Google Flights."""
    return {"low": 0.75, "typical": 1.0, "high": 1.25}.get(label, 1.0)


def search_flights(route: dict, dates: list[str]) -> list[dict]:
    results = []
    passengers = Passengers(adults=1)

    for date in dates:
        try:
            flight_data = [FlightData(date=date, from_airport=route["origin"], to_airport=route["destination"])]
            result = get_flights(
                flight_data=flight_data,
                passengers=passengers,
                trip="one-way",
                seat="economy",
                fetch_mode="fallback",
            )

            price_level = result.current_price  # "low", "typical", "high"

            for i, f in enumerate(result.flights[:5]):
                price = parse_price(f.price)
                if not price:
                    continue

                # Estima preço de referência usando o indicador do Google
                multiplier = price_label_to_multiplier(price_level)
                ref_price  = round(price / multiplier) if price_level == "low" else price
                discount   = max(0, round((1 - price / ref_price) * 100)) if price_level == "low" else 0

                # Extrai data e hora do campo departure (ex: "11:30 PM")
                dep_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m")
                dep_time = f.departure.strip() if f.departure else "—"

                flight_id = f"{route['origin']}-{route['destination']}-{date}-{i}"

                results.append({
                    "id":          flight_id,
                    "origin":      route["origin"],
                    "destination": route["destination"],
                    "origin_city": route["origin_city"],
                    "dest_city":   route["dest_city"],
                    "date":        dep_date,
                    "time":        dep_time,
                    "airline":     f.name,
                    "duration":    f.duration,
                    "stops":       f.stops,
                    "price":       round(price),
                    "price_orig":  ref_price,
                    "discount":    discount,
                    "price_level": price_level,
                    "is_best":     f.is_best,
                    "status":      "ativo",
                    "sent":        False,
                    "sent_at":     None,
                    "found_at":    datetime.now().isoformat(),
                })

        except Exception as e:
            log.warning(f"Erro buscando {route['origin']}→{route['destination']} em {date}: {e}")

    return results


def format_whatsapp_msg(flight: dict) -> str:
    discount_line = f"💰 R$ {flight['price']} com *{flight['discount']}% OFF*" if flight["discount"] > 0 else f"💰 R$ {flight['price']} (preço baixo agora)"
    stops_line    = "✈️ voo direto" if flight["stops"] == 0 else f"🔄 {flight['stops']} parada(s)"
    return (
        f"✈️ *VOO COM DESCONTO!*\n\n"
        f"🛫 {flight['origin_city']} → {flight['dest_city']}\n"
        f"📅 Dia {flight['date']} às {flight['time']}\n"
        f"{discount_line}\n"
        f"{stops_line} · {flight['duration']}\n"
        f"🏢 {flight['airline']}\n\n"
        f"_Aproveite enquanto dura!_ 🔥"
    )


def run_search():
    log.info("🔍 Iniciando busca de voos no Google Flights...")
    history   = set(load_json(HISTORY_FILE, []))
    cache     = load_json(CACHE_FILE, [])
    cache_ids = {f["id"] for f in cache}
    new_count = 0

    dates = [
        (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(1, DAYS_AHEAD + 1)
    ]

    for route in ROUTES:
        log.info(f"Buscando {route['origin_city']} → {route['dest_city']}...")
        flights = search_flights(route, dates)

        for flight in flights:
            # Atualiza cache
            if flight["id"] not in cache_ids:
                cache.append(flight)
                cache_ids.add(flight["id"])
                new_count += 1

            # Verifica se vale disparar mensagem
            if flight["id"] in history:
                continue
            if flight["price_level"] != "low" and flight["discount"] < MINIMUM_DISCOUNT_PCT:
                continue

            msg = format_whatsapp_msg(flight)
            log.info(f"\n{msg}\n")

            # Marca como enviado (WhatsApp será conectado na próxima etapa)
            flight["sent"]    = True
            flight["sent_at"] = datetime.now().strftime("%d/%m %H:%M")
            history.add(flight["id"])

            # Atualiza no cache também
            for c in cache:
                if c["id"] == flight["id"]:
                    c["sent"]    = True
                    c["sent_at"] = flight["sent_at"]

    save_json(CACHE_FILE, cache)
    save_json(HISTORY_FILE, list(history))
    log.info(f"✅ Busca concluída. {new_count} novos voos encontrados. Total no cache: {len(cache)}")


if __name__ == "__main__":
    run_search()  # roda imediatamente ao iniciar

    scheduler = BlockingScheduler(timezone="America/Sao_Paulo")
    hour   = int(os.getenv("SEARCH_HOUR", "8"))
    minute = int(os.getenv("SEARCH_MINUTE", "0"))
    scheduler.add_job(run_search, "cron", hour=hour, minute=minute)
    log.info(f"⏰ Próxima busca agendada para {hour:02d}:{minute:02d} BRT")
    scheduler.start()
