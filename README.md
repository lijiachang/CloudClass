# CloudClass 网络教学平台

基于 `Django 4.2 + MySQL 8.0 + Django Templates` 的课程作业型网络教学平台，包含学生、教师、管理员三类角色，覆盖课程管理、资料共享、作业提交与批改、讨论答疑、公告 Banner、课程标签、个性化推荐、收藏浏览行为和增强数据统计。

## 技术栈

- Python 3.13
- Django 4.2
- MySQL 8.0
- Django Templates + Bootstrap 5
- mysqlclient / Pillow / python-dotenv

## 已实现模块

- 账号体系：自定义用户模型、登录、退出、学生注册、个人信息维护
- 课程模块：课程分类、课程创建、课程加入、课程详情
- 课程发现：关键词搜索、分类筛选、标签筛选、热门榜、新课展示、推荐中心
- 推荐能力：基于浏览、收藏、选课标签和热度的规则推荐
- 学习行为：课程浏览记录、课程收藏、最近浏览、我的收藏
- 教学资料：文档/视频/外链资料上传与展示
- 作业模块：作业发布、学生提交、教师批改
- 讨论模块：课程发帖、评论回复、帖子删除
- 平台内容：公告、Banner
- 数据统计：学生、教师、管理员三类工作台统计卡片、热门课程和标签分布
- 演示数据：一键初始化管理员、教师、多名学生及 10 门样例课程

## 快速启动

1. 创建虚拟环境并安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. 复制环境变量文件并按需修改数据库配置：

```bash
cp .env.example .env
```

默认 `.env.example` 使用 SQLite，若要切换到 MySQL 8.0，请将：

```env
DB_ENGINE=mysql
DB_NAME=cloudclass
DB_USER=root
DB_PASSWORD=你的密码
DB_HOST=127.0.0.1
DB_PORT=3306
```

3. 执行迁移并初始化演示数据：

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo
```

4. 启动项目：

```bash
python manage.py runserver
```

访问地址：`http://127.0.0.1:8000/`

## 演示账号

- 管理员：`admin / admin123456`
- 教师：`teacher01 / teacher123456`
- 学生：`student01 / student123456`

## 目录说明

- `accounts`：用户、登录注册、权限控制
- `courses`：课程与选课
- `resources`：教学资料
- `assignments`：作业与提交记录
- `discussions`：讨论答疑
- `core`：首页、工作台、公告、Banner、演示数据命令
