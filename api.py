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
from apollo_client import ApolloClient

load_dotenv()

app = FastAPI(title="VYUD AI API", version="1.0.0")
resend.api_key = os.getenv("RESEND_API_KEY")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_SECRET_KEY = os.getenv("VYUD_API_SECRET", "vyud-secret-key-2026")

class AnalyzeRequest(BaseModel):
    url: str
    target_role: Optional[str] = "Decision Maker"
    research_keywords: Optional[str] = ""

class DecisionMaker(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    relevance_reason: str

class AnalyzeResponse(BaseModel):
    company_name: Optional[str]
    industry: Optional[str]
    found_signals: List[str]
    tech_stack: List[str]
    confidence_score: float
    analysis_log: str
    email_draft: str
    decision_maker: Optional[DecisionMaker] = None

class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str

agent = VyudAgent()
writer = VyudWriter()
searcher = PersonSearcher(openai_client=agent.client)
apollo = ApolloClient()

@app.get("/")
async def health_check():
    return {"status": "online", "message": "VYUD AI API is running"}

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_company(request: AnalyzeRequest, x_api_key: str = Header(...)):
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

    try:
        # 1. Анализ компании
        result = agent.analyze_company(url=request.url, research_keywords=request.research_keywords)
        if not result:
            # Возвращаем кастомную ошибку, которую фронтенд сможет красиво показать
            raise HTTPException(status_code=400, detail="Сайт недоступен или заблокировал скрапер. Попробуйте другой URL.")
        
        # 2. Поиск ЛПР
        dm_info = None
        
        # Сначала Apollo
        apollo_res = apollo.search_person(request.url, request.target_role)
        if apollo_res:
            dm_info = DecisionMaker(**apollo_res)
        
        # Затем Agentic Search
        if not dm_info:
            real_dm = searcher.find_decision_maker(result.company_name, request.target_role, company_context=result.analysis_log)
            if real_dm:
                dm_info = DecisionMaker(**real_dm)

        # Если никто не найден - четко об этом пишем
        if not dm_info:
            dm_info = DecisionMaker(
                relevance_reason="Сотрудник не найден автоматически. Рекомендуем ручной поиск в LinkedIn по компании " + (result.company_name or "")
            )
        
        # 3. Генерация письма
        enrichment_data = result.model_dump()
        enrichment_data["target_role"] = request.target_role
        enrichment_data["dm_name"] = dm_info.name if dm_info.name else "Коллега" # В письме допустимо, но в UI покажем как есть
        enrichment_data["research_keywords"] = request.research_keywords
        
        email_draft = writer.generate_email(enrichment_data)
        
        return AnalyzeResponse(
            company_name=result.company_name,
            industry=result.industry,
            found_signals=result.found_signals,
            tech_stack=result.tech_stack,
            confidence_score=result.confidence_score,
            analysis_log=result.analysis_log,
            email_draft=email_draft,
            decision_maker=dm_info
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"💥 Ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Системная ошибка: {str(e)}")

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
