# main.py
# A complete FastAPI e-commerce style API:
# - User signup/signin with JWT
# - Product CRUD
# - Cart management
# - Checkout -> Order + PDF Invoice
# - List orders and ordered products
#
# Run:
#   uvicorn main:app --reload
#
# Swagger docs: http://127.0.0.1:8000/docs

import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field

from jose import JWTError, jwt
from passlib.context import CryptContext

from sqlalchemy import (
    Column, Integer, String, Text, Float, ForeignKey, DateTime, create_engine, func
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

# ---------------------------
# Configuration
# ---------------------------
SECRET_KEY = os.environ.get("JWT_SECRET", "change_this_in_production_" + uuid.uuid4().hex)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./shop.db")
INVOICE_DIR = os.environ.get("INVOICE_DIR", "./invoices")
os.makedirs(INVOICE_DIR, exist_ok=True)

# ---------------------------
# DB setup
# ---------------------------
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------------------
# Models (SQLAlchemy)
# ---------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    carts = relationship("CartItem", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    sku = Column(String, unique=True, index=True, nullable=True)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    order_items = relationship("OrderItem", back_populates="product", cascade="all, delete")


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="carts")
    product = relationship("Product")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    status = Column(String, default="PAID")  # simple flow
    created_at = Column(DateTime, server_default=func.now())
    invoice_path = Column(String, nullable=True)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    name_snapshot = Column(String, nullable=False)
    unit_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    subtotal = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

# ---------------------------
# Security / Auth helpers
# ---------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

# ---------------------------
# Schemas (Pydantic v2)
# ---------------------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str = Field(min_length=6)

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True  # for ORM

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    currency: str = "USD"
    sku: Optional[str] = None
    stock: int = 0

class ProductOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    currency: str
    sku: Optional[str] = None
    stock: int
    created_at: datetime
    class Config:
        from_attributes = True

class CartAdd(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, default=1)

class CartItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    unit_price: float
    quantity: int
    subtotal: float

class CheckoutOut(BaseModel):
    order_id: int
    total_amount: float
    currency: str
    invoice_url: str

class OrderItemOut(BaseModel):
    product_id: int
    name_snapshot: str
    unit_price: float
    quantity: int
    subtotal: float

class OrderOut(BaseModel):
    id: int
    total_amount: float
    currency: str
    status: str
    created_at: datetime
    items: List[OrderItemOut]

class OrderedProductOut(BaseModel):
    order_id: int
    product_id: int
    name_snapshot: str
    unit_price: float
    quantity: int
    subtotal: float

# ---------------------------
# App init & DB create
# ---------------------------
app = FastAPI(title="Ecommerce API", version="1.0.0")
Base.metadata.create_all(bind=engine)

# ---------------------------
# Auth routes
# ---------------------------
@app.post("/auth/signup", response_model=UserOut, status_code=201)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 spec uses 'username' field; we treat it as email
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

# ---------------------------
# Product routes (CRUD)
# ---------------------------
@app.post("/products", response_model=ProductOut, status_code=201)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = Product(**product.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

@app.get("/products", response_model=List[ProductOut])
def list_products(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Product).offset(skip).limit(limit).all()

@app.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    return p

@app.put("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    for k, v in product.model_dump().items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p

@app.delete("/products/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    db.delete(p)
    db.commit()
    return None

# ---------------------------
# Cart routes
# ---------------------------
@app.post("/cart/add", response_model=CartItemOut, status_code=201)
def add_to_cart(
    item: CartAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.get(Product, item.product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    if product.stock is not None and item.quantity > product.stock:
        raise HTTPException(400, "Not enough stock")

    existing = (
        db.query(CartItem)
        .filter(CartItem.user_id == current_user.id, CartItem.product_id == item.product_id)
        .first()
    )
    if existing:
        existing.quantity += item.quantity
        db.commit()
        db.refresh(existing)
        cart_item = existing
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=item.product_id, quantity=item.quantity)
        db.add(cart_item)
        db.commit()
        db.refresh(cart_item)

    return CartItemOut(
        id=cart_item.id,
        product_id=product.id,
        product_name=product.name,
        unit_price=product.price,
        quantity=cart_item.quantity,
        subtotal=product.price * cart_item.quantity,
    )

@app.get("/cart", response_model=List[CartItemOut])
def view_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(CartItem).filter(CartItem.user_id == current_user.id).all()
    result = []
    for ci in items:
        result.append(CartItemOut(
            id=ci.id,
            product_id=ci.product_id,
            product_name=ci.product.name,
            unit_price=ci.product.price,
            quantity=ci.quantity,
            subtotal=ci.product.price * ci.quantity,
        ))
    return result

@app.put("/cart/{item_id}", response_model=CartItemOut)
def update_cart_item(
    item_id: int,
    quantity: int = Body(embed=True, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ci = db.get(CartItem, item_id)
    if not ci or ci.user_id != current_user.id:
        raise HTTPException(404, "Cart item not found")
    product = db.get(Product, ci.product_id)
    if product.stock is not None and quantity > product.stock:
        raise HTTPException(400, "Not enough stock")
    ci.quantity = quantity
    db.commit()
    db.refresh(ci)
    return CartItemOut(
        id=ci.id,
        product_id=ci.product_id,
        product_name=product.name,
        unit_price=product.price,
        quantity=ci.quantity,
        subtotal=product.price * ci.quantity,
    )

@app.delete("/cart/{item_id}", status_code=204)
def remove_cart_item(item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ci = db.get(CartItem, item_id)
    if not ci or ci.user_id != current_user.id:
        raise HTTPException(404, "Cart item not found")
    db.delete(ci)
    db.commit()
    return None

@app.delete("/cart", status_code=204)
def clear_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    db.commit()
    return None

# ---------------------------
# Checkout + Invoice
# ---------------------------
def generate_invoice_pdf(order: Order) -> str:
    """Create a simple PDF invoice and return file path."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    filename = f"invoice_order_{order.id}.pdf"
    path = os.path.join(INVOICE_DIR, filename)

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "INVOICE")
    y -= 30

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Order ID: {order.id}")
    y -= 15
    c.drawString(50, y, f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 15
    c.drawString(50, y, f"Customer: {order.user.email}")
    y -= 25

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Item")
    c.drawString(300, y, "Qty")
    c.drawString(350, y, "Unit Price")
    c.drawString(450, y, "Subtotal")
    y -= 15
    c.line(50, y, 550, y)
    y -= 10

    c.setFont("Helvetica", 10)
    for it in order.items:
        c.drawString(50, y, it.name_snapshot[:40])
        c.drawRightString(330, y, str(it.quantity))
        c.drawRightString(430, y, f"{order.currency} {it.unit_price:.2f}")
        c.drawRightString(530, y, f"{order.currency} {it.subtotal:.2f}")
        y -= 18
        if y < 80:
            c.showPage()
            y = height - 50

    y -= 10
    c.line(50, y, 550, y)
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(530, y, f"Total: {order.currency} {order.total_amount:.2f}")
    c.showPage()
    c.save()
    return path

@app.post("/checkout", response_model=CheckoutOut)
def checkout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cart_items = db.query(CartItem).filter(CartItem.user_id == current_user.id).all()
    if not cart_items:
        raise HTTPException(400, "Cart is empty")

    # Validate stock and compute total
    total = 0.0
    currency = "USD"
    for ci in cart_items:
        product = db.get(Product, ci.product_id)
        if product.stock is not None and ci.quantity > product.stock:
            raise HTTPException(400, f"Not enough stock for {product.name}")
        total += product.price * ci.quantity
        currency = product.currency or currency

    # Create order
    order = Order(user_id=current_user.id, total_amount=total, currency=currency, status="PAID")
    db.add(order)
    db.commit()
    db.refresh(order)

    # Create order items, reduce stock
    for ci in cart_items:
        product = db.get(Product, ci.product_id)
        oi = OrderItem(
            order_id=order.id,
            product_id=product.id,
            name_snapshot=product.name,
            unit_price=product.price,
            quantity=ci.quantity,
            subtotal=product.price * ci.quantity,
        )
        db.add(oi)
        if product.stock is not None:
            product.stock = max(0, product.stock - ci.quantity)
    db.commit()
    db.refresh(order)

    # Clear cart
    db.query(CartItem).filter(CartItem.user_id == current_user.id).delete()
    db.commit()

    # Ensure relationship is loaded, then create invoice
    order = db.get(Order, order.id)
    _ = order.items
    invoice_path = generate_invoice_pdf(order)
    order.invoice_path = invoice_path
    db.commit()
    db.refresh(order)

    return CheckoutOut(
        order_id=order.id,
        total_amount=order.total_amount,
        currency=order.currency,
        invoice_url=f"/orders/{order.id}/invoice"
    )

# ---------------------------
# Orders
# ---------------------------
@app.get("/orders", response_model=List[OrderOut])
def list_orders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    orders = (
        db.query(Order)
        .filter(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    result: List[OrderOut] = []
    for o in orders:
        result.append(OrderOut(
            id=o.id,
            total_amount=o.total_amount,
            currency=o.currency,
            status=o.status,
            created_at=o.created_at,
            items=[
                OrderItemOut(
                    product_id=it.product_id,
                    name_snapshot=it.name_snapshot,
                    unit_price=it.unit_price,
                    quantity=it.quantity,
                    subtotal=it.subtotal,
                ) for it in o.items
            ],
        ))
    return result

@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    o = db.get(Order, order_id)
    if not o or o.user_id != current_user.id:
        raise HTTPException(404, "Order not found")
    return OrderOut(
        id=o.id,
        total_amount=o.total_amount,
        currency=o.currency,
        status=o.status,
        created_at=o.created_at,
        items=[
            OrderItemOut(
                product_id=it.product_id,
                name_snapshot=it.name_snapshot,
                unit_price=it.unit_price,
                quantity=it.quantity,
                subtotal=it.subtotal,
            ) for it in o.items
        ],
    )

@app.get("/orders/{order_id}/invoice")
def download_invoice(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    o = db.get(Order, order_id)
    if not o or o.user_id != current_user.id:
        raise HTTPException(404, "Order not found")
    if not o.invoice_path or not os.path.exists(o.invoice_path):
        raise HTTPException(404, "Invoice not found")
    return FileResponse(path=o.invoice_path, filename=os.path.basename(o.invoice_path), media_type="application/pdf")

@app.get("/orders/items", response_model=List[OrderedProductOut])
def list_ordered_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Flattened list of all products you've ever ordered."""
    orders = db.query(Order).filter(Order.user_id == current_user.id).all()
    flat: List[OrderedProductOut] = []
    for o in orders:
        for it in o.items:
            flat.append(OrderedProductOut(
                order_id=o.id,
                product_id=it.product_id,
                name_snapshot=it.name_snapshot,
                unit_price=it.unit_price,
                quantity=it.quantity,
                subtotal=it.subtotal,
            ))
    return flat

# ---------------------------
# Root
# ---------------------------
@app.get("/")
def root():
    return {"message": "Ecommerce API is running. See /docs for interactive API docs."}
