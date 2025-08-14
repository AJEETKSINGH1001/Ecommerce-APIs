# 🛒 MyShop API

A complete **Ecommerce-APIs** with authentication, product management, cart, checkout, and invoice generation.

---

## 🚀 Features
- **User Authentication** (Signup & Signin using JWT)
- **Product Management**
  - Add, update, delete products
  - List all products
- **Shopping Cart**
  - Add items to cart
  - View cart
- **Checkout**
  - Place orders from cart
- **Invoice Generation** (PDF)
- **Order History** for users

---

## 📂 Project Structure
```

fastapi\_ecommerce\_api/
├── .venv/                  # Virtual environment
├── invoices/               # Generated PDF invoices
│   ├── invoice\_order\_1.pdf
│   ├── invoice\_order\_2.pdf
├── ecommerce\_api.zip       # API packaged as zip (optional)
├── main.py                  # FastAPI app entry point
├── requirements.txt         # Python dependencies
├── shop.db                  # SQLite database

````

---

## 🛠 Installation & Local Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/myshop-api.git
cd myshop-api
````

### 2️⃣ Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate   # On Mac/Linux
venv\Scripts\activate      # On Windows
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Run the API locally

```bash
uvicorn main:app --reload
```

Server will start at:

```
http://127.0.0.1:8000
```

Swagger UI Docs:

```
http://127.0.0.1:8000/docs
```

---

## 🔑 Authentication

This API uses **JWT tokens**.

### Steps to authenticate in Swagger UI:

1. **Sign Up** using `/auth/signup`.
2. **Sign In** using `/auth/login` to get your token.
3. In Swagger UI, click **Authorize** and paste:

   ```
   Bearer YOUR_TOKEN_HERE
   ```
4. You can now call protected endpoints.

---

## 📌 Usage Examples (via `curl`)

### **A) Sign up**

```bash
curl -X POST http://127.0.0.1:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"secret123","full_name":"You"}'
```

### **B) Sign in** *(OAuth2 expects `username` field)*

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=you@example.com&password=secret123"
```

Copy `"access_token"` from the response.

In Swagger UI, click **Authorize** and paste:

```
Bearer YOUR_TOKEN_HERE
```

---

### **C) Create a product** *(requires Bearer token)*

```bash
curl -X POST http://127.0.0.1:8000/products \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"name":"Phone Case","price":9.99,"currency":"USD","stock":50,"description":"Matte black"}'
```

---

### **D) Product operations**

**List:**

```bash
curl http://127.0.0.1:8000/products
```

**Get by ID:**

```bash
curl http://127.0.0.1:8000/products/1
```

**Update (auth):**

```bash
curl -X PUT http://127.0.0.1:8000/products/1 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"name":"Phone Case Pro","price":12.49,"currency":"USD","stock":40,"description":"Matte black, reinforced"}'
```

**Delete (auth):**

```bash
curl -X DELETE http://127.0.0.1:8000/products/1 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

### **E) Cart operations**

**Add two of product 1:**

```bash
curl -X POST http://127.0.0.1:8000/cart/add \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"product_id":1,"quantity":2}'
```

**View cart:**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" http://127.0.0.1:8000/cart
```

**Update quantity (cart item ID 1 → qty 3):**

```bash
curl -X PUT http://127.0.0.1:8000/cart/1 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"quantity":3}'
```

**Remove cart item:**

```bash
curl -X DELETE http://127.0.0.1:8000/cart/1 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

### **F) Checkout → creates order + PDF invoice**

```bash
curl -X POST http://127.0.0.1:8000/checkout \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

The response includes:

```
"invoice_url": "/orders/1/invoice"
```

---

### **G) Orders & ordered products**

**List my orders:**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" http://127.0.0.1:8000/orders
```

**Order detail:**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" http://127.0.0.1:8000/orders/1
```

**Flattened list of all products you've ordered:**

```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" http://127.0.0.1:8000/orders/items
```

---

### **H) Download invoice (PDF)**

Open in browser:

```
http://127.0.0.1:8000/orders/1/invoice
```

---

## 📜 License

This project is licensed under the MIT License.

```

---

I also noticed you have **`shop.db`** in the root, so this README now makes it clear you’re using **SQLite** as your database.  

If you want, I can add a **"Database Schema"** diagram to the README so people know the tables & relationships without opening the DB file. That would make it even more professional.  
Do you want me to add that?
```
