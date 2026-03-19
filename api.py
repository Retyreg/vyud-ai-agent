from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

from agent import VyudAgent
from writer import VyudWriter

load_dotenv()

app = FastAPI(title="VYUD AI API", version="1.0.0")

# Настройка CORS для работы с Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # В продакшене лучше указать конкретный домен лендинга
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Простая защита API ключом (можно вынести в .env)
API_SECRET_KEY = os.getenv("VYUD_API_SECRET", "vyud-secret-key-2026")

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

# Модели данных
class AnalyzeRequest(BaseModel):
    url: str

class AnalyzeResponse(BaseModel):
    company_name: Optional[str]
    industry: Optional[str]
    tech_stack: List[str]
    crm_detected: Optional[str]
    confidence_score: float
    analysis_log: str
    email_draft: str

# Инициализация сервисов
agent = VyudAgent()
writer = VyudWriter()

@app.get("/")
async def health_check():
    return {"status": "online", "message": "VYUD AI API is running"}

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_company(request: AnalyzeRequest, api_key: str = Depends(verify_api_key)):
    """
    Эндпоинт для полного цикла: Скрапинг -> Анализ -> Генерация письма.
    """
    try:
        # 1. Анализ через VyudAgent
        result = agent.analyze_company(url=request.url)
        
        if not result:
            raise HTTPException(status_code=400, detail="Не удалось проанализировать сайт. Проверьте URL.")
        
        # 2. Генерация письма через VyudWriter
        email_draft = writer.generate_email(result.model_dump())
        
        return AnalyzeResponse(
            company_name=result.company_name,
            industry=result.industry,
            tech_stack=result.tech_stack,
            crm_detected=result.crm_detected,
            confidence_score=result.confidence_score,
            analysis_log=result.analysis_log,
            email_draft=email_draft
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
