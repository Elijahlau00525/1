# 衣橱搭搭 (Python 全栈)

一个可在手机/平板/电脑浏览器使用的电子衣橱与自动搭配应用。

- 后端: FastAPI + SQLite
- 前端: 原生 HTML/CSS/JS + PWA
- 登录: 账号密码可直接使用，微信/QQ 提供 OAuth 接口位（需你填写平台密钥）

## 项目结构

| 路径 | 作用 |
|---|---|
| `backend/app/main.py` | FastAPI 入口，挂载 API 与前端静态资源 |
| `backend/app/routers/auth.py` | 注册/登录/微信/QQ OAuth |
| `backend/app/routers/items.py` | 衣物 CRUD 与图片分析 |
| `backend/app/routers/recommend.py` | 自动穿搭推荐接口 |
| `backend/app/services/image_analysis.py` | 颜色提取 + 上传图自动标签建议 |
| `backend/app/services/recommendation.py` | 穿搭打分规则（同色系/深浅对比/松紧对比等） |
| `backend/.env.example` | 环境变量模板 |
| `frontend/index.html` | App 化页面 |
| `frontend/assets/styles.css` | 移动端优先样式 |
| `frontend/assets/app.js` | 前端业务逻辑与 API 接入 |
| `frontend/manifest.json` | PWA 配置 |
| `frontend/sw.js` | Service Worker 缓存 |
| `run.ps1` | 一键初始化并启动 |

## 快速启动

1. 初始化并安装依赖:

```powershell
./run.ps1 -Init
```

如果 PowerShell 提示脚本策略限制，可用等价命令:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

2. 启动开发服务:

```powershell
./run.ps1
```

或:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --app-dir backend --host 0.0.0.0 --port 8000
```

3. 打开浏览器:

`http://127.0.0.1:8000`

## 已实现能力

- PNG 多图上传
- 电子衣橱管理（查看、删除）
- 自动识别建议（颜色、分类建议、版型建议、风格标签建议）
- 智能穿搭（按场景生成）
- 三套主题可切换（奶油通勤 / 都市冷调 / 晚风约会）并自动记住
- PWA（可添加到手机主屏）
- 账号密码登录
- 微信/QQ 登录 OAuth 路由骨架

## 微信/QQ 登录配置

在 `backend/.env` 配置以下字段:

- `WECHAT_APP_ID`
- `WECHAT_APP_SECRET`
- `WECHAT_REDIRECT_URI`
- `QQ_APP_ID`
- `QQ_APP_SECRET`
- `QQ_REDIRECT_URI`

说明:
- 你需要先在微信开放平台和 QQ 互联拿到应用资质与密钥。
- 回调地址必须和平台后台配置一致。
- 本项目可用 `GET /api/auth/providers/status` 检查当前是否已配置完成。

### 申请材料与步骤（你可直接照做）

1. 准备材料：
- 主体资料（个人/企业实名信息）
- 应用名称、图标、简介、隐私政策 URL
- 回调域名（开发阶段可先用固定公网域名）

2. QQ 互联申请：
- 官网入口：`https://connect.qq.com/`
- 文档入口：`https://wiki.connect.qq.com/`
- 完成创建应用、填写回调地址、获取 `App ID` / `App Key`

3. 微信开放平台申请：
- 官网入口：`https://open.weixin.qq.com/`
- 创建网站应用或移动应用，提交审核后获取 `AppID` / `AppSecret`

4. 填写到 `backend/.env` 后重启服务：
- `WECHAT_APP_ID` / `WECHAT_APP_SECRET`
- `QQ_APP_ID` / `QQ_APP_SECRET`

### 重要说明

- `AppID/Secret` 不能由我代领，必须在你自己的微信/QQ 开放平台账号下申请并签约。
- 我已经把联调代码打通，你拿到密钥后只需填 `.env` 即可进入真登录联调。

## API 简表

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/auth/wechat/login`
- `GET /api/auth/qq/login`
- `GET /api/auth/{provider}/callback`
- `GET /api/items`
- `POST /api/items`
- `POST /api/items/analyze`
- `DELETE /api/items/{item_id}`
- `GET /api/recommend?occasion=work`

## Android / iOS 打包（平板落地）

已新增目录：`mobile/`（Capacitor 原生壳工程配置）

### 你现在能做（Windows）

1. 安装 Node.js LTS、Android Studio、JDK 17  
2. 进入 `mobile/` 安装依赖：

```bash
cd mobile
npm install
```

3. 第一次创建 Android 工程：

```bash
npm run cap:add:android
```

4. 同步前端并打开 Android Studio：

```bash
npm run cap:android
```

5. 在 Android Studio 选择平板模拟器或真机，构建 `APK/AAB`

### iOS 平板（iPad）步骤

1. 把项目拷到 macOS（必须有 Xcode）  
2. 在 `mobile/` 运行：

```bash
npm install
npm run cap:add:ios
npm run cap:ios
```

3. 用 Xcode 选择 iPad 模拟器或真机，Archive 导出 `IPA`

### 移动端 API 地址配置

- 文件：`frontend/assets/runtime-config.js`
- 本地网页开发默认：

```js
apiBase: "/api"
```

- 打包 App 时建议改成公网后端：

```js
apiBase: "https://your-domain.com/api"
```

- 示例文件：`frontend/assets/runtime-config.mobile.example.js`

## 上 GitHub / 上云

- GitHub 上传与云部署说明见：`DEPLOY.md`
- 云部署已提供：
  - `Dockerfile`
  - `render.yaml`（Render Blueprint）
  - `GET /api/health` 健康检查接口

## 下一步建议

- 把 `style_tags` 扩展为多标签体系（韩系、Clean Fit、美拉德、Y2K）
- 接入更强视觉模型做衣物类别识别
- 增加“收藏搭配”和“穿搭日历”
