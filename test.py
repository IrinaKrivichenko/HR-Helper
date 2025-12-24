# рассчет tree_box_parameters_file_path

import cv2
import pandas as pd
from shapely.geometry import Polygon, MultiPolygon
from shapely import affinity
from shapely.ops import unary_union

# Параметры ёлочки
trunk_w, trunk_h = 0.15, 0.2
base_w, mid_w, top_w = 0.7, 0.4, 0.25
tip_y, tier_1_y, tier_2_y, base_y = 0.8, 0.5, 0.25, 0.0


scale_factor = 100  # Коэффициент масштабирования
import matplotlib
matplotlib.use('MacOSX')  # Используем бэкенд MacOSX

import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon, Point
from shapely import affinity

import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union

import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import unary_union

def plot_union(polygons, alpha=0.5, edgecolor='blue', linewidth=2, union_color='cyan'):
    """
    Рисует объединение списка полигонов.

    Parameters:
    - polygons: список объектов типа shapely.geometry.Polygon
    - alpha: прозрачность заливки объединения
    - edgecolor: цвет границ объединения
    - linewidth: толщина границ объединения
    - union_color: цвет заливки объединения
    """
    fig, ax = plt.subplots(figsize=(10, 10))

    # Объединяем все полигоны
    union = unary_union(polygons)

    # Рисуем каждый полигон из списка
    for polygon in polygons:
        if isinstance(polygon, Polygon):
            x, y = polygon.exterior.xy
            ax.fill(x, y, alpha=0.3, color='gray', edgecolor='black', linewidth=1)
        elif isinstance(polygon, MultiPolygon):
            for geom in polygon.geoms:
                x, y = geom.exterior.xy
                ax.fill(x, y, alpha=0.3, color='gray', edgecolor='black', linewidth=1)

    # Рисуем объединение
    if isinstance(union, Polygon):
        x, y = union.exterior.xy
        ax.fill(x, y, alpha=alpha, color=union_color, edgecolor=edgecolor, linewidth=linewidth)
    elif isinstance(union, MultiPolygon):
        for polygon in union.geoms:
            x, y = polygon.exterior.xy
            ax.fill(x, y, alpha=alpha, color=union_color, edgecolor=edgecolor, linewidth=linewidth)

    ax.set_aspect('equal')
    ax.axis('off')
    plt.tight_layout()
    plt.show(block=True)


def plot_polygons(polygons, colors=['blue'], alpha=0.7, edgecolor='black', linewidth=1):
    """
    Рисует список полигонов, выделяя пересекающиеся полигоны красным цветом и отмечая центры пересечений жёлтыми метками.
    """
    fig, ax = plt.subplots(figsize=(10, 10))

    if colors is None:
        colors = plt.cm.tab10(np.linspace(0, 1, len(polygons)))

    intersecting_indices = set()
    intersection_points = []

    # Проверка на пересечения
    for i in range(len(polygons)):
        for j in range(i + 1, len(polygons)):
            if polygons[i].intersects(polygons[j]):
                intersecting_indices.add(i)
                intersecting_indices.add(j)
                intersection = polygons[i].intersection(polygons[j])
                if not intersection.is_empty:
                    if intersection.geom_type == 'Polygon':
                        intersection_points.append(intersection.centroid)
                    elif intersection.geom_type == 'MultiPolygon':
                        for geom in intersection.geoms:
                            intersection_points.append(geom.centroid)
                    elif intersection.geom_type in ['Point', 'MultiPoint']:
                        if intersection.geom_type == 'Point':
                            intersection_points.append(intersection)
                        else:
                            for point in intersection.geoms:
                                intersection_points.append(point)
                    elif intersection.geom_type in ['LineString', 'MultiLineString']:
                        if intersection.geom_type == 'LineString':
                            coords = list(intersection.coords)
                            intersection_points.append(Point(np.mean(coords, axis=0)))
                        else:
                            for line in intersection.geoms:
                                coords = list(line.coords)
                                intersection_points.append(Point(np.mean(coords, axis=0)))

    # Рисуем полигоны
    for i, polygon in enumerate(polygons):
        x, y = polygon.exterior.xy
        color = 'red' if i in intersecting_indices else colors[i % len(colors)] if colors is not None else 'green'
        ax.fill(x, y, alpha=alpha, color=color, edgecolor=edgecolor, linewidth=linewidth)

    # Рисуем жёлтые метки в центре пересечений
    for point in intersection_points:
        ax.plot(point.x, point.y, marker='o', markersize=8, color='yellow', alpha=0.8)

    ax.set_aspect('equal')
    ax.axis('off')
    plt.tight_layout()
    plt.show(block=True)


def print_intersections_info(intersections):
    """
    Печатает информацию о пересечениях.

    Parameters:
    - intersections: результат работы функции check_intersections_for_four_trees
    """
    if intersections['has_intersections']:
        print("Обнаружены пересечения между следующими парами ёлочек:")
        for pair in intersections['pairs']:
            print(f"Ёлочка {pair[0]} и ёлочка {pair[1]}")
    else:
        print("Пересечений между ёлочками не обнаружено.")

def check_intersections_for_trees(trees):
    """
    Проверяет наличие пересечений между четырьмя ёлочками.

    Parameters:
    - trees: список из четырёх объектов типа shapely.geometry.Polygon

    Returns:
    - пересечения: словарь с информацией о пересечениях
    """
    intersections = {
        'pairs': [],
        'has_intersections': False
    }
    for i in range(len(trees)):
        for j in range(i + 1, len(trees)):
            if trees[i].intersects(trees[j]):
                intersections['pairs'].append((i, j))
                intersections['has_intersections'] = True
    print_intersections_info(intersections)


# Создание ёлочки
def create_tree(center_x, center_y, angle=0):
    coords = [
        (0.0, tip_y),
        (top_w / 2, tier_1_y), (top_w / 4, tier_1_y),
        (mid_w / 2, tier_2_y), (mid_w / 4, tier_2_y),
        (base_w / 2, base_y), (trunk_w / 2, base_y), (trunk_w / 2, -trunk_h),
        (-trunk_w / 2, -trunk_h), (-trunk_w / 2, base_y), (-base_w / 2, base_y),
        (-mid_w / 4, tier_2_y), (-mid_w / 2, tier_2_y),
        (-top_w / 4, tier_1_y), (-top_w / 2, tier_1_y),
    ]
    polygon = Polygon(coords)
    rotated = affinity.rotate(polygon, angle, origin=(0, 0))
    return affinity.translate(rotated, xoff=center_x, yoff=center_y)


# Получение точек контура полигона с масштабированием
def get_contour_points(polygon):
    if isinstance(polygon, MultiPolygon):
        points = []
        for p in polygon.geoms:
            x, y = p.exterior.xy
            points.extend(list(zip(x, y)))
        return np.array(points).astype(np.float32) * scale_factor
    else:
        x, y = polygon.exterior.xy
        return np.column_stack((x, y)).astype(np.float32) * scale_factor


# Поиск оптимального горизонтального расстояния между двумя ёлочками
def find_optimal_delta_x(angle1, angle2, delta_y=0, precision=0.0001):
    x1, x2 = -5.0, 5.0  # Начальные позиции
    step = 0.1  # Размер шага

    # Создаём ёлочки
    tree1 = create_tree(x1, 0, angle=angle1)
    tree2 = create_tree(x2, delta_y, angle=angle2)

    # Перемещаем ёлочки навстречу друг другу
    while (step >= precision) or (tree1.intersects(tree2)):
        if tree1.intersects(tree2):
            x1 -= step
            x2 += step
            step /= 10
        x1 += step
        x2 -= step
        tree1 = create_tree(x1, 0, angle=angle1)
        tree2 = create_tree(x2, delta_y, angle=angle2)
    return x2 - x1  # Оптимальное горизонтальное расстояние


def find_min_rectangle(tree1, tree2):
    contour1 = get_contour_points(tree1)
    contour2 = get_contour_points(tree2)
    all_points = np.vstack((contour1, contour2))
    rect = cv2.minAreaRect(all_points)
    box = cv2.boxPoints(rect)
    return rect, box / scale_factor  # Возвращаем координаты в исходном масштабе


def create_tree_pair(delta_y=None, delta_x=None, angle=None, add_90_deg=False):
    if delta_x is None or angle is None:
        delta_x = find_optimal_delta_x(0, 180, delta_y)
        tree1 = create_tree(0, 0, angle=0)
        tree2 = create_tree(delta_x, delta_y, angle=180)
        # Находим минимальный прямоугольник с помощью OpenCV
        rect, box = find_min_rectangle(tree1, tree2)
        cv_center, cv_size, cv_angle = rect
        _, cv_size, _ = rect
        cv_width, cv_height = cv_size[0] / scale_factor, cv_size[1] / scale_factor
        if add_90_deg:
            cv_angle += 90
            cv_height, cv_width = cv_width, cv_height
    else:
        tree1 = create_tree(0, 0, angle=0)
        tree2 = create_tree(delta_x, delta_y, angle=180)
        cv_angle = angle
        cv_width, cv_height = 0, 0

    # Поворот ёлочек на -cv_angle вокруг общего центра масс
    union = unary_union([tree1, tree2])
    center = np.array(union.centroid.coords[0])
    tree1_rotated = affinity.rotate(tree1, -cv_angle, origin=tuple(center), use_radians=False)
    tree2_rotated = affinity.rotate(tree2, -cv_angle, origin=tuple(center), use_radians=False)
    area = cv_width * cv_height
    print('2 елочки пересекаются после построения ', tree1_rotated.intersects(tree2_rotated))
    return tree1_rotated, tree2_rotated, delta_x, cv_angle, cv_width, cv_height, area


from shapely import affinity

def translate_polygons(polygons, delta_x, delta_y):
    """
    Смещает список полигонов на заданные delta_x и delta_y.
    Parameters:
    - polygons: список объектов типа shapely.geometry.Polygon
    - delta_x: смещение по оси x
    - delta_y: смещение по оси y
    Returns:
    - список смещённых полигонов
    """
    translated_polygons = []
    for polygon in polygons:
        translated_polygon = affinity.translate(polygon, xoff=delta_x, yoff=delta_y)
        translated_polygons.append(translated_polygon)
    return translated_polygons


def has_intersections(polygons1, polygons2):
    # Проверка пересечений между всеми полигонами из pair1 и pair2_translated
    for poly1 in polygons1:
        for poly2 in polygons2:
            if poly1.intersects(poly2):
                return True
    return False

def find_optimal_delta_x_between_pairs(pair1, pair2, precision=0.00001):
    """
    Находит оптимальное горизонтальное смещение между двумя парами ёлочек.
    Parameters:
    - pair1: первая пара ёлочек (список полигонов)
    - pair2: вторая пара ёлочек (список полигонов)
    - precision: точность вычислений
    Returns:
    - оптимальное горизонтальное смещение
    """
    x = 0.0
    step = 0.1
    pair2_translated = translate_polygons(pair2, x, 0)
    while step >= precision or has_intersections(pair1, pair2_translated):
        if has_intersections(pair1, pair2_translated):
            x += step
        else:
            x -= step
            step /= 10
        pair2_translated = translate_polygons(pair2, x, 0)

    return abs(x)




def create_row_of_pairs(n_pairs, delta_y=None, delta_x=None, angle=None, add_90_deg=False, pair_delta_x=None):
    trees = []
    angles = []
    x = 0.0

    # Создаем первую пару
    tree1_rotated, tree2_rotated, delta_x, angle, pair_width, pair_height, pair_area = create_tree_pair(delta_y,
                                                                                                        delta_x, angle,
                                                                                                        add_90_deg)
    tree1_translated = affinity.translate(tree1_rotated, xoff=x)
    tree2_translated = affinity.translate(tree2_rotated, xoff=x)
    trees.extend([tree1_translated, tree2_translated])
    angles.extend([0, 180])

    # Определяем оптимальное расстояние между парами, если оно не задано
    if pair_delta_x is None:
        next_tree1_rotated, next_tree2_rotated, _, _, _, _, _ = create_tree_pair(delta_y, delta_x, angle, add_90_deg)
        current_pair = [tree1_translated, tree2_translated]
        next_pair = [next_tree1_rotated, next_tree2_rotated]
        pair_delta_x = find_optimal_delta_x_between_pairs(current_pair, next_pair)

    # Создаем оставшиеся пары
    for i in range(1, n_pairs):
        tree1_rotated, tree2_rotated, _, _, _, _, _ = create_tree_pair(delta_y, delta_x, angle, add_90_deg)
        x += pair_delta_x
        tree1_translated = affinity.translate(tree1_rotated, xoff=x)
        tree2_translated = affinity.translate(tree2_rotated, xoff=x)
        trees.extend([tree1_translated, tree2_translated])
        angles.extend([0, 180])

    check_intersections_for_trees(trees[0:4])

    return trees, angles, pair_width, pair_height, pair_area, pair_delta_x



def find_optimal_delta_y_between_rows(row1, row2, precision=0.00001):
    """
    Находит оптимальное вертикальное смещение между двумя рядами ёлочек.

    Parameters:
    - row1: первый ряд ёлочек (список полигонов)
    - row2: второй ряд ёлочек (список полигонов)
    - precision: точность вычислений

    Returns:
    - оптимальное вертикальное смещение
    """
    y = 0.0
    step = 0.1
    row2_translated = translate_polygons(row2, 0, y)

    while step >= precision:
        if has_intersections(row1, row2_translated):
            y -= step
        else:
            y += step
            step /= 10
        row2_translated = translate_polygons(row2, 0, y)

    # Дополнительная проверка для точности
    while has_intersections(row1, row2_translated):
        y -= precision
        row2_translated = translate_polygons(row2, 0, y)

    plot_polygons(row1 + row2_translated)
    print("Пересечения между рядами:", has_intersections(row1, row2_translated))

    return abs(y)


def create_row_of_pairs(n_pairs, delta_y=None, delta_x=None, angle=None, add_90_deg=False, pair_delta_x=None):
    trees = []
    angles = []
    x = 0.0

    # Создаем первую пару
    tree1_rotated, tree2_rotated, delta_x, angle, pair_width, pair_height, pair_area = create_tree_pair(delta_y,
                                                                                                        delta_x, angle,
                                                                                                        add_90_deg)
    tree1_translated = affinity.translate(tree1_rotated, xoff=x)
    tree2_translated = affinity.translate(tree2_rotated, xoff=x)
    trees.extend([tree1_translated, tree2_translated])
    angles.extend([0, 180])

    # Определяем оптимальное расстояние между парами, если оно не задано
    if pair_delta_x is None:
        next_tree1_rotated, next_tree2_rotated, _, _, _, _, _ = create_tree_pair(delta_y, delta_x, angle, add_90_deg)
        current_pair = [tree1_translated, tree2_translated]
        next_pair = [next_tree1_rotated, next_tree2_rotated]
        pair_delta_x = find_optimal_delta_x_between_pairs(current_pair, next_pair)
        # 1.4430900000000004
        # 1.4430869999999998
    # Создаем оставшиеся пары
    for i in range(1, n_pairs):
        tree1_rotated, tree2_rotated, _, _, _, _, _ = create_tree_pair(delta_y, delta_x, angle, add_90_deg)
        x += pair_delta_x
        tree1_translated = affinity.translate(tree1_rotated, xoff=x)
        tree2_translated = affinity.translate(tree2_rotated, xoff=x)
        trees.extend([tree1_translated, tree2_translated])
        angles.extend([0, 180])

        # Проверка пересечений между новой парой и предыдущими
        for existing_tree in trees[:-2]:
            if tree1_translated.intersects(existing_tree) or tree2_translated.intersects(existing_tree):
                print(f"Пересечение между новой парой и существующими ёлочками на позиции {i}")

    # Проверка всех пересечений в ряду
    for i in range(len(trees)):
        for j in range(i + 1, len(trees)):
            if trees[i].intersects(trees[j]):
                print(f"Пересечение между ёлочками {i} и {j} в ряду")

    check_intersections_for_trees(trees[0:4])
    plot_polygons(trees)

    return trees, angles, pair_width, pair_height, pair_area, pair_delta_x


def calculate_optimal_parameters(t_start, t_end, t_step):
    min_delta_y = 0.355555555
    middle_t = 1 - min_delta_y
    data = []
    for t in np.arange(t_start, t_end, t_step):
        t_rounded = round(t, 3)
        if t_rounded < middle_t:
            delta_y = 1 - t
            add_90_deg = False
        else:
            delta_y = t_rounded - middle_t + min_delta_y
            add_90_deg = True

        tree1_rotated, tree2_rotated, delta_x, angle, pair_width, pair_height, pair_area = create_tree_pair(
            delta_y=delta_y, add_90_deg=add_90_deg)

        # Определяем оптимальное вертикальное расстояние между рядами
        row1, _, _, _, _, pair_delta_x = create_row_of_pairs(2, delta_y, delta_x, angle, add_90_deg)
        row2, _, _, _, _, _ = create_row_of_pairs(2, delta_y, delta_x, angle, add_90_deg)
        optimal_delta_y_between_rows = find_optimal_delta_y_between_rows(row1, row2)

        data.append({
            't': t_rounded,
            'delta_y': delta_y,
            'delta_x': delta_x,
            'angle': angle,
            'pair_width': pair_width,
            'pair_height': pair_height,
            'pair_area': pair_area,
            'optimal_delta_x_between_pair': pair_delta_x,
            'optimal_delta_y_between_rows': optimal_delta_y_between_rows
        })

        df = pd.DataFrame(data)

        # Сохранение DataFrame
        # df.to_csv(tree_box_parameters_file_path, index=False)
    return df


def stack_rows(rows, optimal_delta_y_between_rows):
    all_trees = []
    y_shift = 0.0

    for i, row in enumerate(rows):
        if i > 0:
            y_shift -= optimal_delta_y_between_rows
            row = [affinity.translate(tree, yoff=y_shift) for tree in row]

        all_trees.extend(row)

    return all_trees


# Запуск расчетов и визуализации
df = calculate_optimal_parameters(0, 1.2, 0.001)

# from dotenv import load_dotenv
#
#
# load_dotenv()
#
# # bot.py
# from telegram import Update
# from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler
#
# import os
#
# # async def handle_forwarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
# #     user = update.effective_user
# #     user_name = user.username if user.username else user.first_name
# #     text = update.message.text
# #     await update.message.reply_text(f"Hi, {user_name}. Your have sent me {text}")
# #
# #
# #
# #
# # BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# # app = ApplicationBuilder().token(BOT_TOKEN).build()
# # app.add_handler(MessageHandler(filters.ALL, handle_forwarded))
# # app.run_polling()
#
# # from telegram import Bot
# #
# # BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# # bot = Bot(token=BOT_TOKEN)
# # bot.send_message(chat_id=694614399, text='Message text')
#
# import asyncio
# from telegram import Bot
# load_dotenv()
#
# async def send():
#     BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
#     bot = Bot(token=BOT_TOKEN)
#     await bot.send_message(chat_id=694614399, text='Hello')
#
# asyncio.run(send())
