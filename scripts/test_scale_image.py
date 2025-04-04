from PIL import Image
import os

def compress_to_target(input_path, output_path, target_size_bytes):
    # 打开原始图像
    img = Image.open(input_path)
    
    # 转换为 RGB（BMP 通常是 RGB）
    img = img.convert("RGB")
    
    # 初始质量
    quality = 95
    step = 5
    
    # 二分查找调整质量
    while True:
        # 保存为 JPEG 临时文件
        temp_jpeg = "temp.jpg"
        img.save(temp_jpeg, "JPEG", quality=quality)
        
        # 转回 BMP
        temp_img = Image.open(temp_jpeg)
        temp_img.save(output_path, "BMP")
        
        # 检查 BMP 文件大小
        size = os.path.getsize(output_path)
        print(f"Quality: {quality}, Size: {size} bytes")
        
        if abs(size - target_size_bytes) < 10000:  # 允许 10KB 误差
            break
        elif size > target_size_bytes:
            quality -= step
        else:
            quality += step
        
        if quality < 10 or quality > 100:
            print("Cannot reach target size with acceptable quality.")
            break
    
    #
    os.remove(temp_jpeg)


# input_file = r"D:\Qt_project\2024\dangerous_waters_chinese_translation\scripts\output\mainmenu\测试\MAINMENU_bkg.bmp"  # 1.8 MB
# output_file = r"D:\Qt_project\2024\dangerous_waters_chinese_translation\scripts\output\mainmenu\测试\MAINMENU_bkg1.bmp"
# target_size = 1440054 #原大小 14.4mb

# compress_to_target(input_file, output_file, target_size)