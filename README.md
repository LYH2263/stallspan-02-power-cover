# StallSpan 市集摊档开间

沿街段一维 First-Fit 开间分配，挡柱不可被摊位跨越；可登记供电桩（位置 + 服务半径），摊位起止闭区间须被单桩服务区完全盖住，否则进放不下（供电不足）。输出分配图与放不下清单。

技术栈：Python 3.12 / FastAPI / SQLAlchemy / PostgreSQL / Vue 3 / TypeScript / Vite

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4700 |
| API | http://localhost:9700 |
| API 文档 | http://localhost:9700/docs |
| Postgres | localhost:5448 |

健康检查：`GET http://localhost:9700/api/health`

## 使用说明

1. 在「集日」「街段」确认开市日与可用宽度。
2. 在「摊主」「挡柱」维护需求宽度与障碍位置。
3. 在「供电桩」维护桩位与服务半径（半径须 > 0、位置须在街段范围内；未配置任何桩时不加供电限制）。
4. 打开「分配图」执行一维开间分配（只展示覆盖合法的摊位）。
5. 在「放不下」查看无法安置的摊位及互斥拒因（空档不够 / 供电不足）。

## 开发与测试

```bash
docker compose exec api pytest -q
```
