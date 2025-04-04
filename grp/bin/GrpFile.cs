/*
grp is a program to read, create, and modify .ndx/.grp archive files used by
Sonalysts' simulation software. It is part of the DWMU (Dangerous Waters Mod
Utilities) package.

http://www.adammil.net/
Copyright (C) 2011 Adam Milazzo

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
*/

using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.IO.Compression;
using System.Linq;
using AdamMil.IO;
using AdamMil.IO.Compression;
using AdamMil.Utilities;

namespace grp
{
  #region NdxEntry
  sealed class NdxEntry
  {
    public NdxEntry(uint offset, uint size)
    {
      Offset         = offset;
      CompressedSize = size;
    }

    public NdxEntry(byte[] data)
    {
      Offset           = IOH.ReadLE4U(data, 80);
      UncompressedSize = IOH.ReadLE4U(data, 84);
      CompressedSize   = IOH.ReadLE4U(data, 88);
      PixelWidth       = IOH.ReadLE4U(data, 92);
      PixelHeight      = IOH.ReadLE4U(data, 96);

      int nameLength;
      for(nameLength=0; nameLength<80 && data[nameLength] != 0; nameLength++) { }
      Name = System.Text.Encoding.ASCII.GetString(data, 0, nameLength);
    }

    public uint End
    {
      get { return Offset + CompressedSize; }
    }

    public void Save(byte[] data)
    {
      int nameLength = System.Text.Encoding.ASCII.GetBytes(Name, 0, Name.Length, data, 0);
      Array.Clear(data, nameLength, 80-nameLength);
      IOH.WriteLE4U(data, 80, Offset);
      IOH.WriteLE4U(data, 84, UncompressedSize);
      IOH.WriteLE4U(data, 88, CompressedSize);
      IOH.WriteLE4U(data, 92, PixelWidth);
      IOH.WriteLE4U(data, 96, PixelHeight);
    }

    public override string ToString()
    {
      return (Name == null ? "<free>" : Name) + " " + Offset.ToInvariantString() + " - " + End.ToInvariantString();
    }

    public string Name;
    public uint CompressedSize, Offset, UncompressedSize, PixelWidth, PixelHeight;
  }
  #endregion

  sealed class GrpFile : IDisposable
  {
    public GrpFile(Stream ndxFile, Stream grpFile, bool ownStreams)
    {
      if(ndxFile == null || grpFile == null) throw new ArgumentNullException();
      if(!ndxFile.CanRead || !grpFile.CanRead) throw new ArgumentException("The streams are not readable.");
      if(!grpFile.CanSeek) throw new ArgumentException("The .grp stream is not seekable.");

      byte[] entryData = new byte[100];
      char[] nameChars = new char[80];
      while(true)
      {
        int read = ndxFile.FullRead(entryData, 0, entryData.Length);
        if(read == 0) break;
        if(read != 100) throw new InvalidDataException("The .ndx stream length is not a multiple of 100 bytes.");
        entries.Add(new NdxEntry(entryData));
      }

      // sort entries by offset, then create a linked list representing the .grp file structure
      NdxEntry[] sortedEntries = entries.ToArray();
      Array.Sort(sortedEntries, (a, b) => a.Offset.CompareTo(b.Offset));
      uint start = 0;
      for(int i=0; i<sortedEntries.Length; i++)
      {
        if(i < sortedEntries.Length-1 && sortedEntries[i].End > sortedEntries[i+1].Offset)
        {
          throw new InvalidDataException("The .ndx file contains overlapping entries.");
        }
        if(sortedEntries[i].Offset > start) grpLayout.AddLast(new NdxEntry(start, sortedEntries[i].Offset-start));
        grpLayout.AddLast(sortedEntries[i]);
        start = sortedEntries[i].End;
      }
      if(start < grpFile.Length) grpLayout.AddLast(new NdxEntry(start, (uint)(grpFile.Length - start)));
      else if(start > grpFile.Length) throw new InvalidDataException("The .ndx file references data not contained within the .grp file.");

      this.grpStream = grpFile;
      this.ndxStream = ndxFile;
      this.ownStreams = ownStreams;
    }

    public ReadOnlyCollection<NdxEntry> IndexEntries
    {
      get { return entries.AsReadOnly(); }
    }

    public bool WasModified
    {
      get { return ndxChanged || grpChanged || repack; }
    }

    public void Add(string fileName, Stream file, uint pixelWidth, uint pixelHeight)
    {
      if(fileName == null || file == null) throw new ArgumentNullException();
      if(string.IsNullOrEmpty(fileName) || !file.CanRead || !file.CanSeek || file.Length > int.MaxValue) throw new ArgumentException();

      // if the uncompressed file is larger than 512k, compress it on disk rather than in memory
      string tempFileName = file.Length > 512*1024 ? Path.GetTempFileName() : null;
      try
      {
        using(Stream temp = tempFileName == null ? (Stream)new MemoryStream((int)file.Length/2) : File.Open(tempFileName, FileMode.Create))
        {
          uint size = (uint)file.Length, compressedSize;
          using(PKWareDCLStream compressed = new PKWareDCLStream(temp, CompressionMode.Compress, false)) file.CopyTo(compressed);
          if(temp.Length > int.MaxValue) throw new ArgumentException("The compressed file was too large.");
          compressedSize = (uint)temp.Length;

          NdxEntry entry = entries.FirstOrDefault(e => string.Equals(fileName, e.Name, StringComparison.OrdinalIgnoreCase));
          if(entry != null) Unlink(entry);

          // find the smallest free block that can hold it, if any
          LinkedListNode<NdxEntry> freeNode = null;
          for(LinkedListNode<NdxEntry> node = grpLayout.First; node != null; node = node.Next)
          {
            if(node.Value.Name == null && node.Value.CompressedSize >= compressedSize &&
               (freeNode == null || node.Value.CompressedSize < freeNode.Value.CompressedSize))
            {
              freeNode = node;
            }
          }

          if(freeNode == null) // if no free block could hold it...
          {
            freeNode = grpLayout.Last;
            if(freeNode != null)
            {
              if(freeNode.Value.Name != null) freeNode = grpLayout.AddLast(new NdxEntry(freeNode.Value.End, compressedSize));
            }
            else
            {
              freeNode = grpLayout.AddLast(new NdxEntry(0, compressedSize));
            }
          }

          if(freeNode.Value.CompressedSize > compressedSize)
          {
            grpLayout.AddAfter(freeNode, new NdxEntry(freeNode.Value.Offset+compressedSize, freeNode.Value.CompressedSize-compressedSize));
          }

          grpStream.Position = freeNode.Value.Offset;
          temp.CopyTo(grpStream, true);

          freeNode.Value.Name = fileName;
          freeNode.Value.CompressedSize   = compressedSize;
          freeNode.Value.UncompressedSize = size;
          freeNode.Value.PixelWidth  = pixelWidth;
          freeNode.Value.PixelHeight = pixelHeight;
          entries.Add(freeNode.Value);

          ndxChanged = grpChanged = true;
        }
      }
      finally
      {
        if(tempFileName != null) File.Delete(tempFileName);
      }
    }

    public void Dispose()
    {
      if(ownStreams)
      {
        grpStream.Dispose();
        ndxStream.Dispose();
      }
    }

    public Stream OpenFile(NdxEntry entry)
    {
      if(entry == null) throw new ArgumentNullException();
      return new PKWareDCLStream(new StreamStream(grpStream, entry.Offset, entry.CompressedSize, true), CompressionMode.Decompress);
    }

    public void Repack()
    {
      AssertWritable();
      if(grpLayout.Any(e => e.Name == null)) repack = true;
    }

    public void Save()
    {
      if(WasModified)
      {
        if(repack)
        {
          Console.WriteLine("重新打包...");
          if(grpLayout.Any(e => e.Name == null))
          {
            byte[] buffer = null;
            uint offset = 0;
            for(LinkedListNode<NdxEntry> node = grpLayout.First; node != null; )
            {
              LinkedListNode<NdxEntry> nextNode = node.Next;
              NdxEntry entry = node.Value;
              if(entry.Name == null)
              {
                grpLayout.Remove(entry);
              }
              else
              {
                if(entry.Offset != offset)
                {
                  grpStream.Position = entry.Offset;
                  if(buffer == null || buffer.Length < entry.CompressedSize) buffer = new byte[entry.CompressedSize];
                  grpStream.ReadOrThrow(buffer, 0, (int)entry.CompressedSize);
                  grpStream.Position = offset;
                  grpStream.Write(buffer, 0, (int)entry.CompressedSize);
                  entry.Offset = offset;
                  ndxChanged = true;
                }
                offset += entry.CompressedSize;
              }

              node = nextNode;
            }
            grpStream.SetLength(offset);
          }
          repack = false;
        }
        else // if we're not going to repack, see if we can easily truncate the file
        {
          LinkedListNode<NdxEntry> node = grpLayout.Last;
          if(node != null && node.Value.Name == null)
          {
            grpStream.SetLength(node.Value.Offset);
            grpLayout.Remove(node);
          }
        }

        if(ndxChanged)
        {
          NdxEntry[] sortedEntries = entries.ToArray();
          Array.Sort(sortedEntries, (a, b) => string.Compare(a.Name, b.Name, true));

          ndxStream.Position = 0;
          ndxStream.SetLength(sortedEntries.Length * 100);
          byte[] data = new byte[100];
          foreach(NdxEntry entry in sortedEntries)
          {
            entry.Save(data);
            ndxStream.Write(data);
          }
        }

        grpChanged = ndxChanged = false;
      }
    }

    public void Unlink(NdxEntry entry)
    {
      if(entry == null) throw new ArgumentNullException();
      AssertWritable();

      if(entries.Remove(entry))
      {
        LinkedListNode<NdxEntry> node = grpLayout.Find(entry), prev = node.Previous, next = node.Next;
        if(prev != null && prev.Value.Name == null)
        {
          prev.Value.CompressedSize += entry.CompressedSize;
          if(next != null && next.Value.Name == null)
          {
            prev.Value.CompressedSize += next.Value.CompressedSize;
            grpLayout.Remove(next);
          }
        }
        else if(next != null && next.Value.Name == null)
        {
          next.Value.CompressedSize += entry.CompressedSize;
        }
        else
        {
          grpLayout.AddAfter(node, new NdxEntry(entry.Offset, entry.CompressedSize));
        }
        grpLayout.Remove(node);
        ndxChanged = true;
      }
    }

    void AssertWritable()
    {
      if(!grpStream.CanWrite || !ndxStream.CanSeek || !ndxStream.CanWrite)
      {
        throw new InvalidOperationException("The archive is not writable.");
      }
    }

    readonly List<NdxEntry> entries = new List<NdxEntry>();
    readonly LinkedList<NdxEntry> grpLayout = new LinkedList<NdxEntry>();
    readonly Stream grpStream, ndxStream;
    readonly bool ownStreams;
    bool grpChanged, ndxChanged, repack;
  }
}