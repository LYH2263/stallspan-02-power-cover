# StallSpan 市集摊档开间

沿街段一维 First-Fit 开间分配，挡柱不可被摊位跨越，输出分配图与放不下清单。

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
3. 在「供电桩」按街段登记/增删改供电桩的位置米标与服务半径（半径须 > 0，位置不得越界）。未配置供电桩的街段按绿仓处理，无供电约束。
4. 打开「分配图」执行一维开间分配：摊位起止闭区间须被至少一座供电桩的服务区间完全盖住，只盖中点或一端外露会被拒绝。
5. 在「放不下」查看无法安置的摊位；拒因互斥——「供电不足」与「无连续空档/跨柱」各自独立，不合并成一句。

## 开发与测试

```bash
docker compose exec api pytest -q
```
