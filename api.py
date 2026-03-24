from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv
import resend

from agent import VyudAgent
from writer import VyudWriter
from searcher import PersonSearcher

load_dotenv()

app = FastAPI(title="VYUD AI API", version="1.0.0")
resend.api_key = os.getenv("RESEND_API_KEY")

# Настройка CORS для работы с Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Простая защита API ключом
API_SECRET_KEY = os.getenv("VYUD_API_SECRET", "vyud-secret-key-2026")

# Модели данных
class AnalyzeRequest(BaseModel):
    url: str
    target_role: Optional[str] = "Decision Maker"

class DecisionMaker(BaseModel):
    name: Optional[str] = "Коллега"
    title: Optional[str]
    linkedin_url: Optional[str]
    relevance_reason: str

class AnalyzeResponse(BaseModel):
    company_name: Optional[str]
    industry: Optional[str]
    tech_stack: List[str]
    crm_detected: Optional[str]
    confidence_score: float
    analysis_log: str
    email_draft: str
    decision_maker: Optional[DecisionMaker] = None

class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str

# Инициализация сервисов
agent = VyudAgent()
writer = VyudWriter()
searcher = PersonSearcher()

@app.get("/")
async def health_check():
    return {"status": "online", "message": "VYUD AI API is running"}

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_company(request: AnalyzeRequest, x_api_key: str = Header(...)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    try:
        # 1. Анализ компании через VyudAgent
        result = agent.analyze_company(url=request.url)
        
        if not result:
            raise HTTPException(status_code=400, detail="Не удалось получить данные с сайта.")
        
        # 2. Реальный поиск ЛПР через Serper API
        real_dm = searcher.find_decision_maker(result.company_name, request.target_role)
        
        if real_dm:
            dm_info = DecisionMaker(**real_dm)
        else:
            # Fallback к умной ссылке, если поиск не дал результатов
            dm_info = DecisionMaker(
                name="Коллега",
                title=request.target_role,
                linkedin_url=f"https://www.linkedin.com/search/results/people/?keywords={request.target_role.replace(' ', '%20')}%20{result.company_name.replace(' ', '%20')}",
                relevance_reason=f"Ручной поиск в LinkedIn по запросу {request.target_role}"
            )
        
        # 3. Генерация письма через VyudWriter с учетом реального имени ЛПР
        enrichment_data = result.model_dump()
        enrichment_data["target_role"] = request.target_role
        enrichment_data["dm_name"] = dm_info.name
        
        email_draft = writer.generate_email(enrichment_data)
        
        return AnalyzeResponse(
            company_name=result.company_name,
            industry=result.industry,
            tech_stack=result.tech_stack,
            crm_detected=result.crm_detected,
            confidence_score=result.confidence_score,
            analysis_log=result.analysis_log,
            email_draft=email_draft,
            decision_maker=dm_info
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"💥 Системная ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/send-email")
async def send_email(request: SendEmailRequest, x_api_key: str = Header(...)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    try:
        if not resend.api_key:
             raise HTTPException(status_code=500, detail="RESEND_API_KEY не настроен")

        params = {
            "from": "VYUD AI <onboarding@resend.dev>",
            "to": [request.to_email],
            "subject": request.subject,
            "text": request.body,
        }

        email = resend.Emails.send(params)
        return {"success": True, "email_id": email.get("id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
