# HW01 图片颜色聚类可视化

## 运行步骤

1. 把要分析的图片放到 `HW-01/assets/` 文件夹中。
2. 打开 `index.html`，上传图片并输入 K 值。

部署到 GitHub Pages 后，网页会在浏览器中直接完成图片读取和 k-means 计算。

## 本地预览

直接打开：

```text
index.html
```

或者使用任意静态服务器打开页面。

## Python 版本

启动网页服务：

```bash
python server.py
```

然后打开：

```text
http://127.0.0.1:8000/index.html
```

这个方式会通过本地 Python 服务计算 k-means。

如果只想提前生成默认展示数据，可以运行：

```bash
python kmeans_colors.py
```

只分析某一张图片：

```bash
python kmeans_colors.py --image assets/your_image.jpg
```

修改页面可选 K 值范围：

```bash
python kmeans_colors.py --k-min 2 --k-max 10
```

脚本会输出两个文件：

```text
data/result.json
data/result.js
```

其中 `result.json` 方便查看数据，`result.js` 供页面直接读取。
