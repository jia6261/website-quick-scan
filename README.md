# Website Quick Scan

用 GitHub Actions 快速扫描 GitHub Pages 网站可用性。

## 功能

- 每 2 天自动运行一次
- 支持 GitHub Actions 页面手动触发
- 从 `https://trbo.jiagar.us.kg/sitemap.xml` 自动读取全部 URL
- 并发检查所有页面，优先使用 `HEAD`，失败后自动使用轻量 `GET`
- 自动解析页面中的 `<video>`、`<source>` 和常见视频文件链接（mp4/webm/ogg/m3u8 等）并检查视频资源
- 在 Actions Summary 中分别生成页面和视频状态表
- 每次扫描后创建一个带 UTC 时间戳的 GitHub Release，并上传当次 `sitemap.xml`
- 每次扫描后通过 GitHub Pages Actions 部署到 `/website-quick-scan/sitemap` 和 `/website-quick-scan/sitemap.xml`
- 任意 URL 返回非 `2xx/3xx` 或请求失败时，workflow 标记为失败

## 手动运行

进入 **Actions → Website quick scan → Run workflow**。

每次运行完成后，可在仓库的 **Releases** 页面下载对应的 sitemap 快照。即使扫描发现坏链，也会先发布 sitemap，再将 workflow 标记为失败。

线上 sitemap：

- <https://trbo.jiagar.us.kg/website-quick-scan/sitemap>
- <https://trbo.jiagar.us.kg/website-quick-scan/sitemap.xml>

## 本地运行

```bash
SITEMAP_URL=https://trbo.jiagar.us.kg/sitemap.xml python3 scan.py
```
