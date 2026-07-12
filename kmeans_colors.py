from PIL import Image, ImageDraw
import argparse
import json
import random
from pathlib import Path


def make_sample_image(sample_image_path):
    """如果 assets 里没有图片，就生成一张方便测试的示例图片。"""
    sample_image_path.parent.mkdir(parents=True, exist_ok=True)

    image_width = 360
    image_height = 240
    sample_image = Image.new("RGB", (image_width, image_height), (245, 245, 238))
    image_drawer = ImageDraw.Draw(sample_image)

    image_drawer.rectangle([0, 0, 150, 240], fill=(224, 80, 70))
    image_drawer.rectangle([150, 0, 260, 150], fill=(62, 132, 210))
    image_drawer.rectangle([150, 150, 360, 240], fill=(232, 190, 75))
    image_drawer.ellipse([205, 35, 330, 160], fill=(74, 160, 105))
    image_drawer.rectangle([35, 55, 120, 135], fill=(85, 55, 130))

    sample_image.save(sample_image_path)


def rgb_to_hex(red_value, green_value, blue_value):
    """把 RGB 颜色转换成网页可以直接使用的十六进制颜色。"""
    return f"#{red_value:02x}{green_value:02x}{blue_value:02x}"


def color_distance(first_color, second_color):
    """计算两个 RGB 颜色之间的距离。距离越小，颜色越接近。"""
    red_difference = first_color[0] - second_color[0]
    green_difference = first_color[1] - second_color[1]
    blue_difference = first_color[2] - second_color[2]

    distance_value = (
        red_difference * red_difference
        + green_difference * green_difference
        + blue_difference * blue_difference
    )

    return distance_value


def read_pixels_from_image(image_path, max_size, sample_step):
    """读取图片像素。先缩小图片，再隔几个像素采样一次，避免计算太慢。"""
    image_file = Image.open(image_path).convert("RGB")
    image_file.thumbnail((max_size, max_size))

    image_width, image_height = image_file.size
    pixel_list = []

    for y_position in range(0, image_height, sample_step):
        for x_position in range(0, image_width, sample_step):
            red_value, green_value, blue_value = image_file.getpixel((x_position, y_position))
            pixel_list.append((red_value, green_value, blue_value))

    return pixel_list


def choose_start_centers(pixel_list, cluster_count):
    """第 1 步：随机产生 K 个中心位置。"""
    unique_pixel_list = list(set(pixel_list))

    if len(unique_pixel_list) < cluster_count:
        raise ValueError("图片中的不同颜色数量少于 K 值，请减小 K。")

    start_centers = random.sample(unique_pixel_list, cluster_count)

    return start_centers


def find_nearest_center(pixel_color, center_list):
    """找到一个像素距离最近的中心点。"""
    nearest_center_index = 0
    nearest_distance = color_distance(pixel_color, center_list[0])

    for center_index in range(1, len(center_list)):
        current_distance = color_distance(pixel_color, center_list[center_index])

        if current_distance < nearest_distance:
            nearest_distance = current_distance
            nearest_center_index = center_index

    return nearest_center_index


def make_empty_groups(cluster_count):
    """按照 K 值创建空类别。"""
    color_groups = []

    for group_index in range(cluster_count):
        color_groups.append([])

    return color_groups


def put_pixels_into_groups(pixel_list, center_list):
    """第 2 步：将每个数据点归为距离最近的中心位置所属的类。"""
    color_groups = make_empty_groups(len(center_list))

    for pixel_color in pixel_list:
        nearest_center_index = find_nearest_center(pixel_color, center_list)
        color_groups[nearest_center_index].append(pixel_color)

    return color_groups


def average_group_color(color_group):
    """计算一个类别中所有像素的平均 RGB 颜色。"""
    red_total = 0
    green_total = 0
    blue_total = 0

    for pixel_color in color_group:
        red_total = red_total + pixel_color[0]
        green_total = green_total + pixel_color[1]
        blue_total = blue_total + pixel_color[2]

    pixel_count = len(color_group)
    average_red = round(red_total / pixel_count)
    average_green = round(green_total / pixel_count)
    average_blue = round(blue_total / pixel_count)

    return (average_red, average_green, average_blue)


def update_centers(color_groups, old_center_list):
    """第 3 步：根据新的类别划分重新计算中心位置。"""
    new_center_list = []

    for group_index in range(len(color_groups)):
        color_group = color_groups[group_index]

        if len(color_group) == 0:
            new_center_list.append(old_center_list[group_index])
        else:
            new_center_list.append(average_group_color(color_group))

    return new_center_list


def centers_are_same(first_center_list, second_center_list):
    """判断中心点是否已经不再变化。"""
    for center_index in range(len(first_center_list)):
        if first_center_list[center_index] != second_center_list[center_index]:
            return False

    return True


def run_k_means(pixel_list, cluster_count, max_rounds):
    """第 4 步：重复分组和更新中心，直到中心不再变化或达到最大轮数。"""
    center_list = choose_start_centers(pixel_list, cluster_count)
    final_groups = make_empty_groups(cluster_count)

    for round_index in range(max_rounds):
        color_groups = put_pixels_into_groups(pixel_list, center_list)
        new_center_list = update_centers(color_groups, center_list)
        final_groups = color_groups

        if centers_are_same(center_list, new_center_list):
            break

        center_list = new_center_list

    return center_list, final_groups, round_index + 1


def build_result_data(center_list, color_groups, image_path, round_count):
    """把 Python 聚类结果整理成页面和 ECharts 更容易使用的数据。"""
    result_list = []
    total_pixel_count = 0

    for color_group in color_groups:
        total_pixel_count = total_pixel_count + len(color_group)

    for center_index in range(len(center_list)):
        red_value = center_list[center_index][0]
        green_value = center_list[center_index][1]
        blue_value = center_list[center_index][2]
        pixel_count = len(color_groups[center_index])
        percent_value = round(pixel_count / total_pixel_count * 100, 2)

        result_item = {
            "name": f"颜色 {center_index + 1}",
            "rgb": [red_value, green_value, blue_value],
            "hex": rgb_to_hex(red_value, green_value, blue_value),
            "count": pixel_count,
            "percent": percent_value,
        }

        result_list.append(result_item)

    result_list.sort(key=lambda item: item["count"], reverse=True)

    result_data = {
        "image": str(image_path).replace("\\", "/"),
        "k": len(center_list),
        "rounds": round_count,
        "clusters": result_list,
    }

    return result_data


def find_image_paths(assets_folder):
    """查找 assets 文件夹中的图片，用于实现页面上的图片选择功能。"""
    image_suffixes = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]
    image_path_list = []

    for image_path in assets_folder.iterdir():
        if image_path.suffix.lower() in image_suffixes:
            image_path_list.append(image_path)

    image_path_list.sort()

    return image_path_list


def build_all_result_data(image_path_list, k_min, k_max, max_size, sample_step, max_rounds):
    """提前计算不同图片和不同 K 值的结果，让网页端可以交互切换。"""
    all_result_data = {
        "images": [],
        "kValues": list(range(k_min, k_max + 1)),
        "results": {},
    }

    for image_path in image_path_list:
        image_key = str(image_path).replace("\\", "/")
        pixel_list = read_pixels_from_image(image_path, max_size, sample_step)

        all_result_data["images"].append(image_key)
        all_result_data["results"][image_key] = {}

        for cluster_count in range(k_min, k_max + 1):
            center_list, color_groups, round_count = run_k_means(pixel_list, cluster_count, max_rounds)
            result_data = build_result_data(center_list, color_groups, image_path, round_count)
            all_result_data["results"][image_key][str(cluster_count)] = result_data

    return all_result_data


def save_result_files(all_result_data, json_path, js_path):
    """同时输出 JSON 和 JS。JS 文件可以被 HTML 直接引用。"""
    json_path.parent.mkdir(parents=True, exist_ok=True)

    json_text = json.dumps(all_result_data, ensure_ascii=False, indent=2)
    js_text = "window.colorClusterResults = " + json_text + ";\n"

    json_path.write_text(json_text, encoding="utf-8")
    js_path.write_text(js_text, encoding="utf-8")


def parse_arguments():
    argument_parser = argparse.ArgumentParser(description="使用 Python k-means 分析图片主色。")

    argument_parser.add_argument("--image", default="", help="只分析某一张图片；不填写时分析 assets 中所有图片。")
    argument_parser.add_argument("--assets", default="assets", help="图片文件夹路径。")
    argument_parser.add_argument("--k-min", type=int, default=2, help="页面可选的最小 K 值。")
    argument_parser.add_argument("--k-max", type=int, default=8, help="页面可选的最大 K 值。")
    argument_parser.add_argument("--max-size", type=int, default=320, help="图片参与计算前的最大边长。")
    argument_parser.add_argument("--sample-step", type=int, default=2, help="像素采样步长，数值越大计算越快。")
    argument_parser.add_argument("--max-rounds", type=int, default=30, help="k-means 最大迭代轮数。")
    argument_parser.add_argument("--seed", type=int, default=7, help="随机种子，用来让结果更稳定。")
    argument_parser.add_argument("--json", default="data/result.json", help="JSON 输出路径。")
    argument_parser.add_argument("--js", default="data/result.js", help="JS 输出路径。")

    return argument_parser.parse_args()


def main():
    arguments = parse_arguments()
    random.seed(arguments.seed)

    assets_folder = Path(arguments.assets)
    sample_image_path = assets_folder / "sample.png"

    if not assets_folder.exists():
        assets_folder.mkdir(parents=True, exist_ok=True)

    if arguments.image:
        image_path_list = [Path(arguments.image)]
    else:
        image_path_list = find_image_paths(assets_folder)

    if len(image_path_list) == 0:
        make_sample_image(sample_image_path)
        image_path_list = [sample_image_path]

    all_result_data = build_all_result_data(
        image_path_list,
        arguments.k_min,
        arguments.k_max,
        arguments.max_size,
        arguments.sample_step,
        arguments.max_rounds,
    )

    save_result_files(all_result_data, Path(arguments.json), Path(arguments.js))

    print(f"分析图片数量：{len(image_path_list)}")
    print(f"K 值范围：{arguments.k_min} 到 {arguments.k_max}")
    print(f"结果文件：{arguments.json} 和 {arguments.js}")


if __name__ == "__main__":
    main()
