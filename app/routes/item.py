from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi import Depends, Header
from app.utils import verify_super_admin
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models import PDFItem, Household
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

# from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

router = APIRouter(prefix="/item", tags=["Item"])

UPLOAD_FOLDER = "uploads/"
COVER_FOLDER = "covers/"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # 确保目录存在
os.makedirs(COVER_FOLDER, exist_ok=True)  # 确保目录存在


# 🔹 定义请求体（使用数据库 `id`）
class BatchPreviewRequest(BaseModel):
    ids: List[int]  # 接收整数数组

# 🔹 定义修改商品的请求体
class UpdateItemRequest(BaseModel):
    title: Optional[str] = None
    category1: Optional[str] = None
    category2: Optional[str] = None
    # category3: Optional[str] = None
    household_name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    shape: Optional[str] = None
    year: Optional[str] = None
    price: Optional[float] = None

class HouseholdRequest(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    category2: str






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
    cover: UploadFile = File(None),
    custom_id: str = Form(...),
    title: str = Form(...),
    category1: str = Form(...),
    category2: str = Form(...),
    # category3: str = Form(...),
    household_name: str = Form(None),
    location: str = Form(...),
    description: str = Form(...),
    shape: str = Form(...),
    year: str = Form(...),
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
    cover_path = None
    if cover:
        cover_extension = cover.filename.split(".")[-1]
        cover_filename = f"{custom_id}.{cover_extension}"
        cover_path = os.path.join(COVER_FOLDER, cover_filename)
    print(file_path)
    # 3️⃣ 存储 PDF 文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    if cover:
        with open(cover_path, "wb") as buffer:
            shutil.copyfileobj(cover.file, buffer)
    # 检查household是否存在
    household_id = None
    if household_name:
        household_obj = db.query(Household).filter(Household.name == household_name).first()
        if not household_obj:
            raise HTTPException(status_code=404, detail="归户不存在")
        household_id = household_obj.id
    # 4️⃣ 存入数据库
    new_pdf = PDFItem(
        custom_id=custom_id,
        title=title,
        category1=category1,
        category2=category2,
        # category3=category3,
        household_name=household_name,
        location=location,
        description=description,
        shape=shape,
        year=year,
        price=price,
        pdf_path=file_path,  # 存储新路径
        cover_path=cover_path
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
            # "category3": item.category3,
            "household_name": item.household_name,
            "location": item.location,
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
    category1: str = Query(None, description="一级分类"),
    category2: str = Query(None, description="二级分类，可选"),
    db: Session = Depends(get_db)
):
    # 1️⃣ 基础查询（category1 必填）
    # 如何category1 为空，返回所有的商品
    if not category1:
        items = db.query(PDFItem).all()
        return [item.id for item in items]
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
    # 检查household是否存在
    if request.household_name:
        household_obj = db.query(Household).filter(Household.name == request.household_name).first()
        if not household_obj:
            raise HTTPException(status_code=404, detail="归户不存在")
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
            # "category3": item.category3,
            "household_name": item.household_name,
            "location": item.location,
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
            PDFItem.custom_id.ilike(search_term),
            PDFItem.title.ilike(search_term),
            PDFItem.location.ilike(search_term),
            PDFItem.description.ilike(search_term),
            PDFItem.shape.ilike(search_term),
            PDFItem.year.ilike(search_term),
        )
    ).all()

    return [pdf.id for pdf in results]

@router.post("/create_household")
def create_household(request:HouseholdRequest,db: Session = Depends(get_db),admin=Depends(super_admin_auth)):
    household = Household(
        name=request.name,
        code=request.code,
        description=request.description,
        category2=request.category2
    )
    db.add(household)
    db.commit()
    db.refresh(household)
    return {"message":"归户创建成功","household":household}


@router.get("/households/{category2}")
def get_households(category2: str, db: Session = Depends(get_db)):
    #如何category2 为空，返回所有的归户
    if not category2:
        households = db.query(Household).all()
        return [{"name":household.name,"code":household.code,"description":household.description} for household in households]
    # 从 householde 表中查询 category2 的所有归户
    households = db.query(Household).filter(Household.category2 == category2).all()
    return [{"name":household.name,"code":household.code,"description":household.description} for household in households]

#从户名得到归户
@router.get("/household/{name}")
def get_household(name: str, db: Session = Depends(get_db)):
    household = db.query(Household).filter(Household.name == name).first()
    if not household:
        raise HTTPException(status_code=404, detail="归户不存在")
    return {"name":household.name,"code":household.code,"description":household.description}
    
#更新归户信息
@router.put("/update_household")
def update_household(request: HouseholdRequest, db: Session = Depends(get_db),admin=Depends(super_admin_auth)):
    household = db.query(Household).filter(Household.name==request.name).first()
    if not household:
        raise HTTPException(status_code=404, detail="归户不存在")
    # 更新除了户名以外的信息
    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(household, key, value)
    # 如果更新了category2, 那么更新 PDF 表项中该户名对应的 category2
    if update_data.get("category2"):
        db.query(PDFItem).filter(PDFItem.household_name == request.name).update({"category2":request.category2})
    db.commit()
    db.refresh(household)
    return {"message":"归户信息已更新","household":household}


