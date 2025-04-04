import os
import clr
from contextlib import closing

import struct


clr.AddReference(os.path.abspath(r"../grp/bin/AdamMil.IO.dll"))
clr.AddReference(os.path.abspath(r"../grp/bin/AdamMil.Utilities.dll"))
clr.AddReference(os.path.abspath(r"../grp/bin/grp.dll"))
clr.AddReference("System")  # 加载 System.dll


from System.IO import FileStream, FileMode, FileAccess


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


def unpack_data(ndx_path,grp_path,output_dir):
  ndx_stream = FileStream(ndx_path, FileMode.Open, FileAccess.Read)
  grp_stream = FileStream(grp_path, FileMode.Open, FileAccess.Read)
  
  # 创建 GrpFile 实例
  grp_file = GrpFile(ndx_stream, grp_stream, False)
  
  try:
    if not os.path.exists(output_dir):
      os.makedirs(output_dir)

    for entry in grp_file.IndexEntries:
      file_name = entry.Name
      print(f"Extracting: {file_name}")
 
      output_path = os.path.join(output_dir, file_name)
      
     
      #方法1
      in_stream = grp_file.OpenFile(entry)
      out_stream = FileStream(output_path, FileMode.Create, FileAccess.Write)
      try:
            bytes_written = in_stream.CopyTo(out_stream)
            print(f"Wrote {bytes_written} bytes")
            # if bytes_written != entry.UncompressedSize:
            #     print(f"WARNING: Size mismatch! Expected {entry.UncompressedSize}, got {bytes_written}")
      finally:
          out_stream.Close()
          in_stream.Close()
      
  

  finally:
    grp_file.Dispose()
    ndx_stream.Close()
    grp_stream.Close()


  
  
  for file_name in os.listdir(output_dir):
    if file_name.endswith(".bmp"):
      check_bmp_header(os.path.join(output_dir, file_name))
        
if __name__=="__main__":
  # test_dll_interface()
  
  
  GAME_DIR=r"D:\SteamLibrary\steamapps\common\Dangerous Waters"
  BASE_DIR = os.path.dirname(os.path.abspath(__file__))
  
  folders=["Graphics"]
  
  for folder in folders:
    folder_path=os.path.join(GAME_DIR,folder)
    files=os.listdir(folder_path)
    
    grp_files=[]
    ndx_files=[]
    output_dirs=[]
    for file in files:
      if file.lower().endswith(('.grp')):
        ndx_file=file[0:-4]+".ndx"
        if ndx_file in files:
          ndx_files.append(os.path.join(folder_path,ndx_file) )
          grp_files.append(os.path.join(folder_path,file))
          output_dirs.append(os.path.join(BASE_DIR,f".\output\{file[0:-4]}"))
          
   
    
    
    for ndx_path,grp_path,output_dir in zip(ndx_files,grp_files,output_dirs):
      unpack_data(ndx_path,grp_path,output_dir)
      
    

  
  
  
