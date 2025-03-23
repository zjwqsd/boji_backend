from sqlalchemy import Column, Integer, String, Float,BigInteger,Boolean,UniqueConstraint
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.database import Base
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, ForeignKey, Boolean, DateTime, func
from sqlalchemy.orm import relationship


class SuperAdmin(Base):
    __tablename__ = "super_admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # 存储哈希后的密码

# class DataItem(Base):
#     __tablename__ = "data_items"

#     id = Column(Integer, primary_key=True, index=True, autoincrement=True)
#     name = Column(String(255), index=True)
#     description = Column(String(255))
#     price = Column(Float)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)  # 数据库ID
    user_id = Column(String(50), unique=True, nullable=True)  # 可由系统或管理员分配的唯一 ID
    nickname = Column(String(100), nullable=True)  # 必填昵称，不唯一
    realname = Column(String(100),  nullable=True)  # 用户真实姓名，选填
    address = Column(String(255), nullable=True)  # 可选地址
    company = Column(String(255), nullable=True)  # 可选公司
    phone = Column(String(20), nullable=True)  # 可选电话
    email = Column(String(100), unique=True, nullable=True)  # 必须有邮箱，唯一
    password = Column(String(255), nullable=False)  # 存储哈希密码
    email_verified = Column(Boolean, default=False)  # 邮箱是否验证
    is_sub_user = Column(Boolean, default=False)  # 是否为附属用户
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 关联普通用户（仅附属用户有效）
    parent_user = relationship("User", remote_side=[id], backref="sub_users")  # 允许主用户访问附属用户列表
    __table_args__ = (UniqueConstraint("user_id", name="unique_user_id"),)  # 确保 user_id 唯一


class PDFItem(Base):
    __tablename__ = "pdf_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    custom_id = Column(String(50), nullable=False, unique=True)  # 用户填写的编号
    title = Column(String(255), nullable=False)
    category1 = Column(String(100), nullable=False)  # 一级分类
    category2 = Column(String(100), nullable=False)  # 二级分类
    
    household_name = Column(String(100), ForeignKey("households.name"), nullable=True)
    household = relationship("Household", backref="pdf_items", primaryjoin="PDFItem.household_name==Household.name")

    location = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)
    # year = Column(Integer, nullable=True)
    shape = Column(String(100), nullable=False)
    year = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    pdf_path = Column(String(255), nullable=False)  # PDF 文件存储路径
    cover_path = Column(String(255), nullable=True)  # 封面图片存储路径

class SuperAdminSession(Base):
    __tablename__ = "super_admin_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("super_admins.id"), nullable=False)
    session_id = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=10))  # 10 分钟有效

class UserPDFPermission(Base):
    __tablename__ = "user_pdf_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 关联用户
    pdf_id = Column(Integer, ForeignKey("pdf_items.id"), nullable=False)  # 关联 PDFItem
    has_access = Column(Boolean, default=True)  # 是否有访问权限
    created_at = Column(DateTime, default=func.now())  # 记录创建时间

    user = relationship("User", backref="pdf_permissions")
    pdf_item = relationship("PDFItem", backref="user_permissions")

class UserCategoryPermission(Base):
    __tablename__ = "user_category_permissions"
    # 仅仅记录对三种一级分类的权限
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 关联用户
    access1 = Column(Boolean, default=True)  
    access2 = Column(Boolean, default=True)  
    access3 = Column(Boolean, default=True)  
    created_at = Column(DateTime, default=func.now())  # 记录创建时间

    user = relationship("User", backref="category_permissions")
    
    
class Household(Base):
    __tablename__ = "households"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False,unique=True)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=True)

    category2 = Column(String(100), nullable=False)  # 指定归属的二级分类