from fastapi import FastAPI, HTTPException, Request, Depends, Form
from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 1. Настройка базы данных Postgres
DATA_BASE_URL = "postgresql://postgres:12345678@localhost:5432/market"

engine = create_engine(DATA_BASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Модель таблицы в БД
class ProductModel(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    stock = Column(Integer)
    image_url = Column(String, default="https://via.placeholder.com/150")

# Создаем таблицу, если её еще нет
Base.metadata.create_all(bind=engine)

# 3. Pydantic модель (для API)
class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int

# 4. Зависимость для подключения к БД
def get_db():
    db = SessionLocal()
    try:
        yield db 
    finally:
        db.close()

# --- ЭНДПОИНТЫ ---

# ГЛАВНАЯ СТРАНИЦА (Витрина + Поиск)
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, search: str = None, db: Session = Depends(get_db)):
    query = db.query(ProductModel)
    if search:
        # icontains делает поиск нечувствительным к регистру
        query = query.filter(ProductModel.name.icontains(search))
    products = query.all()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "products": products, 
        "search_query": search or ""
    })

# ПОКУПКА ТОВАРА (Шаг 2)
@app.post("/buy/{product_id}")
async def buy_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(ProductModel).filter(ProductModel.id == product_id).first()
    if product and product.stock > 0:
        product.stock -= 1
        db.commit()
    return RedirectResponse(url="/", status_code=303)

# АДМИНКА: ДОБАВЛЕНИЕ (Шаг 3)
@app.post("/admin/add")
async def add_product_admin(
    name: str = Form(...), 
    price: float = Form(...), 
    stock: int = Form(...), 
    db: Session = Depends(get_db)
):
    new_product = ProductModel(name=name, price=price, stock=stock)
    db.add(new_product)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

# API для получения списка (для тестов)
@app.get("/api/products")
async def get_products_api(db: Session = Depends(get_db)):
    return db.query(ProductModel).all()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)