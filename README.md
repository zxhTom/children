# children

Children 成长日记与家庭健康记录系统。记录儿童成长过程、多视角家庭日记、音视频照片素材管理与体检健康跟踪。

## 技术架构

- **后端**: FastAPI + SQLite (SQLAlchemy ORM)
- **前端**: 原生 HTML / JavaScript / CSS，位于 `backend/static/index.html`。
- **说明**: 根目录下的 `frontend` 为空目录，不作为前端组件打包或独立同步。
- **AI 模块**: 当前代码中的 AI summary 与体检分析模块为模板与关键词占位模拟，未实际接入外部商业大模型。

## 运行环境与启动方式

### 1. 依赖安装

```bash
pip install -r backend/requirements.txt
```

### 2. 运行后端服务

运行时的工作目录**必须**在 `backend` 目录下：

```bash
# 方式一：使用启动脚本
bash run_backend.sh

# 方式二：手动运行
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8088
```

> [!NOTE]
> 启动脚本实际监听地址为 `--host 0.0.0.0 --port 8088`，服务不仅在回环地址可用，局域网同网段设备亦可访问。

## 数据隐私与存储说明

- 本地 SQLite 数据库（`backend/children_diary.db`）以及照片、音频等上传素材（`backend/uploads/`）属于家庭隐私数据，受 `.gitignore` 保护，**不进入代码仓库，亦不参与此次代码同步**。
- 首次在全新环境启动服务时，FastAPI 应用会自动在工作目录下创建全新的空数据库表结构，本次代码检出与发布不启动应用。
