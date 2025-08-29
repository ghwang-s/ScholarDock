# ScholarDock - 学术文献智能搜索与联系平台

## 项目概述

ScholarDock是一个现代化的全栈Web应用程序，专门用于搜索、分析和联系Google Scholar上的学术文献作者。该系统结合了网络爬虫技术、数据提取、自动化邮件通信等功能，为研究人员提供了一站式的学术文献处理解决方案。

## 核心功能

### 1. 智能学术搜索
- 基于Google Scholar的高级文献搜索
- 支持关键词、年份范围、排序方式等多维度筛选
- 自动去重机制，避免重复搜索相同文献
- 支持最多1000篇文献的批量搜索

### 2. 作者邮箱智能提取
- 从Google Scholar个人主页提取作者邮箱
- PDF回退机制：当主页无邮箱时，自动从论文PDF中提取
- 邮箱格式智能识别与验证
- 支持批量提取搜索结果中所有文献的作者邮箱

### 3. 自动化邮件通信
- 个性化邮件模板系统
- 支持单个和批量邮件发送
- 邮件预览功能
- 自动跳过已联系的作者，避免重复发送

### 4. 数据可视化分析
- 引用趋势图表分析
- 发表年份分布统计
- 实时数据过滤与探索

### 5. 数据管理
- SQLite数据库持久化存储
- 多格式数据导出（CSV、JSON、Excel、BibTeX）
- 搜索历史管理
- 搜索结果删除与维护

## 技术架构

### 后端技术栈
- **FastAPI**: 高性能异步Web框架
- **SQLAlchemy**: 数据库ORM
- **BeautifulSoup4**: HTML解析与数据提取
- **Selenium**: 处理CAPTCHA验证和复杂页面交互
- **Jinja2**: 邮件模板渲染
- **SQLite**: 轻量级数据库存储

### 前端技术栈
- **React 18**: 现代化组件化UI框架
- **TypeScript**: 类型安全的JavaScript超集
- **Tailwind CSS**: 实用优先的CSS框架
- **Framer Motion**: 流畅动画效果
- **React Query**: 服务器状态管理

## 系统要求

- Python 3.8+
- Node.js 16+
- Chrome/Chromium浏览器（用于Selenium回退）
- Conda（推荐用于Python环境管理）

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/ghwang-s/ScholarDock.git
cd ScholarDock

# 创建Conda环境
conda create -n scholar python=3.9
conda activate scholar
```

### 2. 后端配置

```bash
# 安装Python依赖
cd backend
pip install -r requirements.txt

# 配置邮箱
cd ..
echo "EMAIL_ADDRESS=your_email@163.com" >> .env
echo "EMAIL_PASSWORD=your_app_password" >> .env
```

### 3. 前端配置

```bash
# 安装前端依赖
cd frontend
npm install
```

### 4. 启动服务

```bash
# 返回项目根目录
cd ..

# 启动服务（推荐方式）
./run.sh
```

### 5. 测试安装流程

项目包含一个测试脚本，可以模拟完整的安装流程：

```bash
# 运行测试安装脚本
./test_installation.sh
```

该脚本将：
- 创建名为 `scholar_test` 的Conda环境
- 安装所有后端和前端依赖
- 创建必要的目录结构
- 配置环境变量

## 服务启动后，访问以下地址：
- 前端界面: http://localhost:5173
- 后端API: http://localhost:8001
- API文档: http://localhost:8001/docs

## 使用指南

### 1. 文献搜索
1. 在搜索页面输入关键词
2. 设置年份范围、排序方式等参数
3. 点击搜索按钮获取结果

### 2. 邮箱提取
1. 在搜索结果页面，点击"批量提取作者邮箱"
2. 系统将自动提取所有文献作者的邮箱
3. 提取结果将显示在作者信息区域

### 3. 邮件发送
1. 点击作者邮箱旁的发送按钮
2. 编辑邮件主题和内容
3. 使用预览功能查看邮件效果
4. 点击发送完成邮件发送

### 4. 批量邮件
1. 在搜索结果页面点击"批量发送邮件"
2. 设置邮件主题
3. 选择发送选项（作者邮箱、PDF邮箱）
4. 系统将自动发送邮件给所有提取到的邮箱

### 5. 邮件模板定制
邮件模板位于 `templates/email_template.html` 文件中，可以根据需要进行修改：
1. 打开 `templates/email_template.html` 文件
2. 修改HTML内容和样式
3. 调整模板变量（如作者名、论文标题等）
4. 保存文件后重新发送邮件即可看到效果

邮件模板支持以下变量：
- `{{ author_name }}` - 作者姓名
- `{{ paper_title }}` - 论文标题
- `{{ paper_venue_text }}` - 发表期刊/会议信息
- `{{ paper_year_text }}` - 发表年份
- `{{ sender_email }}` - 发送者邮箱

## 配置说明

### 代理配置
为提高Google Scholar访问稳定性，可配置代理：

```bash
# 设置环境变量
export SCHOLARDOCK_PROXY="http://127.0.0.1:7890"
```

### 邮箱配置
在项目根目录的`.env`文件中配置邮箱：

```env
EMAIL_ADDRESS=your_email@email.com
EMAIL_PASSWORD=your_app_password
```

注意：需要使用邮箱的授权码而非登录密码。

## API接口

主要API端点：

- `POST /api/search` - 执行文献搜索
- `GET /api/searches` - 获取搜索历史
- `GET /api/search/{id}` - 获取搜索详情
- `POST /api/extract-author-emails/{id}` - 提取单篇文献作者邮箱
- `POST /api/extract-all-author-emails/{id}` - 提取搜索结果中所有文献的作者邮箱
- `POST /api/email/send` - 发送邮件
- `POST /api/email/batch-send` - 批量发送邮件

完整的API文档请访问: http://localhost:8001/docs

## 项目结构

```
ScholarDock/
├── backend/                    # 后端代码
│   ├── api/                   # API路由
│   ├── core/                  # 核心配置
│   ├── models/                # 数据模型
│   ├── services/              # 业务服务
│   └── run.py                # 后端入口
├── frontend/                  # 前端代码
│   ├── src/                   # 源代码
│   │   ├── components/        # UI组件
│   │   ├── pages/             # 页面组件
│   │   ├── services/          # API服务
│   │   └── contexts/          # React上下文
│   └── package.json          # 前端依赖
├── data/                      # 数据库存储
├── templates/                 # 邮件模板
├── run.sh                    # 启动脚本
└── dev-server.sh             # 开发服务器脚本
```

## 故障排除

### 常见问题

1. **CAPTCHA验证**
   - 系统会自动打开浏览器窗口进行手动验证
   - 确保已安装Chrome/Chromium浏览器

2. **访问频率限制**
   - 系统内置延迟机制避免被封禁
   - 如仍被限制，可增加请求间隔时间

3. **邮箱发送失败**
   - 检查邮箱配置是否正确
   - 确认使用的是授权码而非登录密码
   - 检查网络连接和代理设置

## 贡献指南

欢迎提交Issue和Pull Request来改进项目：

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 许可证

本项目采用MIT许可证，详见[LICENSE](LICENSE)文件。

## 联系方式

如有问题或建议，请通过以下方式联系：

- WeChat: 15279836691
## 致谢

本项目基于 [JessyTsui/ScholarDock](https://github.com/JessyTsui/ScholarDock) 进行开发，在其基础上进行了以下改进：

1. 补充了完整的邮件发送功能，包括：
   - 个性化邮件模板系统
   - 单个和批量邮件发送
   - 邮件预览功能
   - 自动跳过已联系作者的机制

2. 前端界面美化：
   - 优化了搜索界面设计
   - 改进了数据可视化效果
   - 增强了用户体验

感谢原作者 JessyTsui 提供的基础框架和核心功能实现。
- GitHub Issues: https://github.com/ghwang-s/ScholarDock/issues