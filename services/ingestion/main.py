from fastapi import FastAPI, HTTPException
from ingestion.admin import create_topic
from ingestion.track_service.producer import EventProducer
from ingestion.track_service.schemas import AnalyticsEvent

app = FastAPI()
producer = EventProducer()


@app.on_event("startup")
async def startup_event():
    create_topic()


@app.post("/track")
async def track_event(event: AnalyticsEvent):
    try:
        producer.send_event(event)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
