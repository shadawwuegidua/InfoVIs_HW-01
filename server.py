from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote
import base64
import json
import random

from kmeans_colors import build_result_data
from kmeans_colors import read_pixels_from_image
from kmeans_colors import run_k_means


class ColorKMeansHandler(SimpleHTTPRequestHandler):
    """本地网页服务：普通文件直接返回，/analyze 用来处理图片上传和 k-means。"""

    def do_POST(self):
        if self.path == "/analyze":
            self.handle_analyze_request()
        else:
            self.send_error(404, "接口不存在")

    def handle_analyze_request(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            request_body = self.rfile.read(content_length).decode("utf-8")
            request_data = json.loads(request_body)

            image_name = request_data["imageName"]
            image_data = request_data["imageData"]
            cluster_count = int(request_data["k"])

            image_path = self.save_uploaded_image(image_name, image_data)
            pixel_list = read_pixels_from_image(image_path, max_size=320, sample_step=2)

            random.seed(7)
            center_list, color_groups, round_count = run_k_means(pixel_list, cluster_count, max_rounds=30)
            result_data = build_result_data(center_list, color_groups, image_path, round_count)

            self.send_json(result_data)
        except Exception as error:
            self.send_json({"message": str(error)}, status_code=400)

    def save_uploaded_image(self, image_name, image_data):
        upload_folder = Path("assets") / "uploads"
        upload_folder.mkdir(parents=True, exist_ok=True)

        clean_image_name = Path(unquote(image_name)).name
        image_path = upload_folder / clean_image_name
        base64_text = image_data.split(",", 1)[1]
        image_bytes = base64.b64decode(base64_text)

        image_path.write_bytes(image_bytes)

        return image_path

    def send_json(self, result_data, status_code=200):
        response_text = json.dumps(result_data, ensure_ascii=False)
        response_bytes = response_text.encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)


def main():
    server_address = ("127.0.0.1", 8000)
    web_server = ThreadingHTTPServer(server_address, ColorKMeansHandler)

    print("本地服务已启动：http://127.0.0.1:8000/index.html")
    print("按 Ctrl+C 可以停止服务。")

    web_server.serve_forever()


if __name__ == "__main__":
    main()
