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

@router.get("/webapp/select-service")
async def select_service_page(request: Request):
    # Этот список можно потом брать из базы данных
    services = [
        {"id": "cleaning", "name": "🧹 Клининг"},
        {"id": "electrician", "name": "⚡ Электрик"},
        {"id": "plumber", "name": "🔧 Сантехник"},
        {"id": "nanny", "name": "🧸 Няня"},
        {"id": "tutor", "name": "📚 Репетитор"},
        {"id": "courier", "name": "📦 Курьер"},
    ]
    
    return templates.TemplateResponse(
        name="select_service.html",
        context={
            "request": request,
            "services": services
        }
    )


@router.get("/webapp/order-details")
async def order_details_page(request: Request, service_id: str):
    """
    Страница заполнения деталей заказа.
    service_id передается с прошлой страницы.
    """
    # Варианты времени (можно тоже вынести в настройки или БД)
    time_options = [
        {"value": "2", "label": "2 часа"},
        {"value": "3", "label": "3 часа"},
        {"value": "4", "label": "4 часа"},
        {"value": "5", "label": "5+ часов"},
    ]

    return templates.TemplateResponse(
        name="order_details.html",
        context={
            "request": request,
            "service_id": service_id,
            "time_options": time_options
        }
    )


@router.get("/webapp/map-select")
async def map_select_page(
    request: Request,
    service_id: str,
    duration: str,
    price: int,
    comment: str = ""
):
    """
    Страница карты. Принимает все накопленные данные.
    """
    # Словарь названий для красоты
    service_names = {
        "cleaning": "🧹 Клининг",
        "electrician": "⚡ Электрик",
        "plumber": "🔧 Сантехник",
        # добавьте остальные...
    }
    
    service_name = service_names.get(service_id, service_id)

    return templates.TemplateResponse(
        name="map_select.html",
        context={
            "request": request,
            # Передаем данные, чтобы JS мог их собрать и отправить
            "order_data": {
                "service_id": service_id,
                "service_name": service_name,
                "duration": duration,
                "price": price,
                "comment": comment
            }
        }
    )