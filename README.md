# children

Children 是按儿童成长手册思路设计的家庭记录系统。一个家庭可管理多个宝宝，并把同一段共同经历关联到多个宝宝。

## 主要功能

- 宝宝档案：出生日期、昵称和主题色；顶部可切换单个宝宝或家庭总览。
- 成长手册：按宝宝出生后的月龄翻阅章节，把同阶段的回忆、体检、家庭测量和黄疸观察放在一起；可直接为当前章节生成故事。
- 成长时间轴：图文和音频日记、关键时刻；一条记录可关联多个宝宝，旧版视角记录会尽量自动归档，无法确定归属的记录可手动关联。
- 健康手册：体检单、复查日期、黄疸观察；体检时填写的身高、体重和头围自动进入生长曲线。
- 成长记录：按宝宝查看身高、体重、头围趋势。随访节点由出生日期推算，供家庭记录核对，实际安排以医生和当地儿童保健机构为准。
- 关键时刻与成长故事：从日记关键词提示可标记的关键时刻；按宝宝与日期生成可打印的成长故事，包含共同回忆和该时段的体检、测量摘要。故事只整理已保存的内容，不补写未经记录的事实。

随访节点参考[国家卫生健康委《0～6岁儿童健康管理服务规范》](https://www.nhc.gov.cn/ewebeditor/uploadfile/2017/03/20170329103413888.pdf)。成长记录与提示用于家庭整理，不构成医疗诊断。

## 技术架构

- **后端**: FastAPI + SQLite (SQLAlchemy ORM)
- **前端**: 原生 HTML / JavaScript / CSS，位于 `backend/static/index.html`。
- **说明**: 根目录下的 `frontend` 为空目录，不作为前端组件打包或独立同步。
- **成长故事**: 基于数据库中的真实记录生成结构化手册，可由浏览器打印或保存为 PDF，不依赖外部模型。

## 运行环境与启动方式

### 1. 依赖安装

```bash
pip install -r backend/requirements.txt
```

### 2. 运行后端服务

运行时的工作目录**必须**在 `backend` 目录下：

先设置登录凭据。以下命令生成密码哈希和会话密钥；将输出写入仅服务账号可读的环境文件，勿提交到 Git。

```bash
python3 -c 'from backend.app.auth import hash_password; import getpass; print("AUTH_PASSWORD_HASH=" + hash_password(getpass.getpass("登录密码: ")))'
python3 -c 'import secrets; print("AUTH_SECRET=" + secrets.token_hex(32))'
```

环境变量还可设置 `AUTH_USERNAME`（默认 `admin`）。服务启动时必须提供 `AUTH_PASSWORD_HASH` 和 `AUTH_SECRET`。

```bash
# 方式一：使用启动脚本
bash run_backend.sh

# 方式二：手动运行
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8088
```

> [!NOTE]
> 启动脚本实际监听地址为 `--host 0.0.0.0 --port 8088`，服务不仅在回环地址可用，局域网同网段设备亦可访问。登录会话有效期为 7 天；在纯 HTTP 下密码和会话会明文经过网络，跨不可信网络使用时应配置 HTTPS。

## 部署

生产环境需通过环境变量提供登录凭据，并在反向代理处启用 HTTPS。更新代码时保留 `backend/children_diary.db` 和 `backend/uploads/`；旧数据库首次启动新版时会自动创建 `*.pre-multichild-*.bak` 并迁移。登录凭据与证书私钥保存在部署环境中，不进入公开仓库。

当前公开入口为 `https://children.port.toms.chat/`。对应的 Nginx 站点模板见 `deploy/children-port-toms-chat.conf`；证书由网关上的 Certbot 续期。

## 数据隐私与存储说明

- 本地 SQLite 数据库（`backend/children_diary.db`）以及照片、音频等上传素材（`backend/uploads/`）属于家庭隐私数据，受 `.gitignore` 保护，**不进入代码仓库，亦不参与此次代码同步**。
- 首次在全新环境启动服务时，FastAPI 应用会自动在工作目录下创建全新的空数据库表结构。部署时应保留现有数据库和上传目录，不要用代码同步覆盖。
