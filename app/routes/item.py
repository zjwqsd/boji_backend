from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi import Depends, Header
from app.utils import verify_super_admin
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import PDFItem
from typing import List, Optional
from pydantic import BaseModel

import shutil
import os
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from app.database import get_db
from app.models import PDFItem

from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

router = APIRouter(prefix="/item", tags=["Item"])

UPLOAD_FOLDER = "uploads/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # 确保目录存在


# 🔹 定义请求体（使用数据库 `id`）
class BatchPreviewRequest(BaseModel):
    ids: List[int]  # 接收整数数组

# 🔹 定义修改商品的请求体
class UpdateItemRequest(BaseModel):
    title: Optional[str] = None
    category1: Optional[str] = None
    category2: Optional[str] = None
    category3: Optional[str] = None
    keywords: Optional[str] = None
    description: Optional[str] = None
    shape: Optional[str] = None
    year: Optional[int] = None
    price: Optional[float] = None





# 🔹 需要超级用户权限的依赖项
# 🔹 依赖项：检查是否是超级用户
def super_admin_auth(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="认证失败，缺少 Bearer 令牌")
    
    token = authorization.split(" ")[1]
    return verify_super_admin(token)  # 验证超级用户身份
# 🔹 上传完整商品信息 + PDF



@router.post("/upload")
def upload_item(
    file: UploadFile = File(...),
    custom_id: str = Form(...),
    title: str = Form(...),
    category1: str = Form(...),
    category2: str = Form(...),
    category3: str = Form(...),
    keywords: str = Form(...),
    description: str = Form(...),
    shape: str = Form(...),
    year: int = Form(...),
    price: float = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(super_admin_auth)
):
    # 1️⃣ 检查 `custom_id` 是否唯一
    existing_item = db.query(PDFItem).filter(PDFItem.custom_id == custom_id).first()
    if existing_item:
        raise HTTPException(status_code=400, detail="编号已存在")

    # 2️⃣ 生成新的文件名（使用 custom_id）
    file_extension = file.filename.split(".")[-1]  # 获取原始文件扩展名
    new_filename = f"{custom_id}.{file_extension}"  # 以 custom_id 作为文件名
    file_path = os.path.join(UPLOAD_FOLDER, new_filename)  # 存储路径
    print(file_path)
    # 3️⃣ 存储 PDF 文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 4️⃣ 存入数据库
    new_pdf = PDFItem(
        custom_id=custom_id,
        title=title,
        category1=category1,
        category2=category2,
        category3=category3,
        keywords=keywords,
        description=description,
        shape=shape,
        year=year,
        price=price,
        pdf_path=file_path  # 存储新路径
    )
    db.add(new_pdf)
    db.commit()
    db.refresh(new_pdf)

    return {
        "message": "商品上传成功"
        # "pdf_id": new_pdf.id,
        # "title": new_pdf.title,
        # "category1": new_pdf.category1,
        # "category2": new_pdf.category2,
        # "file_path": new_pdf.pdf_path  # 确认存储的路径
    }

# 🔹 批量预览商品信息 API
@router.post("/batch-preview", response_model=List[dict])
def batch_preview(request: BatchPreviewRequest, db: Session = Depends(get_db)):
    # 1️⃣ 查询匹配的商品
    items = db.query(PDFItem).filter(PDFItem.id.in_(request.ids)).all()
    
    # 2️⃣ 构造返回数据
    response_data = [
        {
            "id": item.id,
            "custom_id": item.custom_id,  # 仍然可以返回自定义编号
            "title": item.title,
            "category1": item.category1,
            "category2": item.category2,
            "category3": item.category3,
            "keywords": item.keywords,
            "description": item.description,
            "shape": item.shape,
            "year": item.year,
            "price": item.price
        }
        for item in items
    ]

    return response_data

# 🔹 过滤商品 API
@router.get("/filter", response_model=List[int],dependencies=[Depends(RateLimiter(times=7, seconds=10))])
def filter_items(
    category1: str = Query(..., description="一级分类"),
    category2: str = Query(None, description="二级分类，可选"),
    db: Session = Depends(get_db)
):
    # 1️⃣ 基础查询（category1 必填）
    query = db.query(PDFItem).filter(PDFItem.category1 == category1)

    # 2️⃣ 如果提供了 category2，则进一步筛选
    if category2:
        query = query.filter(PDFItem.category2 == category2)

    # 3️⃣ 获取符合条件的商品 ID
    item_ids = [item.id for item in query.all()]

    return item_ids

# 🔹 修改商品信息 API
@router.put("/update/{id}")
def update_item(
    id: int,
    request: UpdateItemRequest,
    db: Session = Depends(get_db),
    admin=Depends(super_admin_auth)
):
    # 1️⃣ 查询商品是否存在
    item = db.query(PDFItem).filter(PDFItem.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 2️⃣ 不能修改 `custom_id` 和 `pdf_path`
    update_data = request.dict(exclude_unset=True)  # 只更新提供的字段
    for key, value in update_data.items():
        setattr(item, key, value)

    # 3️⃣ 提交修改
    db.commit()
    db.refresh(item)

    return {
        "message": "商品信息已更新",
        "updated_item": {
            "id": item.id,
            "custom_id": item.custom_id,  # 仍然返回编号
            "title": item.title,
            "category1": item.category1,
            "category2": item.category2,
            "category3": item.category3,
            "keywords": item.keywords,
            "description": item.description,
            "shape": item.shape,
            "year": item.year,
            "price": item.price
        }
    }

@router.delete("/delete/{id}")
def delete_item(id: int, db: Session = Depends(get_db),admin=Depends(super_admin_auth)):
    item = db.query(PDFItem).filter(PDFItem.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 🔹 删除 PDF 文件（如果文件存在）
    if os.path.exists(item.pdf_path):
        os.remove(item.pdf_path)

    # 🔹 删除数据库记录
    db.delete(item)
    db.commit()

    return {"message": "商品及 PDF 文件已删除", "deleted_id": id}



@router.get("/search",dependencies=[Depends(RateLimiter(times=3, seconds=10))])
def search_pdfs(query: str = Query(..., min_length=1), db: Session = Depends(get_db)) -> List[int]:
    search_term = f"%{query}%"
    results = db.query(PDFItem).filter(
        or_(
            PDFItem.title.ilike(search_term),
            PDFItem.category1.ilike(search_term),
            PDFItem.category2.ilike(search_term),
            PDFItem.keywords.ilike(search_term)
        )
    ).all()

    return [pdf.id for pdf in results]