"""MCP Server — exposes DB tools, RAG tools, resources, and prompts.

Run standalone via: python -m app.mcp_server
The FastAPI backend connects to this process over stdio transport.
"""
import json
import os
import sys
from typing import Any, Dict, List

# ensure project root on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp.server.fastmcp import FastMCP
from sqlalchemy import func

from app.database import SessionLocal
from app.models import User, Product, Order, OrderItem, Review
from app.rag import search_docs

mcp = FastMCP(
    name="shop-mcp",
    instructions="E-commerce MCP server. Use tools to query the shop database and docs.",
)


# -------------------- TOOLS --------------------

@mcp.tool()
def list_users(limit: int = 20) -> List[Dict[str, Any]]:
    """List users in the database. Returns id, name, email, country, joined_at."""
    db = SessionLocal()
    try:
        rows = db.query(User).limit(limit).all()
        return [{"id": u.id, "name": u.name, "email": u.email,
                 "country": u.country, "joined_at": str(u.joined_at)} for u in rows]
    finally:
        db.close()


@mcp.tool()
def get_user_orders(user_id: int) -> Dict[str, Any]:
    """Get all orders for a specific user, including order items and product names."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": f"User {user_id} not found"}
        orders = []
        for o in user.orders:
            items = []
            for it in o.items:
                items.append({
                    "product": it.product.name if it.product else "?",
                    "quantity": it.quantity,
                    "unit_price": it.unit_price,
                    "line_total": it.quantity * it.unit_price,
                })
            orders.append({
                "order_id": o.id, "total": o.total, "status": o.status,
                "created_at": str(o.created_at), "items": items,
            })
        return {"user": {"id": user.id, "name": user.name, "email": user.email},
                "orders": orders, "total_spent": sum(o["total"] for o in orders)}
    finally:
        db.close()


@mcp.tool()
def search_products(query: str = "", category: str = "", limit: int = 10) -> List[Dict[str, Any]]:
    """Search products by name substring and/or category."""
    db = SessionLocal()
    try:
        q = db.query(Product)
        if query:
            q = q.filter(Product.name.ilike(f"%{query}%"))
        if category:
            q = q.filter(Product.category.ilike(f"%{category}%"))
        rows = q.limit(limit).all()
        return [{"id": p.id, "name": p.name, "category": p.category,
                 "price": p.price, "stock": p.stock} for p in rows]
    finally:
        db.close()


@mcp.tool()
def get_product_reviews(product_id: int) -> Dict[str, Any]:
    """Get reviews for a product plus average rating."""
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return {"error": f"Product {product_id} not found"}
        reviews = db.query(Review).filter(Review.product_id == product_id).all()
        avg = sum(r.rating for r in reviews) / len(reviews) if reviews else None
        return {
            "product": {"id": product.id, "name": product.name},
            "average_rating": round(avg, 2) if avg else None,
            "review_count": len(reviews),
            "reviews": [{"rating": r.rating, "comment": r.comment,
                         "created_at": str(r.created_at)} for r in reviews],
        }
    finally:
        db.close()


@mcp.tool()
def get_revenue_stats() -> Dict[str, Any]:
    """Aggregate revenue statistics: total revenue, order count, avg order value, top products."""
    db = SessionLocal()
    try:
        total_revenue = db.query(func.sum(Order.total)).scalar() or 0.0
        order_count = db.query(func.count(Order.id)).scalar()
        avg_order = total_revenue / order_count if order_count else 0.0

        top_products = (
            db.query(Product.name, func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"))
            .join(OrderItem, OrderItem.product_id == Product.id)
            .group_by(Product.id, Product.name)
            .order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc())
            .limit(5).all()
        )
        return {
            "total_revenue": round(total_revenue, 2),
            "order_count": order_count,
            "avg_order_value": round(avg_order, 2),
            "top_products": [{"name": n, "revenue": round(r, 2)} for n, r in top_products],
        }
    finally:
        db.close()


@mcp.tool()
def top_customers(limit: int = 5) -> List[Dict[str, Any]]:
    """Get customers ranked by total spending."""
    db = SessionLocal()
    try:
        rows = (
            db.query(User.id, User.name, User.email, func.sum(Order.total).label("total_spent"))
            .join(Order, Order.user_id == User.id)
            .group_by(User.id, User.name, User.email)
            .order_by(func.sum(Order.total).desc())
            .limit(limit).all()
        )
        return [{"id": u.id, "name": u.name, "email": u.email,
                 "total_spent": round(float(u.total_spent), 2)} for u in rows]
    finally:
        db.close()


@mcp.tool()
def search_docs(query: str, limit: int = 4) -> List[Dict[str, Any]]:
    """Semantic search over product documentation and policies (RAG)."""
    return search_docs(query, k=limit)


# -------------------- RESOURCES --------------------

@mcp.resource("schema://database")
def db_schema() -> str:
    """Return the database schema as a readable description."""
    return (
        "Tables:\n"
        "- users(id, name, email, country, joined_at)\n"
        "- products(id, name, category, price, stock, description)\n"
        "- orders(id, user_id FK users, total, status, created_at)\n"
        "- order_items(id, order_id FK orders, product_id FK products, quantity, unit_price)\n"
        "- reviews(id, product_id FK products, user_id FK users, rating 1-5, comment, created_at)\n"
    )


@mcp.resource("stats://summary")
def stats_summary() -> str:
    """Quick summary counts of the database."""
    db = SessionLocal()
    try:
        return (
            f"users: {db.query(func.count(User.id)).scalar()}, "
            f"products: {db.query(func.count(Product.id)).scalar()}, "
            f"orders: {db.query(func.count(Order.id)).scalar()}, "
            f"reviews: {db.query(func.count(Review.id)).scalar()}"
        )
    finally:
        db.close()


@mcp.resource("catalog://products")
def product_catalog() -> str:
    """Return a lightweight catalog (id, name, category, price) of all products."""
    db = SessionLocal()
    try:
        rows = db.query(Product).all()
        return json.dumps([{"id": p.id, "name": p.name, "category": p.category,
                            "price": p.price} for p in rows])
    finally:
        db.close()


# -------------------- PROMPTS --------------------

@mcp.prompt()
def customer_report(user_id: int) -> str:
    """Generate a full customer analysis report."""
    return (
        f"Produce a detailed customer report for user_id={user_id}. "
        "Use get_user_orders to retrieve their order history, then summarize: "
        "lifetime value, most-purchased category, recency of last order, "
        "and any upsell/cross-sell recommendations."
    )


@mcp.prompt()
def order_summary(order_id: int) -> str:
    """Summarize a single order."""
    return (
        f"Summarize order #{order_id}: list items with totals, "
        "compute the overall value, and suggest one relevant product the "
        "customer may want to buy next."
    )


if __name__ == "__main__":
    mcp.run()
