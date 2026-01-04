from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

# Указываем папку, где лежат html
templates = Jinja2Templates(directory="app/templates")

router = APIRouter(tags=["Frontend"])

@router.get("/webapp")
async def get_webapp_page(request: Request):
 
    return templates.TemplateResponse(
        name="index.html",   
        context={"request": request, "title": "Ustabar Map"} # Переменные для шаблона
    )