# Website Quick Scan

用 GitHub Actions 快速扫描 GitHub Pages 网站可用性。

## 功能

- 每 15 分钟自动运行一次
- 支持 GitHub Actions 页面手动触发
- 从 `https://trbo.jiagar.us.kg/sitemap.xml` 自动读取全部 URL
- 并发检查所有页面，优先使用 `HEAD`，失败后自动使用轻量 `GET`
- 在 Actions Summary 中生成逐 URL 状态表
- 任意 URL 返回非 `2xx/3xx` 或请求失败时，workflow 标记为失败

## 手动运行

进入 **Actions → Website quick scan → Run workflow**。

## 本地运行

```bash
SITEMAP_URL=https://trbo.jiagar.us.kg/sitemap.xml python3 scan.py
```
