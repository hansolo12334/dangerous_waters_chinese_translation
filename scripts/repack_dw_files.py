import os
import clr
from contextlib import closing

import struct
from test_scale_image import compress_to_target

clr.AddReference(os.path.abspath(r"../grp/bin/AdamMil.IO.dll"))
clr.AddReference(os.path.abspath(r"../grp/bin/AdamMil.Utilities.dll"))
clr.AddReference(os.path.abspath(r"../grp/bin/grp.dll"))
clr.AddReference("System")  # 加载 System.dll


from System.IO import FileStream, FileMode, FileAccess,MemoryStream


# from grp import GrpFile
# from System import String

from System.Reflection import Assembly
from grp import GrpFile

def test_dll_interface():
  dll_path = os.path.abspath(r"../grp/bin/AdamMil.IO.dll")
  assembly = Assembly.LoadFrom(dll_path)
  print(f"Types in {dll_path}:")
  for t in assembly.GetTypes():
    print(t.FullName)
    
  print("-----------------------------------")
  dll_path = os.path.abspath(r"../grp/bin/AdamMil.Utilities.dll")
  assembly = Assembly.LoadFrom(dll_path)
  print(f"Types in {dll_path}:")
  for t in assembly.GetTypes():
    print(t.FullName)
  
  print("-----------------------------------")
  dll_path =os.path.abspath(r"../grp/bin/grp.dll")
  assembly = Assembly.LoadFrom(dll_path)
  print(f"Types in {dll_path}:")
  for t in assembly.GetTypes():
    print(t.FullName)


def check_bmp_header(file_path):
  with open(file_path, "rb") as f:
    header = f.read(2)
    if header == b"BM":
        print(f"{file_path} is a standard BMP file.")
    else:
        print(f"{file_path} is not a standard BMP file. Header: {header.hex()}")


def convert_to_bmp(input_path, output_path, width, height):
    with open(input_path, "rb") as f:
        raw_data = f.read()

    # BMP 文件头 (14 字节)
    file_size = 14 + 40 + len(raw_data)  # 文件头 + 信息头 + 数据
    bmp_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54)  # 文件头: "BM", 文件大小, 保留, 数据偏移

    # BMP 信息头 (40 字节, BITMAPINFOHEADER)
    info_header = struct.pack("<IIIHHIIIIII",
                              40,          # 信息头大小
                              width,       # 宽度
                              height,      # 高度
                              1,           # 颜色平面数
                              24,          # 每像素位数 (RGB, 24位)
                              0,           # 压缩类型 (无压缩)
                              len(raw_data),  # 图像数据大小
                              0,           # 水平分辨率
                              0,           # 垂直分辨率
                              0,           # 颜色数
                              0)           # 重要颜色数

    # 写入新文件
    with open(output_path, "wb") as f:
        f.write(bmp_header)
        f.write(info_header)
        f.write(raw_data)

def repack_data(ndx_path,grp_path,file_path):
  ndx_stream = FileStream(ndx_path, FileMode.Open, FileAccess.ReadWrite)
  grp_stream = FileStream(grp_path, FileMode.Open, FileAccess.ReadWrite)
  
  grp_file = GrpFile(ndx_stream, grp_stream, False)
  pixel_width=0
  pixel_height=0
  
  # file_stream = FileStream(file_path, FileMode.Open, FileAccess.Read)
  file_name=os.path.basename(file_path)
  print(file_name)
  try:
    # 找到并删除旧文件
    orig_entry = next((e for e in grp_file.IndexEntries if e.Name == file_name), None)
    if orig_entry:
      pixel_height=orig_entry.PixelHeight
      pixel_width=orig_entry.PixelWidth
      uncompressedSize=orig_entry.UncompressedSize
      print(f"原始图片大小:{pixel_width}x{pixel_height}")
      print(f"取消连接 {orig_entry.Name} (原始文件 压缩大小: {orig_entry.CompressedSize} 新文件 未压缩大小:{uncompressedSize} )")
      compress_to_target(file_path,file_path,uncompressedSize)
      file_stream = FileStream(file_path, FileMode.Open, FileAccess.Read)
      print(f"重新压缩修改后文件大小至->{uncompressedSize}")
      grp_file.Unlink(orig_entry)
      # print("保存更改...")
      # grp_file.Repack()
      # grp_file.Save()
    else:
        print("Original file not found.")

    try:
      grp_file.Add(file_name, file_stream, pixel_width, pixel_height)
    finally:
      file_stream.Close()
      
      
    # 检查新文件大小
    new_entry = next((e for e in grp_file.IndexEntries if e.Name == file_name), None)
    if new_entry:
        print(f"新文件: 未压缩大小={new_entry.UncompressedSize}, 压缩大小={new_entry.CompressedSize}")
    else:
        print("Failed to add new entry.")

    # 重新打包
    print("重新打包...")
    grp_file.Repack()
    # 保存更改
    print("保存更改...")
    grp_file.Save()

  finally:
      grp_file.Dispose()
      ndx_stream.Close()
      grp_stream.Close()

  print("修改完成!")
    
if __name__=="__main__":
  
  ndx_path = r"D:\Qt_project\2024\dangerous_waters_chinese_translation\scripts\mainmenu.ndx"
  grp_path = r"D:\Qt_project\2024\dangerous_waters_chinese_translation\scripts\mainmenu.grp"
  modified_bmp = r"D:\Qt_project\2024\dangerous_waters_chinese_translation\scripts\MAINMENU_bkg.bmp"  # 修改后的图片
  
  
  repack_data(ndx_path,grp_path,modified_bmp)
  

  
  
  
  
  # GAME_DIR=r"D:\SteamLibrary\steamapps\common\Dangerous Waters"
  # BASE_DIR = os.path.dirnamgrp_filee(os.path.abspath(__file__))
  
  # folders=["Graphics"]
  
  # for folder in folders:
  #   folder_path=os.path.join(GAME_DIR,folder)
  #   files=os.listdir(folder_path)
    
  #   grp_files=[]
  #   ndx_files=[]
  #   output_dirs=[]
  #   for file in files:
  #     if file.lower().endswith(('.grp')):
  #       ndx_file=file[0:-4]+".ndx"
  #       if ndx_file in files:
  #         ndx_files.append(os.path.join(folder_path,ndx_file) )
  #         grp_files.append(os.path.join(folder_path,file))
  #         output_dirs.append(os.path.join(BASE_DIR,f".\output\{file[0:-4]}"))
          
   
    
    
  #   for ndx_path,grp_path,output_dir in zip(ndx_files,grp_files,output_dirs):
  #     unpack_data(ndx_path,grp_path,output_dir)
      
    

  
  
  
