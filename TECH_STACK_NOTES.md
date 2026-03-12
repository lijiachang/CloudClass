# CloudClass 技术组件说明

本文档介绍项目中使用的以下组件：

- Django Templates + Bootstrap 5
- Pillow
- python-dotenv

## 1. Django Templates + Bootstrap 5

### 作用
- `Django Templates` 负责服务端页面渲染，处理模板继承、循环、条件判断、URL 反向解析等。
- `Bootstrap 5` 负责页面样式和常用交互组件（导航栏、按钮、表单、提醒框、响应式布局等）。

### 在本项目中的落地
- Django 模板引擎配置在 `config/settings.py`：
  - `BACKEND` 使用 `django.template.backends.django.DjangoTemplates`
  - `DIRS` 指向项目级 `templates/`
  - `APP_DIRS=True` 支持各 app 内模板自动发现
- 全站基础模板在 `templates/base.html`，通过 `{% block %}` 提供统一布局。
- Bootstrap 5 通过 CDN 引入：
  - CSS：`bootstrap@5.3.3/dist/css/bootstrap.min.css`
  - JS：`bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js`
- 各业务页面（课程、作业、讨论、登录注册等）基于基础模板扩展，实现一致的 UI 风格。

### 优势
- 开发效率高：后端渲染和前端样式开箱即用。
- 维护成本低：统一模板结构，页面改版可集中在基础模板完成。
- 响应式支持完善：兼容桌面端与移动端。

## 2. Pillow

### 作用
- `Pillow` 是 Python 图像处理库，Django 在处理 `ImageField` 时依赖它完成图片格式识别和基础处理。

### 在本项目中的落地
- 依赖声明在 `requirements.txt`：`Pillow==12.1.1`
- 项目中多个模型使用了 `ImageField`（需要 Pillow 支持），例如：
  - 用户头像：`accounts/models.py` 中 `avatar`
  - 课程封面：`courses/models.py` 中 `cover`
  - Banner 图片：`core/models.py` 中 `image`
- 媒体文件配置在 `config/settings.py`：
  - `MEDIA_URL = "/media/"`
  - `MEDIA_ROOT = BASE_DIR / "media"`
- 开发环境通过 `config/urls.py` 中 `static(..., document_root=settings.MEDIA_ROOT)` 提供媒体文件访问。

### 优势
- 与 Django 文件上传体系无缝配合。
- 满足教学平台对头像、课程封面、Banner 等图片上传需求。

## 3. python-dotenv

### 作用
- `python-dotenv` 用于从 `.env` 文件加载环境变量，分离配置与代码，便于不同环境切换（开发/测试/生产）。

### 在本项目中的落地
- 依赖声明在 `requirements.txt`：`python-dotenv==1.2.2`
- 在 `config/settings.py` 中加载：
  - `from dotenv import load_dotenv`
  - `load_dotenv(BASE_DIR / ".env")`
- 使用 `os.getenv(...)` 读取关键配置：
  - Django 基础配置：`SECRET_KEY`、`DEBUG`、`ALLOWED_HOSTS`
  - 数据库配置：`DB_ENGINE`、`DB_NAME`、`DB_USER`、`DB_PASSWORD`、`DB_HOST`、`DB_PORT`
- 项目通过 `.env.example` 提供示例，支持 SQLite 与 MySQL 的快速切换。

### 优势
- 降低敏感信息硬编码风险。
- 部署更灵活，同一份代码可适配多环境配置。

## 小结

这三项组件在本项目中形成了清晰分工：
- `Django Templates + Bootstrap 5`：页面渲染与界面呈现
- `Pillow`：图片字段与媒体资源能力
- `python-dotenv`：环境配置管理与部署灵活性
